"""
Test Performance Agent

Tests for performance agent with mock quiz data, learning velocity calculation,
improvement trend detection, and weak topic identification.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from agents.performance_agent import PerformanceAgent
from agents.state import AgentState


@pytest.fixture
def performance_agent():
    """Create performance agent instance"""
    return PerformanceAgent("test_performance_agent")


@pytest.fixture
def mock_quiz_results():
    """Mock quiz results for testing"""
    base_date = datetime.now() - timedelta(days=30)
    return [
        {
            "id": f"quiz_{i}",
            "studentId": "student_123",
            "moduleId": f"module_{i % 3}",
            "score": 60 + (i * 3),  # Improving trend
            "totalQuestions": 10,
            "correctAnswers": 6 + (i // 2),
            "timeSpentSeconds": 300 - (i * 10),
            "completedAt": base_date + timedelta(days=i * 2),
            "topic": ["Math", "Science", "History"][i % 3],
            "difficulty": "medium"
        }
        for i in range(10)
    ]


@pytest.fixture
def mock_state():
    """Create mock agent state"""
    return AgentState(
        student_id="student_123",
        session_id="session_456",
        timestamp=int(datetime.now().timestamp()),
        behavioral_events=[],
        aggregated_metrics={},
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
async def test_performance_agent_execute(performance_agent, mock_state, monkeypatch):
    """Test performance agent execution"""
    
    # Mock database fetch
    async def mock_fetch_quiz_results(self, student_id, days=30):
        base_date = datetime.now() - timedelta(days=30)
        return [
            {
                "id": f"quiz_{i}",
                "studentId": student_id,
                "totalQuestions": 10,
                "correctAnswers": 7,
                "timeSpentSeconds": 300,
                "completedAt": base_date + timedelta(days=i * 3),
                "topic": "Math",
                "difficulty": "medium"
            }
            for i in range(5)
        ]
    
    async def mock_task_completion(self, student_id):
        return 75.0
    
    async def mock_generate_insights(self, metrics):
        return "Mock performance insights: Student showing steady progress."
    
    # Mock LLM to prevent live API calls
    class MockLLM:
        async def ainvoke(self, messages):
            class MockResponse:
                content = "Mock performance insights: Student showing steady progress."
            return MockResponse()
    
    monkeypatch.setattr(PerformanceAgent, "_fetch_quiz_results", mock_fetch_quiz_results)
    monkeypatch.setattr(PerformanceAgent, "_calculate_task_completion_rate", mock_task_completion)
    monkeypatch.setattr(PerformanceAgent, "_generate_performance_insights", mock_generate_insights)
    monkeypatch.setattr(performance_agent, "llm", MockLLM())
    
    result = await performance_agent.execute(mock_state)
    
    assert "performance_metrics" in result
    assert "quiz_accuracy" in result
    assert "learning_velocity" in result
    assert "improvement_trend" in result
    assert "weak_topics" in result


def test_learning_velocity_calculation():
    """Test learning velocity calculation"""
    from analytics.improvement_curves import ImprovementCurveCalculator
    
    calculator = ImprovementCurveCalculator()
    
    # Create quiz results with improving scores
    base_date = datetime.now() - timedelta(days=20)
    quiz_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 5 + i,
            "completedAt": base_date + timedelta(days=i * 2)
        }
        for i in range(5)
    ]
    
    velocity = calculator.calculate_learning_velocity(quiz_results)
    
    # Should show positive velocity (improving)
    assert velocity > 0


def test_improvement_trend_detection():
    """Test improvement trend detection"""
    from analytics.improvement_curves import ImprovementCurveCalculator
    
    calculator = ImprovementCurveCalculator()
    
    # Declining trend
    base_date = datetime.now() - timedelta(days=20)
    declining_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 10 - i,
            "completedAt": base_date + timedelta(days=i * 2)
        }
        for i in range(6)
    ]
    
    trend = calculator.calculate_improvement_trend(declining_results)
    assert trend == "declining"
    
    # Improving trend
    improving_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 5 + i,
            "completedAt": base_date + timedelta(days=i * 2)
        }
        for i in range(6)
    ]
    
    trend = calculator.calculate_improvement_trend(improving_results)
    assert trend == "improving"


def test_weak_topic_identification():
    """Test weak topic identification"""
    from analytics.improvement_curves import PerformanceAnalyzer
    
    analyzer = PerformanceAnalyzer()
    
    quiz_results = [
        {
            "topic": "Math",
            "totalQuestions": 10,
            "correctAnswers": 3  # 30% - weak
        },
        {
            "topic": "Science",
            "totalQuestions": 10,
            "correctAnswers": 8  # 80% - strong
        },
        {
            "topic": "History",
            "totalQuestions": 10,
            "correctAnswers": 5  # 50% - weak
        }
    ]
    
    weak_topics = analyzer.detect_weak_topics(quiz_results)
    
    assert "Math" in weak_topics
    assert "History" in weak_topics
    assert "Science" not in weak_topics


def test_plateau_detection():
    """Test learning plateau detection"""
    from analytics.improvement_curves import ImprovementCurveCalculator
    
    calculator = ImprovementCurveCalculator()
    
    # Plateaued performance (no improvement)
    base_date = datetime.now() - timedelta(days=20)
    plateau_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 7,  # Consistent 70%
            "completedAt": base_date + timedelta(days=i * 2)
        }
        for i in range(5)
    ]
    
    is_plateau = calculator.detect_learning_plateau(plateau_results)
    assert is_plateau is True


def test_quiz_accuracy_analysis():
    """Test quiz accuracy analysis"""
    from analytics.improvement_curves import PerformanceAnalyzer
    
    analyzer = PerformanceAnalyzer()
    
    quiz_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 7,
            "completedAt": datetime.now() - timedelta(days=i),
            "difficulty": "medium"
        }
        for i in range(10)
    ]
    
    accuracy_metrics = analyzer.analyze_quiz_accuracy(quiz_results)
    
    assert "overall_accuracy" in accuracy_metrics
    assert "recent_accuracy" in accuracy_metrics
    assert "accuracy_by_difficulty" in accuracy_metrics
    assert accuracy_metrics["overall_accuracy"] == 70.0


def test_consistency_score():
    """Test performance consistency score calculation"""
    from analytics.improvement_curves import PerformanceAnalyzer
    
    analyzer = PerformanceAnalyzer()
    
    # Consistent performance
    consistent_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 7
        }
        for _ in range(5)
    ]
    
    consistency = analyzer.calculate_consistency_score(consistent_results)
    assert consistency > 90  # Very consistent
    
    # Inconsistent performance
    inconsistent_results = [
        {"totalQuestions": 10, "correctAnswers": 10},
        {"totalQuestions": 10, "correctAnswers": 3},
        {"totalQuestions": 10, "correctAnswers": 9},
        {"totalQuestions": 10, "correctAnswers": 2},
        {"totalQuestions": 10, "correctAnswers": 8}
    ]
    
    consistency = analyzer.calculate_consistency_score(inconsistent_results)
    assert consistency < 50  # Very inconsistent
