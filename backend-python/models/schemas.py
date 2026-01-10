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


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response"""
    student_id: str
    quiz_accuracy: float
    learning_velocity: float
    improvement_trend: str
    task_completion_rate: float
    weak_topics: List[str]
    performance_insights: str
    timestamp: int


class ImprovementCurveResponse(BaseModel):
    """Improvement curve data for visualization"""
    student_id: str
    data_points: List[Dict[str, Any]]
    trend_line: List[float]
    velocity: float
    plateau_detected: bool
    confidence: float


class EngagementMetricsResponse(BaseModel):
    """Engagement metrics response"""
    student_id: str
    engagement_score: float
    session_duration_avg: int
    interaction_depth: float
    dropout_risk: float
    return_frequency: Dict[str, int]
    engagement_insights: str
    dropout_signals: List[str]
    timestamp: int


class StudentProfileResponse(BaseModel):
    """Comprehensive student profile response"""
    student_id: str
    cognitive_load_summary: Dict[str, Any]
    performance_summary: Dict[str, Any]
    engagement_summary: Dict[str, Any]
    combined_health_score: float
    risk_level: str
    recommended_actions: List[str]
    generated_at: str


class CurriculumStateResponse(BaseModel):
    """Current curriculum state response"""
    student_id: str
    learning_path_id: str
    title: str
    difficulty: str
    current_module_id: Optional[str]
    progress: float
    completed_modules: List[str]
    last_updated: Optional[str]
    last_accessed: Optional[str]
    recent_adjustments: List[Dict[str, Any]]


class LearningPathResponse(BaseModel):
    """Complete learning path structure"""
    learning_path_id: str
    modules: List[Dict[str, Any]]
    total_modules: int
    completed_count: int
    difficulty_distribution: Dict[str, int]
    avg_difficulty_score: float
    is_valid: bool


class AdjustmentRecommendation(BaseModel):
    """AI-generated curriculum adjustment recommendation"""
    type: str
    priority: str
    description: str
    reasoning: str
    estimated_impact: Dict[str, Any]
    confidence: float


class CurriculumHistoryResponse(BaseModel):
    """Curriculum adjustment history entry"""
    id: str
    learning_path_id: str
    change_type: str
    previous_state: Dict[str, Any]
    new_state: Dict[str, Any]
    reason: str
    created_at: Optional[str]


# ===== Content Generation Schemas =====

class GenerateContentRequest(BaseModel):
    """Request to generate educational content"""
    topic: str = Field(..., description="Content topic")
    content_type: str = Field(..., description="Type: lesson, quiz, exercise, recap")
    difficulty: str = Field(..., description="Difficulty: easy, medium, hard")
    student_id: str = Field(..., description="Student UUID")
    learning_path_id: str = Field(..., description="Learning path UUID")
    cognitive_load_profile: Dict[str, Any] = Field(..., description="Student's cognitive load data")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite topics")
    estimated_minutes: Optional[int] = Field(None, description="Target duration in minutes")


class GeneratedContentResponse(BaseModel):
    """Response with generated content"""
    content_id: str = Field(..., description="Generated content module ID")
    topic: str
    content_type: str
    difficulty: str
    content: str = Field(..., description="Content as JSON or Markdown")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    estimated_minutes: int
    prerequisites: List[str] = Field(default_factory=list)
    generated_at: str
    cached: bool = Field(False, description="Whether content was served from cache")


class ContentVariationRequest(BaseModel):
    """Request to generate content variation"""
    variation_type: str = Field(..., description="Type: easier, harder, alternative")
    cognitive_load_profile: Dict[str, Any] = Field(..., description="Current cognitive load")


class ContentVariationResponse(BaseModel):
    """Response with content variation"""
    original_content_id: str
    variation_content_id: str
    variation_type: str
    content: str
    difficulty_change: Optional[str] = None


class BatchGenerateRequest(BaseModel):
    """Request to generate multiple content modules"""
    topics: List[str] = Field(..., description="List of topics to generate")
    difficulty_progression: List[str] = Field(..., description="Difficulty for each topic")
    student_id: str
    learning_path_id: str
    cognitive_load_profile: Dict[str, Any]


class BatchGenerateResponse(BaseModel):
    """Response with batch generated content IDs"""
    generated_content_ids: List[str]
    total_generated: int
    failed_topics: List[str] = Field(default_factory=list)
    generation_time_seconds: float


class ContentModuleResponse(BaseModel):
    """Response with content module details"""
    id: str
    title: str
    content: str
    module_type: str
    difficulty: str
    estimated_minutes: int
    prerequisites: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContentSearchRequest(BaseModel):
    """Request to search content"""
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    content_type: Optional[str] = None
    learning_path_id: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)


class ContentCacheStatsResponse(BaseModel):
    """Cache performance statistics"""
    cache_hits: int
    cache_misses: int
    hit_rate_percent: float
    total_cached_items: int
    memory_used: str


