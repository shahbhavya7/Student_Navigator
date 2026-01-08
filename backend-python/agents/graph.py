from langgraph.graph import StateGraph, END
from typing import Dict, Any
import logging
import time

from agents.state import AgentState
from agents.base_agent import BaseAgent
from config.redis_client import redis_client
from config.settings import settings

logger = logging.getLogger(__name__)


# Placeholder agent implementations (to be expanded in future phases)

class CLRAgent(BaseAgent):
    """Cognitive Load Recognition Agent"""
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """Calculate cognitive load score from behavioral metrics"""
        try:
            metrics = state.get("aggregated_metrics", {})
            
            # Weighted cognitive load calculation
            weights = {
                "taskSwitchingFreq": 0.25,
                "errorRate": 0.20,
                "procrastinationScore": 0.20,
                "browsingDriftScore": 0.15,
                "avgTimePerConcept": 0.10,
                "productivityScore": 0.10
            }
            
            task_switching = min(metrics.get("taskSwitchingFreq", 0) * 10, 100)
            error_rate = metrics.get("errorRate", 0) * 100
            procrastination = min(metrics.get("procrastinationScore", 0), 100)
            browsing_drift = metrics.get("browsingDriftScore", 0) * 100
            time_per_concept = min((metrics.get("avgTimePerConcept", 0) / 60000) * 20, 100)
            productivity = 100 - metrics.get("productivityScore", 50)
            
            cognitive_load = (
                task_switching * weights["taskSwitchingFreq"] +
                error_rate * weights["errorRate"] +
                procrastination * weights["procrastinationScore"] +
                browsing_drift * weights["browsingDriftScore"] +
                time_per_concept * weights["avgTimePerConcept"] +
                productivity * weights["productivityScore"]
            )
            
            cognitive_load = max(0, min(cognitive_load, 100))
            
            # Determine mental fatigue level
            if cognitive_load < settings.CLR_THRESHOLD_LOW:
                fatigue_level = "low"
            elif cognitive_load < settings.CLR_THRESHOLD_MEDIUM:
                fatigue_level = "medium"
            elif cognitive_load < settings.CLR_THRESHOLD_HIGH:
                fatigue_level = "high"
            else:
                fatigue_level = "critical"
            
            output = {
                "cognitive_load_score": cognitive_load,
                "mental_fatigue_level": fatigue_level
            }
            
            self.log_execution(state, output)
            await self.publish_event("cognitive_load_calculated", output)
            
            return output
            
        except Exception as e:
            self.log_error(e, state)
            return {"cognitive_load_score": 50.0, "mental_fatigue_level": "medium"}


class PerformanceAgent(BaseAgent):
    """Performance Analysis Agent"""
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """Analyze student performance metrics"""
        try:
            # Placeholder implementation
            metrics = state.get("aggregated_metrics", {})
            
            output = {
                "performance_metrics": {
                    "quiz_accuracy": state.get("quiz_accuracy", 0.0),
                    "learning_velocity": metrics.get("productivityScore", 50) / 100,
                    "improvement_trend": "stable"
                }
            }
            
            self.log_execution(state, output)
            return output
            
        except Exception as e:
            self.log_error(e, state)
            return {"performance_metrics": {}}


class EngagementAgent(BaseAgent):
    """Student Engagement Agent"""
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """Calculate engagement score"""
        try:
            metrics = state.get("aggregated_metrics", {})
            
            # Simple engagement calculation
            engagement_score = (
                (100 - metrics.get("procrastinationScore", 50)) * 0.4 +
                (100 - metrics.get("browsingDriftScore", 0.5) * 100) * 0.3 +
                metrics.get("productivityScore", 50) * 0.3
            )
            
            output = {
                "engagement_score": engagement_score,
                "dropout_risk": 1 - (engagement_score / 100)
            }
            
            self.log_execution(state, output)
            return output
            
        except Exception as e:
            self.log_error(e, state)
            return {"engagement_score": 50.0, "dropout_risk": 0.5}


class CurriculumAgent(BaseAgent):
    """Curriculum Adjustment Agent"""
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """Adjust learning path based on cognitive load and performance"""
        try:
            cognitive_load = state.get("cognitive_load_score", 50)
            
            adjustments = []
            
            if cognitive_load > settings.CLR_THRESHOLD_HIGH:
                adjustments.append({
                    "type": "difficulty_reduction",
                    "reason": "High cognitive load detected",
                    "adjustment": "Reduce difficulty by one level"
                })
            elif cognitive_load < settings.CLR_THRESHOLD_LOW:
                adjustments.append({
                    "type": "difficulty_increase",
                    "reason": "Low cognitive load - student ready for challenge",
                    "adjustment": "Increase difficulty by one level"
                })
            
            output = {
                "curriculum_adjustments": adjustments,
                "difficulty_level": "medium"  # Placeholder
            }
            
            self.log_execution(state, output)
            await self.publish_event("curriculum_adjusted", output)
            
            return output
            
        except Exception as e:
            self.log_error(e, state)
            return {"curriculum_adjustments": []}


class MotivationAgent(BaseAgent):
    """Motivation & Intervention Agent"""
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """Generate interventions for high cognitive load"""
        try:
            cognitive_load = state.get("cognitive_load_score", 50)
            fatigue_level = state.get("mental_fatigue_level", "medium")
            
            interventions = []
            
            if cognitive_load >= settings.CLR_THRESHOLD_HIGH:
                interventions.append({
                    "type": "break_suggestion",
                    "priority": "high",
                    "message": "You've been working hard! Consider taking a 5-minute break.",
                    "timestamp": int(time.time())
                })
            
            if fatigue_level == "critical":
                interventions.append({
                    "type": "encouragement",
                    "priority": "critical",
                    "message": "Great effort! Let's adjust the pace to help you succeed.",
                    "timestamp": int(time.time())
                })
            
            # Publish interventions to Redis for Node.js to deliver
            for intervention in interventions:
                await redis_client.publish_agent_event(
                    "interventions",
                    {
                        "type": "intervention_triggered",
                        "student_id": state["student_id"],
                        "session_id": state["session_id"],
                        "intervention": intervention
                    }
                )
            
            output = {
                "interventions_triggered": interventions,
                "last_intervention_time": int(time.time())
            }
            
            self.log_execution(state, output)
            return output
            
        except Exception as e:
            self.log_error(e, state)
            return {"interventions_triggered": []}


# Initialize agent instances
clr_agent = CLRAgent("clr_agent")
performance_agent = PerformanceAgent("performance_agent")
engagement_agent = EngagementAgent("engagement_agent")
curriculum_agent = CurriculumAgent("curriculum_agent")
motivation_agent = MotivationAgent("motivation_agent")


# Node functions for LangGraph

async def fetch_behavioral_data_node(state: AgentState) -> AgentState:
    """Fetch behavioral events from Redis"""
    try:
        session_id = state["session_id"]
        events = await redis_client.get_behavioral_events(session_id)
        
        # Simple aggregation (matches EventAggregator logic)
        task_switches = sum(1 for e in events if e.get("eventType") == "TASK_SWITCH")
        errors = sum(1 for e in events if e.get("eventType") == "QUIZ_ERROR")
        idle_events = [e for e in events if e.get("eventType") == "IDLE_TIME"]
        
        total_idle = sum(e.get("eventData", {}).get("idleDuration", 0) for e in idle_events)
        
        aggregated_metrics = {
            "taskSwitchingFreq": task_switches / max(len(events), 1),
            "errorRate": errors / max(len(events), 1),
            "procrastinationScore": min(total_idle / 60000, 100),  # Convert to minutes
            "browsingDriftScore": 0.0,  # Placeholder
            "avgTimePerConcept": 30000,  # Placeholder
            "productivityScore": 50.0  # Placeholder
        }
        
        state["behavioral_events"] = events
        state["aggregated_metrics"] = aggregated_metrics
        
        logger.info(f"📊 Aggregated {len(events)} events for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error fetching behavioral data: {e}")
        state["behavioral_events"] = []
        state["aggregated_metrics"] = {}
    
    return state


async def clr_agent_node(state: AgentState) -> AgentState:
    """Execute CLR Agent"""
    output = await clr_agent.execute(state)
    state.update(output)
    state["agents_executed"].append("clr_agent")
    state["agent_outputs"]["clr_agent"] = output
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
    """Execute Motivation Agent"""
    output = await motivation_agent.execute(state)
    state.update(output)
    state["agents_executed"].append("motivation_agent")
    state["agent_outputs"]["motivation_agent"] = output
    return state


def route_by_cognitive_load(state: AgentState) -> str:
    """Route workflow based on cognitive load thresholds"""
    score = state.get("cognitive_load_score", 50)
    
    if score < settings.CLR_THRESHOLD_MEDIUM:
        return "performance_agent"
    elif score < settings.CLR_THRESHOLD_HIGH:
        return "performance_agent"  # Will also trigger curriculum
    else:
        return "motivation_agent"  # Critical intervention


# Build LangGraph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("fetch_data", fetch_behavioral_data_node)
workflow.add_node("clr_agent", clr_agent_node)
workflow.add_node("performance_agent", performance_agent_node)
workflow.add_node("engagement_agent", engagement_agent_node)
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
workflow.add_edge("engagement_agent", "curriculum_agent")
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
            "execution_errors": []
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
