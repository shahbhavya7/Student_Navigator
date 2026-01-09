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


# CLR-specific Pydantic schemas

class CLRCurrentResponse(BaseModel):
    """Current cognitive load data response"""
    student_id: str
    cognitive_load_score: float = Field(..., ge=0, le=100)
    mental_fatigue_level: str
    detected_patterns: List[str]
    mood_indicators: Dict[str, Any]
    timestamp: int
    session_id: str


class CLRHistoryResponse(BaseModel):
    """Cognitive load history response"""
    student_id: str
    time_range: str
    granularity: str
    history: List[Dict[str, Any]]
    statistics: Dict[str, float]
    trend: str
    trend_slope: float
    data_points: int


class CLRInsightsResponse(BaseModel):
    """AI-generated insights response"""
    student_id: str
    insights: str
    recommendations: List[str]
    generated_at: int


class CLRPatternsResponse(BaseModel):
    """Detected patterns analysis response"""
    student_id: str
    days_analyzed: int
    patterns: Dict[str, int]
    most_common_pattern: Optional[str]
    total_pattern_detections: int


class CLRBaselineResponse(BaseModel):
    """Baseline metrics response"""
    student_id: str
    baseline_avg: float
    baseline_std: float
    baseline_range: Dict[str, float]
    current_score: Optional[float]
    deviation_from_baseline: Optional[float]
    common_patterns: List[Any]
    data_points: int
    calculated_at: str


class TextAnalysisRequest(BaseModel):
    """Text mood analysis request"""
    student_id: str
    text: str
    context: str = ""


class TextAnalysisResponse(BaseModel):
    """Text mood analysis response"""
    student_id: str
    mood_score: float = Field(..., ge=-1, le=1)
    dominant_emotion: str
    confidence: float = Field(..., ge=0, le=1)
    explanation: str


class CLRPredictionResponse(BaseModel):
    """Cognitive load prediction response"""
    student_id: str
    predicted_load_15min: float
    predicted_load_30min: float
    trend: str
    confidence: float
    early_intervention_needed: bool
    recommendations: List[str] = []


class CLRDashboardResponse(BaseModel):
    """Comprehensive dashboard response"""
    student_id: str
    current: CLRCurrentResponse
    history: CLRHistoryResponse
    insights: CLRInsightsResponse
    patterns: CLRPatternsResponse
    baseline: CLRBaselineResponse
    predictions: CLRPredictionResponse
    timestamp: int

