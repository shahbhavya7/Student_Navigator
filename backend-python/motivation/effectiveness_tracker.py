"""
Intervention Effectiveness Tracker

Tracks intervention outcomes by measuring metrics before and after
interventions to calculate effectiveness scores.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import asyncio

from sqlalchemy import text
from config.database import get_async_db
from config.redis_client import redis_client
from services.intervention_storage import InterventionStorageService


class InterventionEffectivenessTracker:
    """Tracks and measures intervention effectiveness"""
    
    def __init__(self):
        self.logger = logging.getLogger("InterventionEffectivenessTracker")
        self.storage = InterventionStorageService()
    
    async def track_intervention_outcome(
        self,
        student_id: str,
        intervention_id: str,
        pre_metrics: Dict[str, Any],
        post_metrics: Dict[str, Any],
        intervention_type: str
    ):
        """
        Track intervention outcome by comparing pre/post metrics.
        
        Args:
            student_id: Student UUID
            intervention_id: Intervention UUID
            pre_metrics: Metrics before intervention
            post_metrics: Metrics after intervention
            intervention_type: Type of intervention
        """
        try:
            self.logger.info(
                f"Tracking outcome for intervention {intervention_id}: "
                f"type={intervention_type}, student={student_id}"
            )
            
            # Calculate effectiveness score
            effectiveness = await self.storage.calculate_intervention_effectiveness(
                student_id=student_id,
                intervention_id=intervention_id,
                pre_metrics=pre_metrics,
                post_metrics=post_metrics,
                intervention_type=intervention_type
            )
            
            self.logger.info(
                f"Intervention {intervention_id} effectiveness: {effectiveness:.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to track intervention outcome: {e}", exc_info=True)
    
    async def measure_post_intervention_metrics(
        self,
        student_id: str,
        intervention_time: int,
        intervention_type: str
    ) -> Dict[str, Any]:
        """
        Measure metrics after intervention (15-minute window).
        
        Args:
            student_id: Student UUID
            intervention_time: Timestamp when intervention was delivered
            intervention_type: Type of intervention
            
        Returns:
            Dict with post-intervention metrics
        """
        try:
            # Wait for effectiveness window
            await asyncio.sleep(60)  # Wait 1 minute for immediate check
            
            metrics = {}
            
            # Fetch cognitive load from Redis time-series (if available)
            cognitive_load = await self._get_recent_cognitive_load(student_id)
            if cognitive_load is not None:
                metrics["cognitive_load"] = cognitive_load
            
            # Fetch performance data from PostgreSQL
            performance_data = await self._get_recent_performance(student_id)
            metrics.update(performance_data)
            
            # Fetch engagement metrics
            engagement = await self._get_recent_engagement(student_id)
            if engagement is not None:
                metrics["engagement_score"] = engagement
            
            # Fetch mood data
            mood = await self._get_recent_mood(student_id)
            if mood is not None:
                metrics["mood_score"] = mood
            
            self.logger.info(
                f"Post-intervention metrics for {student_id}: {metrics}"
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to measure post-intervention metrics: {e}", exc_info=True)
            return {}
    
    async def schedule_effectiveness_measurement(
        self,
        intervention_id: str,
        student_id: str,
        intervention_time: int,
        intervention_type: str,
        pre_metrics: Dict[str, Any]
    ):
        """
        Schedule background task to measure effectiveness after window.
        
        Args:
            intervention_id: Intervention UUID
            student_id: Student UUID
            intervention_time: Timestamp when intervention was delivered
            intervention_type: Type of intervention
            pre_metrics: Metrics before intervention
        """
        try:
            # Create background task
            asyncio.create_task(
                self._measure_effectiveness_after_delay(
                    intervention_id=intervention_id,
                    student_id=student_id,
                    intervention_time=intervention_time,
                    intervention_type=intervention_type,
                    pre_metrics=pre_metrics
                )
            )
            
            self.logger.info(
                f"Scheduled effectiveness measurement for intervention {intervention_id}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to schedule effectiveness measurement: {e}", exc_info=True)
    
    async def _measure_effectiveness_after_delay(
        self,
        intervention_id: str,
        student_id: str,
        intervention_time: int,
        intervention_type: str,
        pre_metrics: Dict[str, Any]
    ):
        """
        Wait for effectiveness window then measure and track outcome.
        
        Args:
            intervention_id: Intervention UUID
            student_id: Student UUID
            intervention_time: Timestamp when intervention was delivered
            intervention_type: Type of intervention
            pre_metrics: Metrics before intervention
        """
        try:
            # Wait for effectiveness window
            from config.settings import settings
            wait_seconds = settings.INTERVENTION_EFFECTIVENESS_WINDOW_MINUTES * 60
            await asyncio.sleep(wait_seconds)
            
            # Measure post-intervention metrics
            post_metrics = await self.measure_post_intervention_metrics(
                student_id=student_id,
                intervention_time=intervention_time,
                intervention_type=intervention_type
            )
            
            # Track outcome
            if post_metrics:
                await self.track_intervention_outcome(
                    student_id=student_id,
                    intervention_id=intervention_id,
                    pre_metrics=pre_metrics,
                    post_metrics=post_metrics,
                    intervention_type=intervention_type
                )
            
        except Exception as e:
            self.logger.error(f"Error in delayed effectiveness measurement: {e}", exc_info=True)
    
    async def _get_recent_cognitive_load(self, student_id: str) -> Optional[float]:
        """Get most recent cognitive load score from Redis"""
        try:
            # Try to get from Redis time-series or latest state
            key = f"student:{student_id}:cognitive_load"
            value = redis_client.client.get(key)
            if value:
                return float(value)
        except Exception as e:
            self.logger.debug(f"Failed to get cognitive load from Redis: {e}")
        return None
    
    async def _get_recent_performance(self, student_id: str) -> Dict[str, Any]:
        """Get recent performance metrics from PostgreSQL"""
        try:
            async for db in get_async_db():
                # Get most recent quiz results
                query = text("""
                    SELECT 
                        AVG(score) as avg_score,
                        COUNT(*) as quiz_count
                    FROM quiz_results
                    WHERE "studentId" = :student_id
                      AND "completedAt" >= NOW() - INTERVAL '1 hour'
                """)
                
                result = await db.execute(query, {"student_id": student_id})
                row = result.fetchone()
                
                if row and row[1] > 0:
                    return {
                        "quiz_accuracy": float(row[0]),
                        "quiz_count": row[1]
                    }
        except Exception as e:
            self.logger.debug(f"Failed to get performance data: {e}")
        
        return {}
    
    async def _get_recent_engagement(self, student_id: str) -> Optional[float]:
        """Get recent engagement score"""
        try:
            key = f"student:{student_id}:engagement"
            value = redis_client.client.get(key)
            if value:
                return float(value)
        except Exception as e:
            self.logger.debug(f"Failed to get engagement from Redis: {e}")
        return None
    
    async def _get_recent_mood(self, student_id: str) -> Optional[float]:
        """Get recent mood score"""
        try:
            key = f"student:{student_id}:mood"
            value = redis_client.client.get(key)
            if value:
                return float(value)
        except Exception as e:
            self.logger.debug(f"Failed to get mood from Redis: {e}")
        return None
    
    def _calculate_effectiveness_score(
        self,
        pre_metrics: Dict[str, Any],
        post_metrics: Dict[str, Any],
        intervention_type: str
    ) -> float:
        """
        Calculate effectiveness score based on metric changes.
        
        This is a wrapper that delegates to storage service's implementation.
        Kept here for backwards compatibility.
        
        Args:
            pre_metrics: Metrics before intervention
            post_metrics: Metrics after intervention
            intervention_type: Type of intervention
            
        Returns:
            Effectiveness score (0-1)
        """
        # This will be calculated by storage service
        return 0.5
