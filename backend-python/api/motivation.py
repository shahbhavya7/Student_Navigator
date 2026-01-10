"""
Motivation and Intervention API Endpoints

Provides REST API for intervention history, effectiveness stats,
acknowledgments, and recommendations.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from pydantic import BaseModel
from services.intervention_storage import InterventionStorageService
from motivation.intervention_rules import InterventionRuleEngine
from motivation.message_generator import PersonalizedMessageGenerator
from agents.state import AgentState
from config.database import get_async_db
from sqlalchemy import text

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
intervention_storage = InterventionStorageService()
rule_engine = InterventionRuleEngine()


class AcknowledgeRequest(BaseModel):
    """Request model for acknowledging intervention"""
    intervention_id: str


class InterventionResponse(BaseModel):
    """Response model for intervention data"""
    id: str
    student_id: str
    session_id: str
    intervention_type: str
    priority: str
    message: str
    context: Dict[str, Any]
    delivered_at: datetime
    acknowledged_at: Optional[datetime] = None
    effectiveness: Optional[float] = None
    outcome: Optional[str] = None


class EffectivenessStatsResponse(BaseModel):
    """Response model for effectiveness statistics"""
    intervention_type: str
    total_count: int
    acknowledged_count: int
    acknowledgment_rate: float
    avg_effectiveness: Optional[float]
    improved_count: int
    no_change_count: int
    declined_count: int
    success_rate: float


class RecommendationResponse(BaseModel):
    """Response model for intervention recommendations"""
    intervention_type: str
    priority: str
    trigger_reason: str
    confidence: float
    would_trigger: bool


@router.get("/interventions/{student_id}", response_model=List[InterventionResponse])
async def get_intervention_history(
    student_id: str,
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    intervention_type: Optional[str] = Query(None, description="Filter by intervention type")
):
    """
    Get intervention history for a student.
    
    Args:
        student_id: Student UUID
        days: Number of days to look back (1-90)
        intervention_type: Optional filter by intervention type
        
    Returns:
        List of intervention records
    """
    try:
        interventions = await intervention_storage.get_intervention_history(
            student_id=student_id,
            days=days,
            intervention_type=intervention_type
        )
        
        return interventions
        
    except Exception as e:
        logger.error(f"Failed to get intervention history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve intervention history")


@router.get("/effectiveness/{student_id}", response_model=Dict[str, EffectivenessStatsResponse])
async def get_effectiveness_statistics(student_id: str):
    """
    Get effectiveness statistics by intervention type for a student.
    
    Args:
        student_id: Student UUID
        
    Returns:
        Dict mapping intervention types to effectiveness stats
    """
    try:
        stats = await intervention_storage.get_effectiveness_stats(student_id)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get effectiveness stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve effectiveness statistics")


@router.post("/acknowledge/{intervention_id}")
async def acknowledge_intervention(intervention_id: str):
    """
    Mark intervention as acknowledged by student.
    
    Args:
        intervention_id: Intervention UUID
        
    Returns:
        Success message
    """
    try:
        await intervention_storage.acknowledge_intervention(intervention_id)
        
        return {
            "success": True,
            "intervention_id": intervention_id,
            "acknowledged_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to acknowledge intervention: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to acknowledge intervention")


@router.get("/recommendations/{student_id}", response_model=List[RecommendationResponse])
async def get_intervention_recommendations(student_id: str):
    """
    Get current intervention recommendations without triggering them.
    Useful for instructor dashboard to see what interventions would be triggered.
    
    Args:
        student_id: Student UUID
        
    Returns:
        List of potential interventions based on current state
    """
    try:
        # Fetch current student state from database
        async for db in get_async_db():
            # Get cognitive metrics
            cognitive_query = text("""
                SELECT 
                    "cognitiveLoadScore",
                    "errorRate",
                    "moodScore"
                FROM cognitive_metrics
                WHERE "studentId" = :student_id
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            cognitive_result = await db.execute(cognitive_query, {"student_id": student_id})
            cognitive_row = cognitive_result.fetchone()
            
            # Get quiz results
            quiz_query = text("""
                SELECT AVG(score) as avg_score
                FROM quiz_results
                WHERE "studentId" = :student_id
                  AND "completedAt" >= NOW() - INTERVAL '7 days'
            """)
            quiz_result = await db.execute(quiz_query, {"student_id": student_id})
            quiz_row = quiz_result.fetchone()
            
            # Get session info
            session_query = text("""
                SELECT 
                    id,
                    EXTRACT(EPOCH FROM (NOW() - "startTime"))/60 as duration_minutes
                FROM sessions
                WHERE "studentId" = :student_id
                  AND "endTime" IS NULL
                ORDER BY "startTime" DESC
                LIMIT 1
            """)
            session_result = await db.execute(session_query, {"student_id": student_id})
            session_row = session_result.fetchone()
            
            # Build state dict
            state: AgentState = {
                "student_id": student_id,
                "session_id": session_row[0] if session_row else "unknown",
                "cognitive_load_score": float(cognitive_row[0]) if cognitive_row else 50,
                "error_rate": float(cognitive_row[1]) if cognitive_row else 0,
                "mood_score": float(cognitive_row[2]) if cognitive_row and cognitive_row[2] else 0,
                "quiz_accuracy": float(quiz_row[0]) if quiz_row and quiz_row[0] else 70,
                "session_duration_minutes": float(session_row[1]) if session_row else 0,
                "last_intervention_time": 0,  # Don't throttle for recommendations
            }
            
            # Evaluate rules
            triggers = rule_engine.evaluate_rules(state)
            
            # Convert to response format
            recommendations = []
            for trigger in triggers:
                recommendations.append({
                    "intervention_type": trigger.intervention_type,
                    "priority": trigger.priority,
                    "trigger_reason": trigger.trigger_reason,
                    "confidence": trigger.confidence,
                    "would_trigger": True
                })
            
            return recommendations
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve recommendations")


@router.get("/health")
async def motivation_health_check():
    """Health check endpoint for motivation system"""
    return {
        "status": "healthy",
        "service": "motivation",
        "timestamp": datetime.now().isoformat()
    }
