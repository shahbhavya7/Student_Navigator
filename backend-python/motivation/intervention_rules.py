"""
Intervention Rule Engine

Rule-based system that analyzes agent state and determines
which interventions should be triggered.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from agents.state import AgentState
from motivation.intervention_types import InterventionType, InterventionPriority
from config.settings import settings


@dataclass
class InterventionTrigger:
    """Represents a triggered intervention"""
    intervention_type: InterventionType
    priority: InterventionPriority
    trigger_reason: str
    context: Dict[str, Any]
    confidence: float  # 0-1 score indicating trigger confidence


class InterventionRuleEngine:
    """Evaluates rules and determines which interventions to trigger"""
    
    # Rule thresholds
    COGNITIVE_LOAD_CRITICAL = 80
    COGNITIVE_LOAD_HIGH = 70
    COGNITIVE_LOAD_MEDIUM = 50
    
    QUIZ_ACCURACY_LOW = 60
    QUIZ_ACCURACY_VERY_LOW = 40
    
    MOOD_FRUSTRATED = -0.5
    MOOD_CONFUSED = -0.2
    
    SESSION_DURATION_WARNING = 90  # minutes
    SESSION_DURATION_CRITICAL = 120
    
    DROPOUT_RISK_HIGH = 0.6
    DROPOUT_RISK_CRITICAL = 0.8
    
    def __init__(self):
        self.logger = logging.getLogger("InterventionRuleEngine")
    
    def evaluate_rules(self, state: AgentState) -> List[InterventionTrigger]:
        """
        Evaluate all intervention rules against current state.
        
        Args:
            state: Current agent state
            
        Returns:
            List of triggered interventions (deduplicated and prioritized)
        """
        triggers = []
        
        # Evaluate each rule category
        triggers.extend(self._check_cognitive_load_rules(state))
        triggers.extend(self._check_performance_rules(state))
        triggers.extend(self._check_avoidance_rules(state))
        triggers.extend(self._check_mood_rules(state))
        triggers.extend(self._check_time_based_rules(state))
        triggers.extend(self._check_dropout_risk_rules(state))
        
        # Deduplicate and filter based on throttling
        filtered_triggers = self._deduplicate_interventions(triggers, state)
        
        self.logger.info(
            f"Evaluated intervention rules: {len(triggers)} triggers, "
            f"{len(filtered_triggers)} after deduplication"
        )
        
        return filtered_triggers
    
    def _check_cognitive_load_rules(self, state: AgentState) -> List[InterventionTrigger]:
        """Check cognitive load based rules"""
        triggers = []
        cognitive_load = state.get("cognitive_load_score", 0)
        
        if cognitive_load >= self.COGNITIVE_LOAD_CRITICAL:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.BREAK_SUGGESTION,
                priority=InterventionPriority.CRITICAL,
                trigger_reason=f"Critical cognitive load: {cognitive_load}/100",
                context={
                    "cognitive_load": cognitive_load,
                    "fatigue_level": state.get("mental_fatigue_level", "unknown"),
                    "session_duration": state.get("session_duration_minutes", 0)
                },
                confidence=0.95
            ))
        elif cognitive_load >= self.COGNITIVE_LOAD_HIGH:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.BREAK_SUGGESTION,
                priority=InterventionPriority.HIGH,
                trigger_reason=f"High cognitive load: {cognitive_load}/100",
                context={
                    "cognitive_load": cognitive_load,
                    "fatigue_level": state.get("mental_fatigue_level", "unknown")
                },
                confidence=0.85
            ))
        
        return triggers
    
    def _check_performance_rules(self, state: AgentState) -> List[InterventionTrigger]:
        """Check performance-based rules"""
        triggers = []
        quiz_accuracy = state.get("quiz_accuracy", 100)
        plateau_detected = state.get("plateau_detected", False)
        weak_topics = state.get("weak_topics", [])
        
        if quiz_accuracy < self.QUIZ_ACCURACY_VERY_LOW:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.DIFFICULTY_ADJUSTMENT,
                priority=InterventionPriority.HIGH,
                trigger_reason=f"Very low quiz accuracy: {quiz_accuracy}%",
                context={
                    "quiz_accuracy": quiz_accuracy,
                    "weak_topics": weak_topics,
                    "plateau_detected": plateau_detected
                },
                confidence=0.9
            ))
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.RECAP_PROMPT,
                priority=InterventionPriority.HIGH,
                trigger_reason=f"Low performance requires review: {quiz_accuracy}%",
                context={
                    "quiz_accuracy": quiz_accuracy,
                    "weak_topics": weak_topics
                },
                confidence=0.85
            ))
        elif quiz_accuracy < self.QUIZ_ACCURACY_LOW and weak_topics:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.RECAP_PROMPT,
                priority=InterventionPriority.MEDIUM,
                trigger_reason=f"Quiz accuracy below threshold: {quiz_accuracy}%",
                context={
                    "quiz_accuracy": quiz_accuracy,
                    "weak_topics": weak_topics
                },
                confidence=0.75
            ))
        
        if plateau_detected:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.DIFFICULTY_ADJUSTMENT,
                priority=InterventionPriority.MEDIUM,
                trigger_reason="Learning plateau detected",
                context={
                    "plateau_detected": True,
                    "quiz_accuracy": quiz_accuracy,
                    "learning_velocity": state.get("learning_velocity", 0)
                },
                confidence=0.7
            ))
        
        return triggers
    
    def _check_avoidance_rules(self, state: AgentState) -> List[InterventionTrigger]:
        """Check avoidance pattern rules"""
        triggers = []
        avoidance_behavior = state.get("avoidance_behavior", {})
        cognitive_patterns = state.get("cognitive_patterns", {})
        
        # Check for topic avoidance
        if avoidance_behavior and isinstance(avoidance_behavior, dict):
            avoided_topics = avoidance_behavior.get("avoided_topics", [])
            if avoided_topics:
                triggers.append(InterventionTrigger(
                    intervention_type=InterventionType.TOPIC_SWITCH,
                    priority=InterventionPriority.MEDIUM,
                    trigger_reason=f"Topic avoidance detected: {len(avoided_topics)} topics",
                    context={
                        "avoided_topics": avoided_topics,
                        "avoidance_behavior": avoidance_behavior
                    },
                    confidence=0.75
                ))
        
        # Check for error clustering pattern
        if cognitive_patterns and isinstance(cognitive_patterns, dict):
            error_clustering = cognitive_patterns.get("error_clustering_detected", False)
            if error_clustering:
                triggers.append(InterventionTrigger(
                    intervention_type=InterventionType.TOPIC_SWITCH,
                    priority=InterventionPriority.HIGH,
                    trigger_reason="Error clustering pattern detected",
                    context={
                        "error_clustering": True,
                        "patterns": cognitive_patterns
                    },
                    confidence=0.8
                ))
        
        return triggers
    
    def _check_mood_rules(self, state: AgentState) -> List[InterventionTrigger]:
        """Check mood-based rules"""
        triggers = []
        mood_score = state.get("mood_score", 0)
        sentiment_trend = state.get("sentiment_trend", "neutral")
        
        if mood_score < self.MOOD_FRUSTRATED:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.ENCOURAGEMENT,
                priority=InterventionPriority.HIGH,
                trigger_reason=f"Negative mood detected: {mood_score:.2f}",
                context={
                    "mood_score": mood_score,
                    "sentiment_trend": sentiment_trend,
                    "dominant_emotion": state.get("dominant_emotion", "unknown")
                },
                confidence=0.85
            ))
        elif mood_score < self.MOOD_CONFUSED:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.ENCOURAGEMENT,
                priority=InterventionPriority.MEDIUM,
                trigger_reason=f"Slightly negative mood: {mood_score:.2f}",
                context={
                    "mood_score": mood_score,
                    "sentiment_trend": sentiment_trend
                },
                confidence=0.7
            ))
        
        return triggers
    
    def _check_time_based_rules(self, state: AgentState) -> List[InterventionTrigger]:
        """Check time-based rules (session duration, night degradation)"""
        triggers = []
        session_duration = state.get("session_duration_minutes", 0)
        time_of_day = state.get("time_of_day", "day")
        night_degradation = state.get("night_degradation_detected", False)
        
        if session_duration >= self.SESSION_DURATION_CRITICAL:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.BREAK_SUGGESTION,
                priority=InterventionPriority.CRITICAL,
                trigger_reason=f"Excessive session duration: {session_duration} minutes",
                context={
                    "session_duration": session_duration,
                    "time_of_day": time_of_day
                },
                confidence=0.9
            ))
        elif session_duration >= self.SESSION_DURATION_WARNING:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.BREAK_SUGGESTION,
                priority=InterventionPriority.HIGH,
                trigger_reason=f"Long session duration: {session_duration} minutes",
                context={
                    "session_duration": session_duration,
                    "time_of_day": time_of_day
                },
                confidence=0.8
            ))
        
        if night_degradation:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.BREAK_SUGGESTION,
                priority=InterventionPriority.HIGH,
                trigger_reason="Night degradation pattern detected",
                context={
                    "night_degradation": True,
                    "time_of_day": time_of_day,
                    "session_duration": session_duration
                },
                confidence=0.75
            ))
        
        return triggers
    
    def _check_dropout_risk_rules(self, state: AgentState) -> List[InterventionTrigger]:
        """Check dropout risk rules"""
        triggers = []
        dropout_risk = state.get("dropout_risk_score", 0)
        
        if dropout_risk >= self.DROPOUT_RISK_CRITICAL:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.ENCOURAGEMENT,
                priority=InterventionPriority.CRITICAL,
                trigger_reason=f"Critical dropout risk: {dropout_risk:.2%}",
                context={
                    "dropout_risk": dropout_risk,
                    "engagement_level": state.get("engagement_level", "unknown"),
                    "quiz_accuracy": state.get("quiz_accuracy", 0)
                },
                confidence=0.9
            ))
        elif dropout_risk >= self.DROPOUT_RISK_HIGH:
            triggers.append(InterventionTrigger(
                intervention_type=InterventionType.ENCOURAGEMENT,
                priority=InterventionPriority.HIGH,
                trigger_reason=f"High dropout risk: {dropout_risk:.2%}",
                context={
                    "dropout_risk": dropout_risk,
                    "engagement_level": state.get("engagement_level", "unknown")
                },
                confidence=0.8
            ))
        
        return triggers
    
    def _deduplicate_interventions(
        self, 
        triggers: List[InterventionTrigger],
        state: AgentState
    ) -> List[InterventionTrigger]:
        """
        Deduplicate interventions and apply throttling rules.
        
        Args:
            triggers: List of triggered interventions
            state: Current agent state
            
        Returns:
            Filtered list of interventions
        """
        if not triggers:
            return []
        
        # Get last intervention time
        last_intervention_time = state.get("last_intervention_time", 0)
        current_time = datetime.now().timestamp()
        minutes_since_last = (current_time - last_intervention_time) / 60
        
        # Group by intervention type (take highest priority for each type)
        type_map: Dict[InterventionType, InterventionTrigger] = {}
        for trigger in triggers:
            existing = type_map.get(trigger.intervention_type)
            if not existing or self._compare_priority(trigger.priority, existing.priority) > 0:
                type_map[trigger.intervention_type] = trigger
        
        # Apply throttling
        filtered = []
        for trigger in type_map.values():
            # Critical interventions bypass throttling if configured
            if (trigger.priority == InterventionPriority.CRITICAL and 
                settings.INTERVENTION_CRITICAL_BYPASS_THROTTLE):
                filtered.append(trigger)
                continue
            
            # Check minimum interval
            if minutes_since_last >= settings.INTERVENTION_MIN_INTERVAL_MINUTES:
                filtered.append(trigger)
            else:
                self.logger.debug(
                    f"Throttling {trigger.intervention_type}: "
                    f"{minutes_since_last:.1f} minutes since last intervention"
                )
        
        # Sort by priority (critical first)
        priority_order = {
            InterventionPriority.CRITICAL: 0,
            InterventionPriority.HIGH: 1,
            InterventionPriority.MEDIUM: 2,
            InterventionPriority.LOW: 3
        }
        filtered.sort(key=lambda t: (priority_order[t.priority], -t.confidence))
        
        return filtered
    
    def _compare_priority(
        self, 
        p1: InterventionPriority, 
        p2: InterventionPriority
    ) -> int:
        """Compare two priorities. Returns 1 if p1 > p2, -1 if p1 < p2, 0 if equal"""
        priority_values = {
            InterventionPriority.CRITICAL: 4,
            InterventionPriority.HIGH: 3,
            InterventionPriority.MEDIUM: 2,
            InterventionPriority.LOW: 1
        }
        v1 = priority_values[p1]
        v2 = priority_values[p2]
        if v1 > v2:
            return 1
        elif v1 < v2:
            return -1
        return 0
