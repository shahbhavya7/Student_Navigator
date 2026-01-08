from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class BehaviorEventType(str, Enum):
    TASK_SWITCH = "TASK_SWITCH"
    TYPING_PATTERN = "TYPING_PATTERN"
    SCROLL_BEHAVIOR = "SCROLL_BEHAVIOR"
    MOUSE_MOVEMENT = "MOUSE_MOVEMENT"
    FOCUS_CHANGE = "FOCUS_CHANGE"
    NAVIGATION = "NAVIGATION"
    IDLE_TIME = "IDLE_TIME"
    QUIZ_ERROR = "QUIZ_ERROR"
    CONTENT_INTERACTION = "CONTENT_INTERACTION"
    TIME_TRACKING = "TIME_TRACKING"


class BehaviorEventSchema(BaseModel):
    id: str
    sessionId: str
    studentId: str
    eventType: BehaviorEventType
    eventData: Dict[str, Any]
    timestamp: int
    metadata: Optional[Dict[str, Any]] = None


class CognitiveLoadRequest(BaseModel):
    student_id: str = Field(..., description="Student UUID")
    session_id: str = Field(..., description="Session UUID")


class CognitiveLoadResponse(BaseModel):
    student_id: str
    session_id: str
    cognitive_load_score: float = Field(..., ge=0, le=100)
    mental_fatigue_level: str
    timestamp: int


class InterventionType(str, Enum):
    BREAK_SUGGESTION = "break_suggestion"
    ENCOURAGEMENT = "encouragement"
    RESOURCE_RECOMMENDATION = "resource_recommendation"
    DIFFICULTY_ADJUSTMENT = "difficulty_adjustment"
    PACE_ADJUSTMENT = "pace_adjustment"


class InterventionResponse(BaseModel):
    intervention_id: str
    student_id: str
    intervention_type: InterventionType
    message: str
    priority: str = Field(..., description="low, medium, high, critical")
    context: Dict[str, Any]
    timestamp: int


class CurriculumAdjustmentRequest(BaseModel):
    student_id: str
    learning_path_id: str
    reason: str
    context: Optional[Dict[str, Any]] = None


class CurriculumAdjustmentResponse(BaseModel):
    student_id: str
    learning_path_id: str
    adjustments: List[Dict[str, Any]]
    difficulty_change: Optional[str] = None
    estimated_duration_change: Optional[int] = None


class AgentExecutionStatus(BaseModel):
    workflow_id: str
    status: str = Field(..., description="running, completed, failed")
    student_id: str
    session_id: str
    agents_executed: List[str]
    current_agent: Optional[str] = None
    agent_outputs: Dict[str, Any]
    errors: List[str]
    started_at: int
    completed_at: Optional[int] = None


class TriggerWorkflowRequest(BaseModel):
    student_id: str
    session_id: str
    trigger_type: str = Field(..., description="session_end, quiz_completed, cognitive_threshold_breach, manual")


class TriggerWorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str


class RequestInterventionRequest(BaseModel):
    student_id: str
    reason: str
    context: Dict[str, Any]


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, str]


class AgentHealthResponse(BaseModel):
    status: str
    agents: Dict[str, Dict[str, Any]]
    workflow_stats: Dict[str, Any]
    pubsub_status: str
