"""
Intervention Types Configuration

Defines intervention type configurations including priorities,
cooldowns, and effectiveness metrics.
"""

from enum import Enum
from dataclasses import dataclass


class InterventionType(str, Enum):
    """Available intervention types"""
    BREAK_SUGGESTION = "break_suggestion"
    TOPIC_SWITCH = "topic_switch"
    RECAP_PROMPT = "recap_prompt"
    ENCOURAGEMENT = "encouragement"
    DIFFICULTY_ADJUSTMENT = "difficulty_adjustment"


class InterventionPriority(str, Enum):
    """Intervention priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EffectivenessMetric(str, Enum):
    """Metrics used to measure intervention effectiveness"""
    COGNITIVE_LOAD = "cognitive_load"
    ACCURACY = "accuracy"
    ENGAGEMENT = "engagement"
    MOOD = "mood"


@dataclass
class InterventionConfig:
    """Configuration for an intervention type"""
    type: InterventionType
    default_priority: InterventionPriority
    cooldown_minutes: int
    effectiveness_metric: EffectivenessMetric
    description: str


INTERVENTION_CONFIGS = {
    InterventionType.BREAK_SUGGESTION: InterventionConfig(
        type=InterventionType.BREAK_SUGGESTION,
        default_priority=InterventionPriority.HIGH,
        cooldown_minutes=30,
        effectiveness_metric=EffectivenessMetric.COGNITIVE_LOAD,
        description="Suggests taking a break when cognitive load is high or session is too long"
    ),
    
    InterventionType.TOPIC_SWITCH: InterventionConfig(
        type=InterventionType.TOPIC_SWITCH,
        default_priority=InterventionPriority.MEDIUM,
        cooldown_minutes=20,
        effectiveness_metric=EffectivenessMetric.ENGAGEMENT,
        description="Recommends switching topics when avoidance patterns or error clustering detected"
    ),
    
    InterventionType.RECAP_PROMPT: InterventionConfig(
        type=InterventionType.RECAP_PROMPT,
        default_priority=InterventionPriority.HIGH,
        cooldown_minutes=15,
        effectiveness_metric=EffectivenessMetric.ACCURACY,
        description="Prompts review of weak topics when quiz accuracy is low"
    ),
    
    InterventionType.ENCOURAGEMENT: InterventionConfig(
        type=InterventionType.ENCOURAGEMENT,
        default_priority=InterventionPriority.HIGH,
        cooldown_minutes=10,
        effectiveness_metric=EffectivenessMetric.MOOD,
        description="Provides encouragement when mood is negative or performance is declining"
    ),
    
    InterventionType.DIFFICULTY_ADJUSTMENT: InterventionConfig(
        type=InterventionType.DIFFICULTY_ADJUSTMENT,
        default_priority=InterventionPriority.MEDIUM,
        cooldown_minutes=45,
        effectiveness_metric=EffectivenessMetric.ACCURACY,
        description="Adjusts difficulty when student plateaus or consistently struggles"
    ),
}
