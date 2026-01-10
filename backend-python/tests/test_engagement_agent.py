"""
Test Engagement Agent

Tests for engagement score calculation, dropout risk detection,
session pattern analysis, and interaction depth calculation.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from agents.engagement_agent import EngagementAgent
from agents.state import AgentState


@pytest.fixture
def engagement_agent():
    """Create engagement agent instance"""
    return EngagementAgent("test_engagement_agent")


@pytest.fixture
def mock_sessions():
    """Mock session data for testing"""
    base_date = datetime.now() - timedelta(days=14)
    return [
        {
            "id": f"session_{i}",
            "studentId": "student_123",
            "startTime": base_date + timedelta(days=i),
            "endTime": base_date + timedelta(days=i, hours=1),
            "durationSeconds": 3600 - (i * 60)  # Declining duration
        }
        for i in range(7)
    ]


@pytest.fixture
def mock_state():
    """Create mock agent state"""
    return AgentState(
        student_id="student_123",
        session_id="session_456",
        timestamp=int(datetime.now().timestamp()),
        behavioral_events=[
            {"type": "CONTENT_INTERACTION", "duration": 30},
            {"type": "SCROLL_BEHAVIOR", "duration": 15},
            {"type": "TASK_SWITCH", "duration": 5}
        ],
        aggregated_metrics={"events": []},
        cognitive_load_score=50.0,
        cognitive_load_history=[],
        mental_fatigue_level="medium",
        performance_metrics={},
        quiz_accuracy=0.0,
        learning_velocity=0.0,
        improvement_trend="stable",
        engagement_score=0.0,
        session_duration=0,
        interaction_depth=0.0,
        dropout_risk=0.0,
        current_learning_path_id="",
        current_module_id="",
        curriculum_adjustments=[],
        difficulty_level="medium",
        interventions_triggered=[],
        last_intervention_time=0,
        intervention_effectiveness={},
        agents_executed=[],
        agent_outputs={},
        execution_errors=[],
        student_profile=None,
        weak_topics=[],
        task_completion_rate=0.0,
        return_frequency={},
        dropout_signals=[]
    )


@pytest.mark.asyncio
async def test_engagement_agent_execute(engagement_agent, mock_state, monkeypatch):
    """Test engagement agent execution"""
    
    # Mock database fetch
    async def mock_fetch_sessions(self, student_id, days=14):
        base_date = datetime.now() - timedelta(days=7)
        return [
            {
                "id": f"session_{i}",
                "studentId": student_id,
                "startTime": base_date + timedelta(days=i),
                "endTime": base_date + timedelta(days=i, hours=1),
                "durationSeconds": 3600
            }
            for i in range(4)
        ]
    
    async def mock_generate_insights(self, metrics):
        return "Mock engagement insights: Student maintaining good engagement levels."
    
    # Mock LLM to prevent live API calls
    class MockLLM:
        async def ainvoke(self, messages):
            class MockResponse:
                content = "Mock engagement insights: Student maintaining good engagement levels."
            return MockResponse()
    
    monkeypatch.setattr(EngagementAgent, "_fetch_recent_sessions", mock_fetch_sessions)
    monkeypatch.setattr(EngagementAgent, "_generate_engagement_insights", mock_generate_insights)
    monkeypatch.setattr(engagement_agent, "llm", MockLLM())
    
    result = await engagement_agent.execute(mock_state)
    
    assert "engagement_score" in result
    assert "dropout_risk" in result
    assert "session_frequency" in result
    assert "dropout_signals" in result


def test_session_metrics_calculation():
    """Test session metrics calculation"""
    engagement_agent = EngagementAgent()
    
    base_date = datetime.now() - timedelta(days=14)
    sessions = [
        {
            "id": f"session_{i}",
            "startTime": base_date + timedelta(days=i * 2),
            "endTime": base_date + timedelta(days=i * 2, hours=1),
            "durationSeconds": 3600
        }
        for i in range(5)
    ]
    
    metrics = engagement_agent._calculate_session_metrics(sessions)
    
    assert metrics["avg_session_duration"] == 3600
    assert metrics["total_study_time"] == 18000
    assert metrics["session_frequency"] > 0


def test_interaction_depth_calculation():
    """Test content interaction depth calculation"""
    engagement_agent = EngagementAgent()
    
    # High interaction depth
    high_interaction_events = [
        {"type": "CONTENT_INTERACTION", "duration": 30},
        {"type": "SCROLL_BEHAVIOR", "duration": 20},
        {"type": "TIME_TRACKING", "duration": 40},
        {"type": "NAVIGATION", "duration": 5}
    ]
    
    depth = engagement_agent._calculate_interaction_depth(high_interaction_events)
    assert depth > 50  # Should be high
    
    # Low interaction depth
    low_interaction_events = [
        {"type": "IDLE_TIME", "duration": 100},
        {"type": "TASK_SWITCH", "duration": 5}
    ]
    
    depth = engagement_agent._calculate_interaction_depth(low_interaction_events)
    assert depth < 30  # Should be low


def test_dropout_signal_detection():
    """Test dropout signal detection"""
    engagement_agent = EngagementAgent()
    
    # Declining activity
    base_date = datetime.now() - timedelta(days=14)
    sessions_declining = [
        {
            "id": f"session_{i}",
            "startTime": base_date + timedelta(days=i),
            "durationSeconds": 3600 - (i * 200)
        }
        for i in range(8)
    ]
    
    session_metrics = engagement_agent._calculate_session_metrics(sessions_declining)
    signals = engagement_agent._detect_dropout_signals(sessions_declining, session_metrics)
    
    assert len(signals) > 0
    # Should detect declining frequency or duration


def test_engagement_score_calculation():
    """Test overall engagement score calculation"""
    engagement_agent = EngagementAgent()
    
    # High engagement
    high_session_metrics = {
        "session_frequency": 5.0,  # 5 sessions per week
        "avg_session_duration": 2400  # 40 minutes
    }
    high_return_frequency = {
        "last_7_days": 6
    }
    
    score = engagement_agent._calculate_engagement_score(
        high_session_metrics, 80.0, high_return_frequency
    )
    assert score > 70  # High engagement
    
    # Low engagement
    low_session_metrics = {
        "session_frequency": 1.0,
        "avg_session_duration": 600
    }
    low_return_frequency = {
        "last_7_days": 1
    }
    
    score = engagement_agent._calculate_engagement_score(
        low_session_metrics, 20.0, low_return_frequency
    )
    assert score < 40  # Low engagement


def test_dropout_risk_calculation():
    """Test dropout risk calculation"""
    engagement_agent = EngagementAgent()
    
    # High risk scenario
    low_engagement = 30.0
    many_signals = ["Signal 1", "Signal 2", "Signal 3"]
    recent_sessions = [
        {
            "id": "session_1",
            "startTime": datetime.now() - timedelta(days=6)
        }
    ]
    
    risk = engagement_agent._calculate_dropout_risk(
        low_engagement, many_signals, recent_sessions
    )
    assert risk > 0.6  # High risk
    
    # Low risk scenario
    high_engagement = 80.0
    few_signals = []
    active_sessions = [
        {
            "id": f"session_{i}",
            "startTime": datetime.now() - timedelta(days=i)
        }
        for i in range(3)
    ]
    
    risk = engagement_agent._calculate_dropout_risk(
        high_engagement, few_signals, active_sessions
    )
    assert risk < 0.3  # Low risk


def test_return_frequency_calculation():
    """Test return frequency calculation"""
    engagement_agent = EngagementAgent()
    
    # Regular return pattern
    now = datetime.now()
    regular_sessions = [
        {
            "id": f"session_{i}",
            "startTime": now - timedelta(days=i * 2)
        }
        for i in range(10)
    ]
    
    frequency = engagement_agent._calculate_return_frequency(regular_sessions)
    
    assert "last_7_days" in frequency
    assert "last_14_days" in frequency
    assert "last_30_days" in frequency
    assert frequency["last_7_days"] > 0


def test_declining_session_duration_detection():
    """Test detection of declining session duration"""
    engagement_agent = EngagementAgent()
    
    # Create sessions with declining duration - more dramatic decline
    base_date = datetime.now() - timedelta(days=10)
    declining_sessions = [
        {
            "id": f"session_{i}",
            "startTime": base_date + timedelta(days=i),
            "durationSeconds": 3600 - (i * 500)  # Declining by 8.3 minutes each day
        }
        for i in range(6)
    ]
    
    session_metrics = engagement_agent._calculate_session_metrics(declining_sessions)
    signals = engagement_agent._detect_dropout_signals(declining_sessions, session_metrics)
    
    # Should detect declining duration or frequency
    assert len(signals) > 0, f"Expected dropout signals but got none. Session metrics: {session_metrics}"


def test_long_gap_detection():
    """Test detection of long gaps between sessions"""
    engagement_agent = EngagementAgent()
    
    # Last session was 5 days ago
    old_session = [
        {
            "id": "session_1",
            "startTime": datetime.now() - timedelta(days=5),
            "durationSeconds": 3600
        }
    ]
    
    session_metrics = engagement_agent._calculate_session_metrics(old_session)
    signals = engagement_agent._detect_dropout_signals(old_session, session_metrics)
    
    # Should detect long gap
    assert any("days" in signal.lower() for signal in signals)
