from fastapi import APIRouter, BackgroundTasks, HTTPException
import uuid
import time
import logging

from models.schemas import (
    TriggerWorkflowRequest,
    TriggerWorkflowResponse,
    CognitiveLoadRequest,
    CognitiveLoadResponse,
    RequestInterventionRequest,
    InterventionResponse,
    CurriculumAdjustmentRequest,
    CurriculumAdjustmentResponse,
    AgentExecutionStatus
)
from agents.graph import execute_agent_workflow
from config.redis_client import redis_client
from config.settings import settings

router = APIRouter(prefix="/api/agents", tags=["agents"])
logger = logging.getLogger(__name__)

# In-memory workflow status storage (in production, use Redis/database)
workflow_statuses = {}


@router.post("/trigger-workflow", response_model=TriggerWorkflowResponse)
async def trigger_workflow(
    request: TriggerWorkflowRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger agent workflow execution
    
    Trigger types:
    - session_end: Execute when learning session ends
    - quiz_completed: Execute after quiz completion
    - cognitive_threshold_breach: Execute on high cognitive load
    - manual: Manually triggered workflow
    """
    
    workflow_id = str(uuid.uuid4())
    
    # Initialize workflow status
    workflow_statuses[workflow_id] = AgentExecutionStatus(
        workflow_id=workflow_id,
        status="running",
        student_id=request.student_id,
        session_id=request.session_id,
        agents_executed=[],
        current_agent="fetch_data",
        agent_outputs={},
        errors=[],
        started_at=int(time.time()),
        completed_at=None
    )
    
    # Execute workflow in background
    background_tasks.add_task(
        execute_workflow_background,
        workflow_id,
        request.student_id,
        request.session_id
    )
    
    logger.info(
        f"🎯 Triggered {request.trigger_type} workflow for student {request.student_id} "
        f"(workflow_id: {workflow_id})"
    )
    
    return TriggerWorkflowResponse(
        workflow_id=workflow_id,
        status="running",
        message=f"Workflow triggered successfully with ID {workflow_id}"
    )


async def execute_workflow_background(workflow_id: str, student_id: str, session_id: str):
    """Background task for workflow execution"""
    try:
        result = await execute_agent_workflow(student_id, session_id)
        
        # Update status
        if workflow_id in workflow_statuses:
            workflow_statuses[workflow_id].status = result.get("status", "completed")
            workflow_statuses[workflow_id].agents_executed = result.get("agents_executed", [])
            workflow_statuses[workflow_id].agent_outputs = result
            workflow_statuses[workflow_id].completed_at = int(time.time())
            
            if result.get("error"):
                workflow_statuses[workflow_id].errors.append(result["error"])
        
        logger.info(f"✅ Workflow {workflow_id} completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Workflow {workflow_id} failed: {e}")
        if workflow_id in workflow_statuses:
            workflow_statuses[workflow_id].status = "failed"
            workflow_statuses[workflow_id].errors.append(str(e))
            workflow_statuses[workflow_id].completed_at = int(time.time())


@router.get("/workflow-status/{workflow_id}", response_model=AgentExecutionStatus)
async def get_workflow_status(workflow_id: str):
    """Get current status of agent workflow execution"""
    
    if workflow_id not in workflow_statuses:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflow_statuses[workflow_id]


@router.post("/calculate-cognitive-load", response_model=CognitiveLoadResponse)
async def calculate_cognitive_load(request: CognitiveLoadRequest):
    """
    Calculate cognitive load score for a student session
    
    Fetches behavioral events from Redis, runs CLR Agent, and returns score
    """
    
    try:
        # Fetch events
        events = await redis_client.get_behavioral_events(request.session_id)
        
        if not events:
            logger.warning(f"No behavioral events found for session {request.session_id}")
        
        # Execute workflow to get cognitive load
        result = await execute_agent_workflow(request.student_id, request.session_id)
        
        cognitive_load_score = result.get("cognitive_load_score", 50.0)
        
        # Determine fatigue level
        if cognitive_load_score < settings.CLR_THRESHOLD_LOW:
            fatigue_level = "low"
        elif cognitive_load_score < settings.CLR_THRESHOLD_MEDIUM:
            fatigue_level = "medium"
        elif cognitive_load_score < settings.CLR_THRESHOLD_HIGH:
            fatigue_level = "high"
        else:
            fatigue_level = "critical"
        
        response = CognitiveLoadResponse(
            student_id=request.student_id,
            session_id=request.session_id,
            cognitive_load_score=cognitive_load_score,
            mental_fatigue_level=fatigue_level,
            timestamp=int(time.time())
        )
        
        logger.info(
            f"📊 Calculated cognitive load for student {request.student_id}: "
            f"{cognitive_load_score:.2f} ({fatigue_level})"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error calculating cognitive load: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/request-intervention", response_model=InterventionResponse)
async def request_intervention(request: RequestInterventionRequest):
    """
    Request immediate intervention for a student
    
    Triggers Motivation Agent and publishes intervention to Redis
    """
    
    try:
        intervention_id = str(uuid.uuid4())
        
        # Create intervention message
        intervention = {
            "intervention_id": intervention_id,
            "student_id": request.student_id,
            "intervention_type": "encouragement",
            "message": f"Intervention requested: {request.reason}",
            "priority": "high",
            "context": request.context,
            "timestamp": int(time.time())
        }
        
        # Publish to interventions channel
        await redis_client.publish_agent_event(
            "interventions",
            {
                "type": "intervention_triggered",
                "student_id": request.student_id,
                "intervention": intervention
            }
        )
        
        logger.info(f"🚨 Intervention requested for student {request.student_id}: {request.reason}")
        
        return InterventionResponse(**intervention)
        
    except Exception as e:
        logger.error(f"Error requesting intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/curriculum-adjustment", response_model=CurriculumAdjustmentResponse)
async def curriculum_adjustment(request: CurriculumAdjustmentRequest):
    """
    Trigger Curriculum Agent to adjust learning path
    
    Returns proposed curriculum changes
    """
    
    try:
        # Placeholder implementation
        adjustments = [
            {
                "type": "difficulty_adjustment",
                "reason": request.reason,
                "change": "moderate",
                "modules_affected": []
            }
        ]
        
        # Publish curriculum update
        await redis_client.publish_agent_event(
            "curriculum_updates",
            {
                "type": "curriculum_adjusted",
                "student_id": request.student_id,
                "learning_path_id": request.learning_path_id,
                "adjustments": adjustments
            }
        )
        
        logger.info(
            f"📚 Curriculum adjustment requested for student {request.student_id}, "
            f"path {request.learning_path_id}"
        )
        
        return CurriculumAdjustmentResponse(
            student_id=request.student_id,
            learning_path_id=request.learning_path_id,
            adjustments=adjustments,
            difficulty_change="moderate",
            estimated_duration_change=0
        )
        
    except Exception as e:
        logger.error(f"Error adjusting curriculum: {e}")
        raise HTTPException(status_code=500, detail=str(e))
