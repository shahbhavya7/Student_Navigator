"""
Unit Tests for Motivation Agent

Tests intervention rule evaluation, message generation,
intervention delivery, and effectiveness tracking.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from agents.motivation_agent import MotivationAgent
from motivation.intervention_rules import InterventionRuleEngine, InterventionTrigger
from motivation.intervention_types import InterventionType, InterventionPriority
from agents.state import AgentState


@pytest.fixture
def motivation_agent():
    """Create Motivation Agent instance for testing."""
    return MotivationAgent()


@pytest.fixture
def rule_engine():
    """Create Intervention Rule Engine instance."""
    return InterventionRuleEngine()


@pytest.fixture
def high_cognitive_load_state():
    """Sample state with high cognitive load."""
    return {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'cognitive_load_score': 85,
        'mental_fatigue_level': 'high',
        'quiz_accuracy': 70,
        'session_duration_minutes': 45,
        'mood_score': 0,
        'last_intervention_time': 0,
        'agents_executed': [],
        'agent_outputs': {}
    }


@pytest.fixture
def low_performance_state():
    """Sample state with low performance."""
    return {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'cognitive_load_score': 50,
        'quiz_accuracy': 45,
        'weak_topics': ['functions', 'loops'],
        'plateau_detected': True,
        'last_intervention_time': 0,
        'agents_executed': [],
        'agent_outputs': {}
    }


@pytest.fixture
def negative_mood_state():
    """Sample state with negative mood."""
    return {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'cognitive_load_score': 55,
        'quiz_accuracy': 65,
        'mood_score': -0.6,
        'sentiment_trend': 'declining',
        'dropout_risk_score': 0.4,
        'last_intervention_time': 0,
        'agents_executed': [],
        'agent_outputs': {}
    }


# ============================================================================
# Intervention Rule Tests
# ============================================================================

def test_cognitive_load_critical_triggers_break(rule_engine, high_cognitive_load_state):
    """Test that critical cognitive load triggers break suggestion."""
    triggers = rule_engine.evaluate_rules(high_cognitive_load_state)
    
    assert len(triggers) > 0
    assert any(t.intervention_type == InterventionType.BREAK_SUGGESTION for t in triggers)
    
    break_trigger = next(t for t in triggers if t.intervention_type == InterventionType.BREAK_SUGGESTION)
    assert break_trigger.priority == InterventionPriority.CRITICAL


def test_low_performance_triggers_recap(rule_engine, low_performance_state):
    """Test that low quiz accuracy triggers recap prompt."""
    triggers = rule_engine.evaluate_rules(low_performance_state)
    
    assert len(triggers) > 0
    assert any(t.intervention_type == InterventionType.RECAP_PROMPT for t in triggers)


def test_negative_mood_triggers_encouragement(rule_engine, negative_mood_state):
    """Test that negative mood triggers encouragement."""
    triggers = rule_engine.evaluate_rules(negative_mood_state)
    
    assert len(triggers) > 0
    assert any(t.intervention_type == InterventionType.ENCOURAGEMENT for t in triggers)


def test_long_session_triggers_break(rule_engine):
    """Test that long session duration triggers break suggestion."""
    state = {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'cognitive_load_score': 60,
        'session_duration_minutes': 95,
        'last_intervention_time': 0
    }
    
    triggers = rule_engine.evaluate_rules(state)
    
    assert any(t.intervention_type == InterventionType.BREAK_SUGGESTION for t in triggers)


def test_dropout_risk_triggers_encouragement(rule_engine):
    """Test that high dropout risk triggers encouragement."""
    state = {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'dropout_risk_score': 0.7,
        'engagement_level': 'low',
        'last_intervention_time': 0
    }
    
    triggers = rule_engine.evaluate_rules(state)
    
    assert any(t.intervention_type == InterventionType.ENCOURAGEMENT for t in triggers)


def test_no_triggers_for_healthy_state(rule_engine):
    """Test that no interventions trigger for healthy student state."""
    state = {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'cognitive_load_score': 45,
        'quiz_accuracy': 85,
        'mood_score': 0.3,
        'session_duration_minutes': 30,
        'dropout_risk_score': 0.1,
        'last_intervention_time': 0
    }
    
    triggers = rule_engine.evaluate_rules(state)
    
    assert len(triggers) == 0


# ============================================================================
# Throttling Tests
# ============================================================================

def test_throttling_prevents_rapid_interventions(rule_engine):
    """Test that throttling prevents interventions too close together."""
    import time
    
    state = {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'cognitive_load_score': 75,
        'last_intervention_time': int(time.time()) - 120,  # 2 minutes ago
        'agents_executed': [],
        'agent_outputs': {}
    }
    
    triggers = rule_engine.evaluate_rules(state)
    filtered_triggers = rule_engine._deduplicate_interventions(triggers, state)
    
    # Should be throttled since only 2 minutes passed (min is 5)
    assert len(filtered_triggers) == 0


def test_critical_intervention_bypasses_throttling(rule_engine):
    """Test that critical interventions bypass throttling."""
    import time
    from config.settings import settings
    
    # Only test if bypass is enabled
    if not settings.INTERVENTION_CRITICAL_BYPASS_THROTTLE:
        pytest.skip("Critical bypass not enabled")
    
    state = {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'cognitive_load_score': 95,
        'last_intervention_time': int(time.time()) - 60,  # 1 minute ago
        'agents_executed': [],
        'agent_outputs': {}
    }
    
    triggers = rule_engine.evaluate_rules(state)
    filtered_triggers = rule_engine._deduplicate_interventions(triggers, state)
    
    # Critical intervention should still be allowed
    assert any(t.priority == InterventionPriority.CRITICAL for t in filtered_triggers)


# ============================================================================
# Motivation Agent Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_motivation_agent_execution(motivation_agent, high_cognitive_load_state):
    """Test end-to-end motivation agent execution."""
    with patch.object(motivation_agent.intervention_storage, 'store_intervention') as mock_store, \
         patch.object(motivation_agent, '_publish_intervention') as mock_publish:
        
        mock_store.return_value = "intervention_123"
        mock_publish.return_value = None
        
        result = await motivation_agent.execute(high_cognitive_load_state)
        
        assert 'interventions_triggered' in result
        assert 'last_intervention_time' in result
        assert len(result['interventions_triggered']) > 0


@pytest.mark.asyncio
async def test_message_generation_uses_llm(motivation_agent):
    """Test that personalized messages are generated using LLM."""
    context = {
        'cognitive_load': 85,
        'session_duration': 90,
        'fatigue_level': 'high'
    }
    student_profile = {
        'student_id': 'student_123',
        'progress': 45
    }
    
    with patch.object(motivation_agent.message_generator, 'generate_message') as mock_gen:
        mock_gen.return_value = "You've been working intensely for 90 minutes. Take a short break!"
        
        message = await motivation_agent._generate_personalized_message(
            intervention_type=InterventionType.BREAK_SUGGESTION,
            context=context,
            student_profile=student_profile
        )
        
        assert len(message) > 0
        assert isinstance(message, str)
        mock_gen.assert_called_once_with(
            intervention_type=InterventionType.BREAK_SUGGESTION,
            context=context,
            student_profile=student_profile
        )


@pytest.mark.asyncio
async def test_intervention_published_to_redis(motivation_agent, high_cognitive_load_state):
    """Test that interventions are published to Redis."""
    with patch.object(motivation_agent, '_publish_intervention') as mock_publish, \
         patch.object(motivation_agent.intervention_storage, 'store_intervention') as mock_store:
        
        mock_store.return_value = "intervention_123"
        mock_publish.return_value = None
        
        await motivation_agent.execute(high_cognitive_load_state)
        
        # Verify publish was called
        assert mock_publish.called


@pytest.mark.asyncio
async def test_no_interventions_for_healthy_state(motivation_agent):
    """Test that no interventions are triggered for healthy state."""
    healthy_state = {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'cognitive_load_score': 40,
        'quiz_accuracy': 90,
        'mood_score': 0.5,
        'session_duration_minutes': 20,
        'last_intervention_time': 0,
        'agents_executed': [],
        'agent_outputs': {}
    }
    
    result = await motivation_agent.execute(healthy_state)
    
    assert len(result['interventions_triggered']) == 0


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_agent_handles_missing_state_fields(motivation_agent):
    """Test that agent handles missing state fields gracefully."""
    minimal_state = {
        'student_id': 'student_123',
        'session_id': 'session_456',
        'agents_executed': [],
        'agent_outputs': {}
    }
    
    # Should not crash with minimal state
    result = await motivation_agent.execute(minimal_state)
    
    assert 'interventions_triggered' in result


@pytest.mark.asyncio
async def test_fallback_message_on_llm_failure(motivation_agent):
    """Test that fallback messages are used when LLM fails."""
    context = {'cognitive_load': 85}
    student_profile = {'student_id': 'student_123'}
    
    with patch.object(motivation_agent.message_generator, 'generate_message') as mock_gen:
        mock_gen.side_effect = Exception("LLM service unavailable")
        
        message = await motivation_agent._generate_personalized_message(
            intervention_type=InterventionType.BREAK_SUGGESTION,
            context=context,
            student_profile=student_profile
        )
        
        # Should return fallback message, not crash
        assert len(message) > 0
        assert isinstance(message, str)


def test_intervention_deduplication(rule_engine):
    """Test that duplicate intervention types are deduplicated."""
    triggers = [
        InterventionTrigger(
            intervention_type=InterventionType.BREAK_SUGGESTION,
            priority=InterventionPriority.HIGH,
            trigger_reason="High load",
            context={},
            confidence=0.8
        ),
        InterventionTrigger(
            intervention_type=InterventionType.BREAK_SUGGESTION,
            priority=InterventionPriority.CRITICAL,
            trigger_reason="Critical load",
            context={},
            confidence=0.9
        ),
    ]
    
    state = {
        'last_intervention_time': 0,
        'student_id': 'student_123'
    }
    
    filtered = rule_engine._deduplicate_interventions(triggers, state)
    
    # Should keep only one break suggestion (the critical one)
    break_triggers = [t for t in filtered if t.intervention_type == InterventionType.BREAK_SUGGESTION]
    assert len(break_triggers) == 1
    assert break_triggers[0].priority == InterventionPriority.CRITICAL


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
