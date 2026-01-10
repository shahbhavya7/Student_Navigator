from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """Shared state for LangGraph agents"""
    
    # Identity
    student_id: str
    session_id: str
    timestamp: int
    
    # Behavioral data
    behavioral_events: List[Dict]
    aggregated_metrics: Dict
    
    # Cognitive load
    cognitive_load_score: float
    cognitive_load_history: List[float]
    mental_fatigue_level: str  # low, medium, high, critical
    
    # Performance data
    performance_metrics: Dict
    quiz_accuracy: float
    learning_velocity: float
    improvement_trend: str
    
    # Engagement data
    engagement_score: float
    session_duration: int
    interaction_depth: float
    dropout_risk: float
    
    # Curriculum state
    current_learning_path_id: str
    current_module_id: str
    curriculum_adjustments: List[Dict]
    difficulty_level: str
    
    # Intervention state
    interventions_triggered: List[Dict]
    last_intervention_time: int
    intervention_effectiveness: Dict
    
    # Agent execution tracking
    agents_executed: List[str]
    agent_outputs: Dict[str, Any]
    execution_errors: List[str]
    
    # Student profile
    student_profile: Optional[Dict]
    weak_topics: List[str]
    task_completion_rate: float
    return_frequency: Dict
    dropout_signals: List[str]
