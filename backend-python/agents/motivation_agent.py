"""
Comprehensive Motivation Agent

Orchestrates dynamic intervention system with rule-based triggers,
LLM-powered personalized messaging, and effectiveness tracking.
"""

from typing import Dict, Any, List
import logging
import time
from datetime import datetime

from agents.base_agent import BaseAgent
from agents.state import AgentState
from motivation.intervention_rules import InterventionRuleEngine, InterventionTrigger
from motivation.message_generator import PersonalizedMessageGenerator
from motivation.effectiveness_tracker import InterventionEffectivenessTracker
from services.intervention_storage import InterventionStorageService
from config.redis_client import redis_client
from config.settings import settings


class MotivationAgent(BaseAgent):
    """Agent for triggering and delivering personalized interventions"""
    
    def __init__(self, name: str = "motivation_agent"):
        super().__init__(name)
        self.rule_engine = InterventionRuleEngine()
        self.message_generator = PersonalizedMessageGenerator(self.llm)
        self.intervention_storage = InterventionStorageService()
        self.effectiveness_tracker = InterventionEffectivenessTracker()
        self.logger = logging.getLogger("MotivationAgent")
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute motivation agent: evaluate rules, generate messages, deliver interventions.
        
        Args:
            state: Current agent state
            
        Returns:
            Dict with interventions_triggered and last_intervention_time
        """
        try:
            self.logger.info(
                f"🚨 Executing Motivation Agent for student {state.get('student_id')}"
            )
            
            # Evaluate intervention rules
            triggered_interventions = self.rule_engine.evaluate_rules(state)
            
            if not triggered_interventions:
                self.logger.info("No interventions triggered")
                return {
                    "interventions_triggered": [],
                    "last_intervention_time": state.get("last_intervention_time", 0)
                }
            
            # Capture pre-intervention metrics
            pre_metrics = self._capture_current_metrics(state)
            
            # Process each triggered intervention
            delivered_interventions = []
            for trigger in triggered_interventions:
                try:
                    intervention = await self._process_intervention(
                        trigger=trigger,
                        state=state,
                        pre_metrics=pre_metrics
                    )
                    if intervention:
                        delivered_interventions.append(intervention)
                except Exception as e:
                    self.logger.error(f"Failed to process intervention: {e}", exc_info=True)
                    continue
            
            # Update state - only update last_intervention_time if interventions were delivered
            current_time = int(time.time())
            output = {
                "interventions_triggered": delivered_interventions,
                "last_intervention_time": current_time if delivered_interventions else state.get("last_intervention_time", 0)
            }
            
            self.logger.info(
                f"✅ Delivered {len(delivered_interventions)} interventions"
            )
            
            self.log_execution(state, output)
            return output
            
        except Exception as e:
            self.log_error(e, state)
            return {
                "interventions_triggered": [],
                "last_intervention_time": state.get("last_intervention_time", 0)
            }
    
    async def _process_intervention(
        self,
        trigger: InterventionTrigger,
        state: AgentState,
        pre_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single intervention: generate message, store, publish.
        
        Args:
            trigger: Intervention trigger
            state: Current agent state
            pre_metrics: Metrics before intervention
            
        Returns:
            Dict with intervention data
        """
        student_id = state["student_id"]
        session_id = state["session_id"]
        
        self.logger.info(
            f"🚨 Processing intervention: type={trigger.intervention_type}, "
            f"priority={trigger.priority}, reason={trigger.trigger_reason}"
        )
        
        # Check if should throttle
        if self._should_throttle_intervention(state, trigger.priority):
            self.logger.debug(f"Throttling {trigger.intervention_type}")
            return None
        
        # Build student profile for message generation
        student_profile = self._build_student_profile(state)
        
        # Generate personalized message using LLM
        message = await self._generate_personalized_message(
            intervention_type=trigger.intervention_type,
            context=trigger.context,
            student_profile=student_profile
        )
        
        # Create intervention record
        intervention_record = self._create_intervention_record(
            student_id=student_id,
            session_id=session_id,
            intervention_type=trigger.intervention_type,
            message=message,
            context=trigger.context,
            priority=trigger.priority
        )
        
        # Store in PostgreSQL
        try:
            intervention_id = await self.intervention_storage.store_intervention(
                intervention_record
            )
            intervention_record["id"] = intervention_id
        except Exception as e:
            self.logger.error(f"Failed to store intervention: {e}")
            # Continue anyway - delivery is more important than storage
        
        # Publish to Redis for Node.js to deliver via WebSocket
        await self._publish_intervention(intervention_record)
        
        # Schedule effectiveness measurement
        if "id" in intervention_record:
            await self.effectiveness_tracker.schedule_effectiveness_measurement(
                intervention_id=intervention_record["id"],
                student_id=student_id,
                intervention_time=intervention_record["timestamp"],
                intervention_type=trigger.intervention_type,
                pre_metrics=pre_metrics
            )
        
        return intervention_record
    
    async def _generate_personalized_message(
        self,
        intervention_type: str,
        context: Dict[str, Any],
        student_profile: Dict[str, Any]
    ) -> str:
        """
        Generate personalized intervention message using LLM.
        
        Args:
            intervention_type: Type of intervention
            context: Context data for message generation
            student_profile: Student profile information
            
        Returns:
            Personalized message string
        """
        try:
            message = await self.message_generator.generate_message(
                intervention_type=intervention_type,
                context=context,
                student_profile=student_profile
            )
            
            self.logger.info(
                f"Generated personalized message for {intervention_type}: "
                f"{message[:50]}..."
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"Message generation failed: {e}", exc_info=True)
            # Return fallback message
            return self.message_generator._get_fallback_message(intervention_type)
    
    def _create_intervention_record(
        self,
        student_id: str,
        session_id: str,
        intervention_type: str,
        message: str,
        context: Dict[str, Any],
        priority: str
    ) -> Dict[str, Any]:
        """
        Create intervention record dict.
        
        Args:
            student_id: Student UUID
            session_id: Session UUID
            intervention_type: Type of intervention
            message: Personalized message
            context: Trigger context
            priority: Intervention priority
            
        Returns:
            Dict with intervention data
        """
        return {
            "student_id": student_id,
            "session_id": session_id,
            "intervention_type": intervention_type,
            "priority": priority,
            "message": message,
            "context": context,
            "timestamp": int(time.time()),
            "delivered_at": datetime.now()
        }
    
    async def _publish_intervention(self, intervention: Dict[str, Any]):
        """
        Publish intervention to Redis for Node.js backend to deliver.
        
        Args:
            intervention: Intervention record dict
        """
        try:
            intervention_id = intervention.get("id", "unknown")
            event_data = {
                "type": "intervention_triggered",
                "student_id": intervention["student_id"],
                "session_id": intervention["session_id"],
                "intervention": {
                    "id": intervention_id,
                    "intervention_id": intervention_id,
                    "type": intervention["intervention_type"],
                    "priority": intervention["priority"],
                    "message": intervention["message"],
                    "timestamp": intervention["timestamp"],
                    "context": intervention["context"]
                }
            }
            
            await redis_client.publish_agent_event("interventions", event_data)
            
            self.logger.info(
                f"📤 Published intervention to Redis: "
                f"type={intervention['intervention_type']}, "
                f"priority={intervention['priority']}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to publish intervention to Redis: {e}", exc_info=True)
            raise
    
    def _should_throttle_intervention(self, state: AgentState, priority: str) -> bool:
        """
        Check if intervention should be throttled based on timing.
        
        Args:
            state: Current agent state
            priority: Intervention priority
            
        Returns:
            True if should throttle, False otherwise
        """
        # Critical interventions bypass throttling if configured
        if (priority == "critical" and 
            settings.INTERVENTION_CRITICAL_BYPASS_THROTTLE):
            return False
        
        # Check last intervention time
        last_intervention_time = state.get("last_intervention_time", 0)
        if last_intervention_time == 0:
            return False
        
        current_time = time.time()
        minutes_since_last = (current_time - last_intervention_time) / 60
        
        if minutes_since_last < settings.INTERVENTION_MIN_INTERVAL_MINUTES:
            self.logger.debug(
                f"Throttling intervention: {minutes_since_last:.1f} minutes since last"
            )
            return True
        
        return False
    
    def _build_student_profile(self, state: AgentState) -> Dict[str, Any]:
        """
        Build student profile dict for message generation.
        
        Args:
            state: Current agent state
            
        Returns:
            Dict with student profile data
        """
        return {
            "student_id": state.get("student_id"),
            "progress": state.get("progress", 0),
            "learning_path_id": state.get("learning_path_id"),
            "current_module": state.get("current_module_id"),
            "completed_modules": state.get("completed_modules", []),
        }
    
    def _capture_current_metrics(self, state: AgentState) -> Dict[str, Any]:
        """
        Capture current metrics for pre-intervention baseline.
        
        Args:
            state: Current agent state
            
        Returns:
            Dict with current metrics
        """
        return {
            "cognitive_load": state.get("cognitive_load_score", 50),
            "quiz_accuracy": state.get("quiz_accuracy", 70),
            "engagement_score": state.get("engagement_score", 50),
            "mood_score": state.get("mood_score", 0),
            "learning_velocity": state.get("learning_velocity", 1.0),
            "session_duration": state.get("session_duration_minutes", 0),
        }
