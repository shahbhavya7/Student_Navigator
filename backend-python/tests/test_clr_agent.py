"""
Unit Tests for CLR Agent

Tests cognitive load calculation, pattern detection, and mood analysis.
"""

import sys
import os
# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from agents.clr_agent import CognitiveLoadRadarAgent
from agents.state import AgentState


@pytest.fixture
def clr_agent():
    """Create CLR Agent instance for testing."""
    return CognitiveLoadRadarAgent()


@pytest.fixture
def sample_events():
    """Sample behavioral events for testing."""
    base_time = int(datetime.now().timestamp() * 1000)
    
    return [
        {
            'id': '1',
            'type': 'NAVIGATION',
            'timestamp': base_time,
            'duration': 5000,
            'metadata': {}
        },
        {
            'id': '2',
            'type': 'NAVIGATION',
            'timestamp': base_time + 30000,
            'duration': 3000,
            'metadata': {}
        },
        {
            'id': '3',
            'type': 'NAVIGATION',
            'timestamp': base_time + 60000,
            'duration': 2000,
            'metadata': {}
        },
        {
            'id': '4',
            'type': 'TYPING_PATTERN',
            'timestamp': base_time + 90000,
            'duration': 10000,
            'metadata': {
                'wpm': 35,
                'backspaceRate': 0.15,
                'pauses': 5
            }
        },
        {
            'id': '5',
            'type': 'IDLE',
            'timestamp': base_time + 120000,
            'duration': 60000,
            'metadata': {}
        }
    ]


class TestCLRAgent:
    """Test CLR Agent functionality."""
    
    def test_agent_initialization(self, clr_agent):
        """Test agent initializes correctly."""
        assert clr_agent is not None
        assert clr_agent.pattern_detector is not None
        assert clr_agent.mood_analyzer is not None
    
    def test_basic_metrics_calculation(self, clr_agent, sample_events):
        """Test basic weighted metrics calculation."""
        score = clr_agent._calculate_basic_metrics(sample_events)
        
        assert 0 <= score <= 100
        assert isinstance(score, float)
    
    def test_empty_events(self, clr_agent):
        """Test handling of empty event list."""
        score = clr_agent._calculate_basic_metrics([])
        assert score == 0.0
    
    @pytest.mark.asyncio
    async def test_cognitive_load_detailed_calculation(self, clr_agent, sample_events):
        """Test comprehensive cognitive load calculation."""
        result = await clr_agent.calculate_cognitive_load_detailed(
            sample_events,
            'student123',
            'session456'
        )
        
        assert 'cognitive_load_score' in result
        assert 'mental_fatigue_level' in result
        assert 'component_scores' in result
        assert 'detected_patterns' in result
        assert 'recommendations' in result
        
        assert 0 <= result['cognitive_load_score'] <= 100
        assert result['mental_fatigue_level'] in ['low', 'medium', 'high', 'critical']
    
    def test_fatigue_level_mapping(self, clr_agent):
        """Test fatigue level determination."""
        assert clr_agent._determine_fatigue_level(10) == 'low'
        assert clr_agent._determine_fatigue_level(35) == 'medium'
        assert clr_agent._determine_fatigue_level(60) == 'high'
        assert clr_agent._determine_fatigue_level(80) == 'critical'
    
    def test_recommendations_generation(self, clr_agent):
        """Test recommendation generation."""
        patterns = {
            'task_switching': {'detected': True, 'score': 60},
            'error_clustering': {'detected': False, 'score': 0}
        }
        mood = {'mood_score': -0.4, 'dominant_emotion': 'frustrated'}
        
        recommendations = clr_agent._generate_recommendations(
            score=70,
            patterns=patterns,
            mood=mood,
            baseline_dev=5
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any('break' in rec.lower() for rec in recommendations)
    
    def test_intervention_urgency(self, clr_agent):
        """Test intervention urgency determination."""
        assert clr_agent._determine_intervention_urgency(90, {}, {}) == 'critical'
        assert clr_agent._determine_intervention_urgency(75, {}, {}) == 'high'
        assert clr_agent._determine_intervention_urgency(55, {}, {}) == 'medium'
        assert clr_agent._determine_intervention_urgency(30, {}, {}) == 'low'


class TestCLRAgentExecution:
    """Test CLR Agent execution workflow."""
    
    @pytest.mark.asyncio
    async def test_execute_with_valid_state(self, clr_agent, sample_events):
        """Test execute method with valid state."""
        state = AgentState(
            student_id='student123',
            session_id='session456',
            behavioral_events=sample_events,
            agents_executed=[],
            agent_outputs={}
        )
        
        result_state = await clr_agent.execute(state)
        
        assert 'clr_result' in result_state
        assert result_state['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_events(self, clr_agent):
        """Test execute with no events."""
        state = AgentState(
            student_id='student123',
            session_id='session456',
            behavioral_events=[],
            agents_executed=[],
            agent_outputs={}
        )
        
        result_state = await clr_agent.execute(state)
        
        assert 'clr_result' in result_state
        assert result_state['clr_result']['cognitive_load_score'] == 0


class TestMoodAnalysis:
    """Test mood analysis components."""
    
    def test_dominant_emotion_mapping(self, clr_agent):
        """Test emotion determination from mood score."""
        assert clr_agent._determine_dominant_emotion(0.7) == 'confident'
        assert clr_agent._determine_dominant_emotion(0.3) == 'engaged'
        assert clr_agent._determine_dominant_emotion(0.0) == 'neutral'
        assert clr_agent._determine_dominant_emotion(-0.3) == 'confused'
        assert clr_agent._determine_dominant_emotion(-0.7) == 'frustrated'
    
    def test_mood_adjustment_calculation(self, clr_agent):
        """Test cognitive load adjustment from mood."""
        assert clr_agent._calculate_mood_adjustment({'mood_score': -0.6}) == 20
        assert clr_agent._calculate_mood_adjustment({'mood_score': -0.3}) == 10
        assert clr_agent._calculate_mood_adjustment({'mood_score': -0.1}) == 5
        assert clr_agent._calculate_mood_adjustment({'mood_score': 0.5}) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
