"""
Student Performance Profile Generator

Combines cognitive load, performance, and engagement data to generate
comprehensive student profiles with health scores and risk assessments.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from config.redis_client import redis_client
from config.database import get_async_db


@dataclass
class StudentPerformanceProfile:
    """Comprehensive student performance profile"""
    student_id: str
    cognitive_load_summary: Dict[str, Any]
    performance_summary: Dict[str, Any]
    engagement_summary: Dict[str, Any]
    combined_health_score: float
    risk_level: str
    recommended_actions: List[str]
    generated_at: str


class PerformanceProfileGenerator:
    """Generate comprehensive student performance profiles"""
    
    def generate_profile(
        self,
        student_id: str,
        clr_data: Dict[str, Any],
        performance_data: Dict[str, Any],
        engagement_data: Dict[str, Any]
    ) -> StudentPerformanceProfile:
        """
        Generate comprehensive student profile from combined data.
        
        Args:
            student_id: Student identifier
            clr_data: Cognitive load results from CLR agent
            performance_data: Performance metrics from performance agent
            engagement_data: Engagement metrics from engagement agent
            
        Returns:
            StudentPerformanceProfile instance
        """
        # Extract cognitive load summary - handle both direct dict and API response formats
        if "current_load" in clr_data:
            # Direct dict format (from tests)
            cognitive_load_summary = clr_data
        else:
            # API response format
            cognitive_load_summary = {
                "current_load": clr_data.get("cognitive_load_score", 50),
                "avg_load": clr_data.get("average_load", 50),
                "trend": clr_data.get("load_trend", "stable"),
                "overload_risk": clr_data.get("overload_detected", False)
            }
        
        # Extract performance summary
        performance_summary = {
            "quiz_accuracy": performance_data.get("quiz_accuracy", 0),
            "learning_velocity": performance_data.get("learning_velocity", 0),
            "improvement_trend": performance_data.get("improvement_trend", "stable"),
            "weak_topics": performance_data.get("weak_topics", []),
            "task_completion_rate": performance_data.get("task_completion_rate", 0),
            "plateau_detected": performance_data.get("plateau_detected", False)
        }
        
        # Extract engagement summary
        engagement_summary = {
            "engagement_score": engagement_data.get("engagement_score", 0),
            "dropout_risk": engagement_data.get("dropout_risk", 0),
            "session_frequency": engagement_data.get("session_frequency", 0),
            "interaction_depth": engagement_data.get("interaction_depth", 0),
            "dropout_signals": engagement_data.get("dropout_signals", [])
        }
        
        # Calculate combined health score (0-100)
        combined_health_score = self._calculate_combined_health_score(
            cognitive_load_summary,
            performance_summary,
            engagement_summary
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(
            combined_health_score,
            cognitive_load_summary,
            performance_summary,
            engagement_summary
        )
        
        # Generate recommended actions
        recommended_actions = self._generate_recommended_actions(
            risk_level,
            cognitive_load_summary,
            performance_summary,
            engagement_summary
        )
        
        return StudentPerformanceProfile(
            student_id=student_id,
            cognitive_load_summary=cognitive_load_summary,
            performance_summary=performance_summary,
            engagement_summary=engagement_summary,
            combined_health_score=combined_health_score,
            risk_level=risk_level,
            recommended_actions=recommended_actions,
            generated_at=datetime.now().isoformat()
        )
    
    def _calculate_combined_health_score(
        self,
        cognitive_load: Dict,
        performance: Dict,
        engagement: Dict
    ) -> float:
        """
        Calculate combined health score using weighted formula.
        
        Weights:
        - Inverse of cognitive load: 30% (lower is better)
        - Performance metrics: 40% (higher is better)
        - Engagement score: 30% (higher is better)
        
        Returns:
            Health score (0-100)
        """
        # Cognitive load component (inverse - lower load is better)
        cognitive_score = 100 - cognitive_load["current_load"]
        cognitive_weight = 0.30
        
        # Performance component
        accuracy = performance["quiz_accuracy"]
        velocity_normalized = min(max(performance["learning_velocity"] * 10 + 50, 0), 100)
        completion = performance["task_completion_rate"]
        
        performance_score = (accuracy * 0.5 + velocity_normalized * 0.3 + completion * 0.2)
        performance_weight = 0.40
        
        # Engagement component
        engagement_score = engagement["engagement_score"]
        engagement_weight = 0.30
        
        # Weighted sum
        health_score = (
            cognitive_score * cognitive_weight +
            performance_score * performance_weight +
            engagement_score * engagement_weight
        )
        
        return round(health_score, 2)
    
    def _determine_risk_level(
        self,
        combined_score: float,
        cognitive_load: Dict,
        performance: Dict,
        engagement: Dict
    ) -> str:
        """
        Determine risk level based on combined score and individual red flags.
        
        Risk Levels:
        - Critical: combined_score < 40 OR dropout_risk > 0.8 OR cognitive_load > 85
        - High: combined_score < 55 OR dropout_risk > 0.6 OR cognitive_load > 75
        - Medium: combined_score < 70 OR dropout_risk > 0.4
        - Low: otherwise
        """
        # Critical risk conditions
        if (combined_score < 40 or 
            engagement["dropout_risk"] > 0.8 or 
            cognitive_load["current_load"] > 85):
            return "critical"
        
        # High risk conditions
        if (combined_score < 55 or 
            engagement["dropout_risk"] > 0.6 or 
            cognitive_load["current_load"] > 75):
            return "high"
        
        # Medium risk conditions
        if (combined_score < 70 or 
            engagement["dropout_risk"] > 0.4):
            return "medium"
        
        # Low risk (healthy)
        return "low"
    
    def _generate_recommended_actions(
        self,
        risk_level: str,
        cognitive_load: Dict,
        performance: Dict,
        engagement: Dict
    ) -> List[str]:
        """
        Generate recommended actions based on risk factors.
        
        Returns:
            List of actionable recommendations
        """
        actions = []
        
        # High cognitive load interventions
        if cognitive_load["current_load"] > 75:
            actions.append("Reduce learning pace and difficulty to prevent cognitive overload")
            if cognitive_load["overload_risk"]:
                actions.append("Recommend a break - cognitive overload detected")
        
        # Low performance interventions
        if performance["quiz_accuracy"] < 60:
            actions.append("Review weak topics and provide additional learning resources")
            if performance["weak_topics"]:
                actions.append(f"Focus on struggling areas: {', '.join(performance['weak_topics'][:3])}")
        
        # Plateau detection
        if performance["plateau_detected"]:
            actions.append("Learning plateau detected - introduce new learning strategies or materials")
        
        # Declining trend
        if performance["improvement_trend"] == "declining":
            actions.append("Performance declining - schedule check-in with instructor")
        
        # High dropout risk interventions
        if engagement["dropout_risk"] > 0.6:
            actions.append("High dropout risk - increase engagement through gamification or peer interaction")
            actions.append("Consider personalized outreach or motivation interventions")
        
        # Low engagement
        if engagement["engagement_score"] < 50:
            actions.append("Low engagement detected - introduce more interactive content")
        
        # Dropout signals
        if len(engagement["dropout_signals"]) > 2:
            actions.append("Multiple dropout signals detected - immediate intervention recommended")
        
        # Low task completion
        if performance["task_completion_rate"] < 50:
            actions.append("Low task completion rate - break down learning goals into smaller milestones")
        
        # Risk-level specific actions
        if risk_level == "critical":
            actions.insert(0, "URGENT: Critical risk level - immediate instructor intervention required")
        elif risk_level == "high":
            actions.insert(0, "High priority: Schedule student support session within 48 hours")
        
        # Default action if no specific recommendations
        if not actions:
            actions.append("Continue monitoring - student performance is healthy")
        
        return actions
    
    async def store_profile(self, profile: StudentPerformanceProfile):
        """
        Store profile in Redis and optionally PostgreSQL.
        
        Args:
            profile: StudentPerformanceProfile instance
        """
        try:
            # Store in Redis with 24-hour TTL
            redis_client = await get_redis_client()
            key = f"profile:{profile.student_id}"
            
            profile_dict = asdict(profile)
            await redis_client.hset(key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in profile_dict.items()
            })
            
            await redis_client.expire(key, 86400)
            
            # Optionally store in PostgreSQL for historical tracking
            await self._store_profile_in_db(profile)
            
        except Exception as e:
            print(f"Error storing profile: {str(e)}")
    
    async def _store_profile_in_db(self, profile: StudentPerformanceProfile):
        """Store profile in PostgreSQL for historical tracking"""
        try:
            async for db in get_async_db():
                # Store as JSON in a dedicated table or in student record
                query = """
                    INSERT INTO student_profiles 
                    ("studentId", "profileData", "healthScore", "riskLevel", "createdAt")
                    VALUES (:student_id, :profile_data, :health_score, :risk_level, :created_at)
                    ON CONFLICT ("studentId") 
                    DO UPDATE SET 
                        "profileData" = EXCLUDED."profileData",
                        "healthScore" = EXCLUDED."healthScore",
                        "riskLevel" = EXCLUDED."riskLevel",
                        "updatedAt" = EXCLUDED."createdAt"
                """
                
                profile_dict = asdict(profile)
                
                await db.execute(query, {
                    "student_id": profile.student_id,
                    "profile_data": json.dumps(profile_dict),
                    "health_score": profile.combined_health_score,
                    "risk_level": profile.risk_level,
                    "created_at": datetime.now()
                })
                
                await db.commit()
                break
                
        except Exception as e:
            # Table might not exist yet - silently continue
            print(f"Note: Could not store profile in database: {str(e)}")
    
    async def get_profile(self, student_id: str) -> Optional[StudentPerformanceProfile]:
        """
        Retrieve profile from Redis.
        
        Args:
            student_id: Student identifier
            
        Returns:
            StudentPerformanceProfile instance or None
        """
        try:
            redis_client = await get_redis_client()
            key = f"profile:{student_id}"
            
            profile_data = await redis_client.hgetall(key)
            
            if not profile_data:
                return None
            
            # Parse JSON fields
            def parse_value(v):
                try:
                    return json.loads(v)
                except:
                    return v
            
            parsed_data = {k.decode(): parse_value(v.decode()) for k, v in profile_data.items()}
            
            return StudentPerformanceProfile(**parsed_data)
            
        except Exception as e:
            print(f"Error retrieving profile: {str(e)}")
            return None
