"""
Intervention Storage Service

Handles PostgreSQL storage and retrieval of intervention records
with effectiveness tracking.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy import text
from config.database import get_async_db


class InterventionStorageService:
    """Service for storing and retrieving intervention records"""
    
    def __init__(self):
        self.logger = logging.getLogger("InterventionStorageService")
    
    async def store_intervention(self, intervention_data: Dict[str, Any]) -> str:
        """
        Store intervention record in PostgreSQL.
        
        Args:
            intervention_data: Dict containing intervention details
            
        Returns:
            intervention_id (UUID string)
        """
        try:
            async for db in get_async_db():
                query = text("""
                    INSERT INTO interventions (
                        "studentId", "sessionId", "interventionType",
                        priority, message, context, "deliveredAt"
                    )
                    VALUES (
                        :student_id, :session_id, :intervention_type,
                        :priority, :message, :context::jsonb, :delivered_at
                    )
                    RETURNING id
                """)
                
                result = await db.execute(query, {
                    "student_id": intervention_data["student_id"],
                    "session_id": intervention_data["session_id"],
                    "intervention_type": intervention_data["intervention_type"],
                    "priority": intervention_data["priority"],
                    "message": intervention_data["message"],
                    "context": intervention_data.get("context", {}),
                    "delivered_at": intervention_data.get("delivered_at", datetime.now())
                })
                
                await db.commit()
                
                intervention_id = result.fetchone()[0]
                self.logger.info(f"Stored intervention {intervention_id} for student {intervention_data['student_id']}")
                return intervention_id
                
        except Exception as e:
            self.logger.error(f"Failed to store intervention: {e}", exc_info=True)
            raise
    
    async def get_intervention_history(
        self, 
        student_id: str,
        days: int = 7,
        intervention_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve intervention history for a student.
        
        Args:
            student_id: Student UUID
            days: Number of days to look back
            intervention_type: Optional filter by intervention type
            
        Returns:
            List of intervention records
        """
        try:
            async for db in get_async_db():
                since_date = datetime.now() - timedelta(days=days)
                
                if intervention_type:
                    query = text("""
                        SELECT 
                            id, "studentId", "sessionId", "interventionType",
                            priority, message, context, "deliveredAt",
                            "acknowledgedAt", effectiveness, outcome
                        FROM interventions
                        WHERE "studentId" = :student_id
                          AND "deliveredAt" >= :since_date
                          AND "interventionType" = :intervention_type
                        ORDER BY "deliveredAt" DESC
                    """)
                    result = await db.execute(query, {
                        "student_id": student_id,
                        "since_date": since_date,
                        "intervention_type": intervention_type
                    })
                else:
                    query = text("""
                        SELECT 
                            id, "studentId", "sessionId", "interventionType",
                            priority, message, context, "deliveredAt",
                            "acknowledgedAt", effectiveness, outcome
                        FROM interventions
                        WHERE "studentId" = :student_id
                          AND "deliveredAt" >= :since_date
                        ORDER BY "deliveredAt" DESC
                    """)
                    result = await db.execute(query, {
                        "student_id": student_id,
                        "since_date": since_date
                    })
                
                rows = result.fetchall()
                
                interventions = []
                for row in rows:
                    interventions.append({
                        "id": row[0],
                        "student_id": row[1],
                        "session_id": row[2],
                        "intervention_type": row[3],
                        "priority": row[4],
                        "message": row[5],
                        "context": row[6],
                        "delivered_at": row[7],
                        "acknowledged_at": row[8],
                        "effectiveness": row[9],
                        "outcome": row[10]
                    })
                
                return interventions
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve intervention history: {e}", exc_info=True)
            return []
    
    async def update_intervention_effectiveness(
        self,
        intervention_id: str,
        effectiveness: float,
        outcome: str
    ):
        """
        Update intervention effectiveness score and outcome.
        
        Args:
            intervention_id: Intervention UUID
            effectiveness: Effectiveness score (0-1)
            outcome: Outcome string (improved, no_change, declined)
        """
        try:
            async for db in get_async_db():
                query = text("""
                    UPDATE interventions
                    SET effectiveness = :effectiveness,
                        outcome = :outcome
                    WHERE id = :intervention_id
                """)
                
                await db.execute(query, {
                    "intervention_id": intervention_id,
                    "effectiveness": effectiveness,
                    "outcome": outcome
                })
                
                await db.commit()
                
                self.logger.info(
                    f"Updated intervention {intervention_id}: "
                    f"effectiveness={effectiveness:.2f}, outcome={outcome}"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update intervention effectiveness: {e}", exc_info=True)
            raise
    
    async def acknowledge_intervention(self, intervention_id: str):
        """
        Mark intervention as acknowledged by student.
        
        Args:
            intervention_id: Intervention UUID
        """
        try:
            async for db in get_async_db():
                query = text("""
                    UPDATE interventions
                    SET "acknowledgedAt" = :acknowledged_at
                    WHERE id = :intervention_id
                """)
                
                await db.execute(query, {
                    "intervention_id": intervention_id,
                    "acknowledged_at": datetime.now()
                })
                
                await db.commit()
                
                self.logger.info(f"Intervention {intervention_id} acknowledged")
                
        except Exception as e:
            self.logger.error(f"Failed to acknowledge intervention: {e}", exc_info=True)
            raise
    
    async def get_effectiveness_stats(self, student_id: str) -> Dict[str, Any]:
        """
        Get aggregated effectiveness statistics by intervention type.
        
        Args:
            student_id: Student UUID
            
        Returns:
            Dict with effectiveness statistics
        """
        try:
            async for db in get_async_db():
                query = text("""
                    SELECT 
                        "interventionType",
                        COUNT(*) as total_count,
                        COUNT("acknowledgedAt") as acknowledged_count,
                        AVG(effectiveness) as avg_effectiveness,
                        SUM(CASE WHEN outcome = 'improved' THEN 1 ELSE 0 END) as improved_count,
                        SUM(CASE WHEN outcome = 'no_change' THEN 1 ELSE 0 END) as no_change_count,
                        SUM(CASE WHEN outcome = 'declined' THEN 1 ELSE 0 END) as declined_count
                    FROM interventions
                    WHERE "studentId" = :student_id
                      AND "deliveredAt" >= NOW() - INTERVAL '30 days'
                    GROUP BY "interventionType"
                """)
                
                result = await db.execute(query, {"student_id": student_id})
                rows = result.fetchall()
                
                stats = {}
                for row in rows:
                    intervention_type = row[0]
                    stats[intervention_type] = {
                        "total_count": row[1],
                        "acknowledged_count": row[2],
                        "acknowledgment_rate": row[2] / row[1] if row[1] > 0 else 0,
                        "avg_effectiveness": float(row[3]) if row[3] else None,
                        "improved_count": row[4],
                        "no_change_count": row[5],
                        "declined_count": row[6],
                        "success_rate": row[4] / row[1] if row[1] > 0 else 0
                    }
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get effectiveness stats: {e}", exc_info=True)
            return {}
    
    async def calculate_intervention_effectiveness(
        self,
        student_id: str,
        intervention_id: str,
        pre_metrics: Dict[str, Any],
        post_metrics: Dict[str, Any],
        intervention_type: str
    ) -> float:
        """
        Calculate effectiveness score by comparing pre/post metrics.
        
        Args:
            student_id: Student UUID
            intervention_id: Intervention UUID
            pre_metrics: Metrics before intervention
            post_metrics: Metrics after intervention
            intervention_type: Type of intervention
            
        Returns:
            Effectiveness score (0-1)
        """
        try:
            # Different effectiveness calculations based on intervention type
            if intervention_type == "break_suggestion":
                # Measure cognitive load reduction
                pre_load = pre_metrics.get("cognitive_load", 50)
                post_load = post_metrics.get("cognitive_load", 50)
                
                if pre_load > 70:
                    load_reduction = (pre_load - post_load) / pre_load
                    effectiveness = max(0, min(1, load_reduction))
                else:
                    effectiveness = 0.5  # Neutral if load wasn't high
                    
            elif intervention_type == "recap_prompt":
                # Measure accuracy improvement
                pre_accuracy = pre_metrics.get("quiz_accuracy", 70)
                post_accuracy = post_metrics.get("quiz_accuracy", 70)
                
                if pre_accuracy < 70:
                    accuracy_gain = (post_accuracy - pre_accuracy) / (100 - pre_accuracy)
                    effectiveness = max(0, min(1, accuracy_gain))
                else:
                    effectiveness = 0.5
                    
            elif intervention_type == "topic_switch":
                # Measure engagement increase
                pre_engagement = pre_metrics.get("engagement_score", 50)
                post_engagement = post_metrics.get("engagement_score", 50)
                
                engagement_gain = (post_engagement - pre_engagement) / 100
                effectiveness = max(0, min(1, 0.5 + engagement_gain))
                
            elif intervention_type == "encouragement":
                # Measure mood improvement
                pre_mood = pre_metrics.get("mood_score", 0)
                post_mood = post_metrics.get("mood_score", 0)
                
                mood_improvement = post_mood - pre_mood
                effectiveness = max(0, min(1, 0.5 + mood_improvement))
                
            elif intervention_type == "difficulty_adjustment":
                # Measure accuracy improvement after adjustment
                pre_accuracy = pre_metrics.get("quiz_accuracy", 70)
                post_accuracy = post_metrics.get("quiz_accuracy", 70)
                
                accuracy_gain = (post_accuracy - pre_accuracy) / 100
                effectiveness = max(0, min(1, 0.5 + accuracy_gain))
                
            else:
                # Default: average of all metrics
                effectiveness = 0.5
            
            # Determine outcome
            if effectiveness >= 0.7:
                outcome = "improved"
            elif effectiveness >= 0.4:
                outcome = "no_change"
            else:
                outcome = "declined"
            
            # Update database
            await self.update_intervention_effectiveness(intervention_id, effectiveness, outcome)
            
            return effectiveness
            
        except Exception as e:
            self.logger.error(f"Failed to calculate effectiveness: {e}", exc_info=True)
            return 0.5
