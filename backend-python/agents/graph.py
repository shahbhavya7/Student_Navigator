from langgraph.graph import StateGraph, END
from typing import Dict, Any
import logging
import time

from agents.state import AgentState
from agents.base_agent import BaseAgent
from agents.clr_agent import CognitiveLoadRadarAgent
from agents.performance_agent import PerformanceAgent
from agents.engagement_agent import EngagementAgent
from agents.curriculum_agent import CurriculumAgent
from agents.motivation_agent import MotivationAgent
from analytics.performance_profile import PerformanceProfileGenerator
from config.redis_client import redis_client
from config.settings import settings

logger = logging.getLogger(__name__)


# Initialize agent instances
clr_agent_instance = CognitiveLoadRadarAgent()
performance_agent = PerformanceAgent("performance_agent")
engagement_agent = EngagementAgent("engagement_agent")
curriculum_agent = CurriculumAgent("curriculum_agent")
motivation_agent = MotivationAgent("motivation_agent")
profile_generator = PerformanceProfileGenerator()


# Node functions for LangGraph

async def fetch_behavioral_data_node(state: AgentState) -> AgentState:
    """Fetch behavioral events from Redis"""
    try:
        session_id = state["session_id"]
        events = await redis_client.get_behavioral_events(session_id)
        
        # Normalize events: map eventType to type, eventData to metadata
        normalized_events = []
        for e in events:
            normalized = {
                'type': e.get('eventType', e.get('type', 'unknown')),
                'timestamp': e.get('timestamp', 0),
                'duration': e.get('duration', 0),
                'metadata': e.get('eventData', e.get('metadata', {}))
            }
            
            # Ensure hasError is in metadata for error detection
            if 'eventData' in e:
                event_data = e['eventData']
                if isinstance(event_data, dict):
                    if 'hasError' in event_data:
                        normalized['metadata']['hasError'] = event_data['hasError']
                    if 'errorCount' in event_data:
                        normalized['metadata']['hasError'] = event_data['errorCount'] > 0
            
            # Copy any other relevant fields
            for key in ['sessionId', 'studentId']:
                if key in e:
                    normalized[key] = e[key]
            
            normalized_events.append(normalized)
        
        # Simple aggregation (matches EventAggregator logic) - using normalized events
        task_switches = sum(1 for e in normalized_events if e.get("type") == "TASK_SWITCH")
        errors = sum(1 for e in normalized_events if e.get("type") == "QUIZ_ERROR" or e.get("metadata", {}).get("hasError", False))
        idle_events = [e for e in normalized_events if e.get("type") == "IDLE_TIME"]
        
        total_idle = sum(e.get("duration", e.get("metadata", {}).get("idleDuration", 0)) for e in idle_events)
        
        aggregated_metrics = {
            "taskSwitchingFreq": task_switches / max(len(normalized_events), 1),
            "errorRate": errors / max(len(normalized_events), 1),
            "procrastinationScore": min(total_idle / 60000, 100),  # Convert to minutes
            "browsingDriftScore": 0.0,  # Placeholder
            "avgTimePerConcept": 30000,  # Placeholder
            "productivityScore": 50.0  # Placeholder
        }
        
        state["behavioral_events"] = normalized_events  # Use normalized events
        state["aggregated_metrics"] = aggregated_metrics
        
        logger.info(f"📊 Aggregated {len(normalized_events)} events for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error fetching behavioral data: {e}")
        state["behavioral_events"] = []
        state["aggregated_metrics"] = {}
    
    return state


async def clr_agent_node(state: AgentState) -> AgentState:
    """Execute Enhanced CLR Agent"""
    output_state = await clr_agent_instance.execute(state)
    state.update(output_state)
    state["agents_executed"].append("clr_agent")
    
    # Extract CLR result for backward compatibility
    if "clr_result" in output_state:
        clr_result = output_state["clr_result"]
        state["cognitive_load_score"] = clr_result.get("cognitive_load_score", 50)
        state["mental_fatigue_level"] = clr_result.get("mental_fatigue_level", "medium")
        state["agent_outputs"]["clr_agent"] = clr_result
    
    return state


async def performance_agent_node(state: AgentState) -> AgentState:
    """Execute Performance Agent"""
    output = await performance_agent.execute(state)
    state.update(output)
    state["agents_executed"].append("performance_agent")
    state["agent_outputs"]["performance_agent"] = output
    return state


async def engagement_agent_node(state: AgentState) -> AgentState:
    """Execute Engagement Agent"""
    output = await engagement_agent.execute(state)
    state.update(output)
    state["agents_executed"].append("engagement_agent")
    state["agent_outputs"]["engagement_agent"] = output
    return state


async def curriculum_agent_node(state: AgentState) -> AgentState:
    """Execute Curriculum Agent"""
    output = await curriculum_agent.execute(state)
    state.update(output)
    state["agents_executed"].append("curriculum_agent")
    state["agent_outputs"]["curriculum_agent"] = output
    return state


async def motivation_agent_node(state: AgentState) -> AgentState:
    """Execute Motivation Agent with comprehensive intervention logic"""
    output = await motivation_agent.execute(state)
    state.update(output)
    state["agents_executed"].append("motivation_agent")
    state["agent_outputs"]["motivation_agent"] = output
    return state


async def generate_profile_node(state: AgentState) -> AgentState:
    """Generate comprehensive student performance profile"""
    try:
        clr_data = state.get("clr_result", {})
        performance_data = {
            "quiz_accuracy": state.get("quiz_accuracy", 0),
            "learning_velocity": state.get("learning_velocity", 0),
            "improvement_trend": state.get("improvement_trend", "stable"),
            "weak_topics": state.get("weak_topics", []),
            "task_completion_rate": state.get("task_completion_rate", 0),
            "plateau_detected": state.get("plateau_detected", False)
        }
        engagement_data = {
            "engagement_score": state.get("engagement_score", 0),
            "dropout_risk": state.get("dropout_risk", 0),
            "session_frequency": state.get("session_frequency", 0),
            "interaction_depth": state.get("interaction_depth", 0),
            "dropout_signals": state.get("dropout_signals", [])
        }
        
        profile = profile_generator.generate_profile(
            state["student_id"], clr_data, performance_data, engagement_data
        )
        await profile_generator.store_profile(profile)
        
        # Add profile to state
        state["student_profile"] = {
            "combined_health_score": profile.combined_health_score,
            "risk_level": profile.risk_level,
            "recommended_actions": profile.recommended_actions,
            "cognitive_load_summary": profile.cognitive_load_summary,
            "performance_summary": profile.performance_summary,
            "engagement_summary": profile.engagement_summary
        }
        state["agents_executed"].append("generate_profile")
        
        logger.info(f"📋 Profile generated: Risk={profile.risk_level}, Health={profile.combined_health_score:.1f}")
        
    except Exception as e:
        logger.error(f"Error generating profile: {e}")
        state["student_profile"] = {}
    
    return state


def route_by_cognitive_load(state: AgentState) -> str:
    """Route workflow based on cognitive load, performance, and engagement thresholds"""
    cognitive_score = state.get("cognitive_load_score", 50)
    dropout_risk = state.get("dropout_risk", 0.0)
    improvement_trend = state.get("improvement_trend", "stable")
    
    # Critical intervention needed
    if cognitive_score >= settings.CLR_THRESHOLD_HIGH or dropout_risk > 0.7:
        return "motivation_agent"
    
    # Performance declining rapidly with medium-high dropout risk
    if improvement_trend == "declining" and dropout_risk > 0.5:
        return "motivation_agent"
    
    # Normal flow - analyze performance and engagement
    return "performance_agent"


def route_after_engagement(state: AgentState) -> str:
    """Route after engagement analysis"""
    dropout_risk = state.get("dropout_risk", 0.0)
    
    # High dropout risk - trigger motivation agent
    if dropout_risk > 0.6:
        return "motivation_agent"
    
    # Normal flow - continue to profile generation
    return "generate_profile"


# Build LangGraph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("fetch_data", fetch_behavioral_data_node)
workflow.add_node("clr_agent", clr_agent_node)
workflow.add_node("performance_agent", performance_agent_node)
workflow.add_node("engagement_agent", engagement_agent_node)
workflow.add_node("generate_profile", generate_profile_node)
workflow.add_node("curriculum_agent", curriculum_agent_node)
workflow.add_node("motivation_agent", motivation_agent_node)

# Add edges
workflow.set_entry_point("fetch_data")
workflow.add_edge("fetch_data", "clr_agent")

# Conditional routing after CLR
workflow.add_conditional_edges(
    "clr_agent",
    route_by_cognitive_load,
    {
        "performance_agent": "performance_agent",
        "motivation_agent": "motivation_agent"
    }
)

# Low/medium cognitive load path
workflow.add_edge("performance_agent", "engagement_agent")

# Conditional routing after engagement
workflow.add_conditional_edges(
    "engagement_agent",
    route_after_engagement,
    {
        "motivation_agent": "motivation_agent",
        "generate_profile": "generate_profile"
    }
)

workflow.add_edge("generate_profile", "curriculum_agent")
workflow.add_edge("curriculum_agent", END)

# High cognitive load path
workflow.add_edge("motivation_agent", "curriculum_agent")

# Compile graph
app = workflow.compile()


async def execute_agent_workflow(student_id: str, session_id: str) -> Dict[str, Any]:
    """Execute the complete agent workflow"""
    try:
        # Initialize state
        initial_state: AgentState = {
            "student_id": student_id,
            "session_id": session_id,
            "timestamp": int(time.time()),
            "behavioral_events": [],
            "aggregated_metrics": {},
            "cognitive_load_score": 0.0,
            "cognitive_load_history": [],
            "mental_fatigue_level": "unknown",
            "performance_metrics": {},
            "quiz_accuracy": 0.0,
            "learning_velocity": 0.0,
            "improvement_trend": "stable",
            "engagement_score": 0.0,
            "session_duration": 0,
            "interaction_depth": 0.0,
            "dropout_risk": 0.0,
            "current_learning_path_id": "",
            "current_module_id": "",
            "curriculum_adjustments": [],
            "difficulty_level": "medium",
            "interventions_triggered": [],
            "last_intervention_time": 0,
            "intervention_effectiveness": {},
            "agents_executed": [],
            "agent_outputs": {},
            "execution_errors": [],
            "student_profile": None,
            "weak_topics": [],
            "task_completion_rate": 0.0,
            "return_frequency": {},
            "dropout_signals": []
        }
        
        # Execute workflow
        logger.info(f"🚀 Starting agent workflow for student {student_id}, session {session_id}")
        final_state = await app.ainvoke(initial_state)
        
        logger.info(f"✅ Workflow completed. Agents executed: {final_state['agents_executed']}")
        
        return {
            "status": "completed",
            "agents_executed": final_state["agents_executed"],
            "cognitive_load_score": final_state.get("cognitive_load_score", 0),
            "interventions_triggered": final_state.get("interventions_triggered", []),
            "curriculum_adjustments": final_state.get("curriculum_adjustments", [])
        }
        
    except Exception as e:
        logger.error(f"❌ Workflow execution failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "agents_executed": []
        }
