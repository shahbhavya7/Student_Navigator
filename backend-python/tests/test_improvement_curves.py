"""
Test Improvement Curves

Tests for curve calculation algorithms, plateau detection,
retention rate calculation, and prediction accuracy.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from analytics.improvement_curves import ImprovementCurveCalculator, PerformanceAnalyzer


@pytest.fixture
def curve_calculator():
    """Create improvement curve calculator instance"""
    return ImprovementCurveCalculator()


@pytest.fixture
def performance_analyzer():
    """Create performance analyzer instance"""
    return PerformanceAnalyzer()


def test_learning_velocity_positive_trend():
    """Test learning velocity with improving scores"""
    calculator = ImprovementCurveCalculator()
    
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
    
    # Positive velocity for improving trend
    assert velocity > 0


def test_learning_velocity_negative_trend():
    """Test learning velocity with declining scores"""
    calculator = ImprovementCurveCalculator()
    
    base_date = datetime.now() - timedelta(days=20)
    quiz_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 10 - i,
            "completedAt": base_date + timedelta(days=i * 2)
        }
        for i in range(5)
    ]
    
    velocity = calculator.calculate_learning_velocity(quiz_results)
    
    # Negative velocity for declining trend
    assert velocity < 0


def test_insufficient_data_for_velocity():
    """Test learning velocity with insufficient data"""
    calculator = ImprovementCurveCalculator()
    
    # Only 2 data points
    quiz_results = [
        {"totalQuestions": 10, "correctAnswers": 5, "completedAt": datetime.now()},
        {"totalQuestions": 10, "correctAnswers": 6, "completedAt": datetime.now()}
    ]
    
    velocity = calculator.calculate_learning_velocity(quiz_results)
    
    # Should return 0 for insufficient data
    assert velocity == 0.0


def test_plateau_detection_positive():
    """Test detection of learning plateau"""
    calculator = ImprovementCurveCalculator()
    
    # Consistent scores with no improvement
    base_date = datetime.now() - timedelta(days=20)
    plateau_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 7,
            "completedAt": base_date + timedelta(days=i * 2)
        }
        for i in range(5)
    ]
    
    is_plateau = calculator.detect_learning_plateau(plateau_results)
    
    assert is_plateau is True


def test_plateau_detection_negative():
    """Test no plateau with improving scores"""
    calculator = ImprovementCurveCalculator()
    
    # Improving scores
    base_date = datetime.now() - timedelta(days=20)
    improving_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 5 + i,
            "completedAt": base_date + timedelta(days=i * 2)
        }
        for i in range(5)
    ]
    
    is_plateau = calculator.detect_learning_plateau(improving_results)
    
    assert is_plateau is False


def test_retention_rate_calculation():
    """Test knowledge retention rate calculation"""
    calculator = ImprovementCurveCalculator()
    
    # Same topic repeated - improving
    base_date = datetime.now() - timedelta(days=20)
    quiz_results = [
        {
            "topic": "Math",
            "totalQuestions": 10,
            "correctAnswers": 6,
            "completedAt": base_date
        },
        {
            "topic": "Math",
            "totalQuestions": 10,
            "correctAnswers": 8,
            "completedAt": base_date + timedelta(days=10)
        }
    ]
    
    retention = calculator.calculate_retention_rate(quiz_results)
    
    # Should show good retention (improved from 60% to 80%)
    assert retention > 80


def test_mastery_level_calculation():
    """Test topic-specific mastery level"""
    calculator = ImprovementCurveCalculator()
    
    quiz_results = [
        {
            "topic": "Math",
            "totalQuestions": 10,
            "correctAnswers": 5,
            "completedAt": datetime.now() - timedelta(days=10)
        },
        {
            "topic": "Math",
            "totalQuestions": 10,
            "correctAnswers": 7,
            "completedAt": datetime.now() - timedelta(days=5)
        },
        {
            "topic": "Math",
            "totalQuestions": 10,
            "correctAnswers": 9,
            "completedAt": datetime.now()
        }
    ]
    
    mastery = calculator.calculate_mastery_level(quiz_results, "Math")
    
    # Should be high (weighted toward recent 90% score)
    assert mastery > 70


def test_next_performance_prediction():
    """Test prediction of next quiz performance"""
    calculator = ImprovementCurveCalculator()
    
    # Improving trend
    base_date = datetime.now() - timedelta(days=20)
    quiz_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 5 + i,
            "completedAt": base_date + timedelta(days=i * 3)
        }
        for i in range(5)
    ]
    
    predicted = calculator.predict_next_performance(quiz_results)
    
    # Should predict higher than last score (90%)
    assert predicted > 85


def test_accuracy_by_difficulty():
    """Test accuracy analysis by difficulty level"""
    analyzer = PerformanceAnalyzer()
    
    quiz_results = [
        {
            "difficulty": "easy",
            "totalQuestions": 10,
            "correctAnswers": 9,
            "completedAt": datetime.now()
        },
        {
            "difficulty": "medium",
            "totalQuestions": 10,
            "correctAnswers": 7,
            "completedAt": datetime.now()
        },
        {
            "difficulty": "hard",
            "totalQuestions": 10,
            "correctAnswers": 4,
            "completedAt": datetime.now()
        }
    ]
    
    accuracy_metrics = analyzer.analyze_quiz_accuracy(quiz_results)
    
    assert accuracy_metrics["accuracy_by_difficulty"]["easy"] == 90.0
    assert accuracy_metrics["accuracy_by_difficulty"]["medium"] == 70.0
    assert accuracy_metrics["accuracy_by_difficulty"]["hard"] == 40.0


def test_time_efficiency_calculation():
    """Test time efficiency score calculation"""
    analyzer = PerformanceAnalyzer()
    
    quiz_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 8,
            "timeSpentSeconds": 600  # 10 minutes
        },
        {
            "totalQuestions": 10,
            "correctAnswers": 7,
            "timeSpentSeconds": 480  # 8 minutes
        }
    ]
    
    efficiency_metrics = analyzer.analyze_time_efficiency(quiz_results)
    
    assert efficiency_metrics["avg_time_per_question"] > 0
    assert efficiency_metrics["time_efficiency_score"] > 0
    assert efficiency_metrics["total_time_spent"] == 1080


def test_weak_topics_threshold():
    """Test weak topic detection threshold (< 60%)"""
    analyzer = PerformanceAnalyzer()
    
    quiz_results = [
        {
            "topic": "Math",
            "totalQuestions": 10,
            "correctAnswers": 5  # 50% - weak
        },
        {
            "topic": "Science",
            "totalQuestions": 10,
            "correctAnswers": 7  # 70% - strong
        },
        {
            "topic": "History",
            "totalQuestions": 10,
            "correctAnswers": 3  # 30% - weak
        }
    ]
    
    weak_topics = analyzer.detect_weak_topics(quiz_results)
    
    assert "Math" in weak_topics
    assert "History" in weak_topics
    assert "Science" not in weak_topics


def test_consistency_with_perfect_scores():
    """Test consistency score with perfect performance"""
    analyzer = PerformanceAnalyzer()
    
    perfect_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 10
        }
        for _ in range(5)
    ]
    
    consistency = analyzer.calculate_consistency_score(perfect_results)
    
    # Perfect consistency
    assert consistency == 100.0


def test_consistency_with_varied_scores():
    """Test consistency score with varied performance"""
    analyzer = PerformanceAnalyzer()
    
    varied_results = [
        {"totalQuestions": 10, "correctAnswers": 10},
        {"totalQuestions": 10, "correctAnswers": 2},
        {"totalQuestions": 10, "correctAnswers": 9},
        {"totalQuestions": 10, "correctAnswers": 3},
        {"totalQuestions": 10, "correctAnswers": 8}
    ]
    
    consistency = analyzer.calculate_consistency_score(varied_results)
    
    # Low consistency due to high variation
    assert consistency < 60


def test_improvement_trend_stable():
    """Test stable improvement trend detection"""
    calculator = ImprovementCurveCalculator()
    
    base_date = datetime.now() - timedelta(days=20)
    stable_results = [
        {
            "totalQuestions": 10,
            "correctAnswers": 7,
            "completedAt": base_date + timedelta(days=i * 2)
        }
        for i in range(6)
    ]
    
    trend = calculator.calculate_improvement_trend(stable_results)
    
    assert trend == "stable"


def test_recent_accuracy_vs_overall():
    """Test recent accuracy compared to overall"""
    analyzer = PerformanceAnalyzer()
    
    # Early poor performance, recent improvement
    base_date = datetime.now() - timedelta(days=30)
    quiz_results = [
        # Old quizzes - poor performance
        *[
            {
                "totalQuestions": 10,
                "correctAnswers": 4,
                "completedAt": base_date + timedelta(days=i)
            }
            for i in range(5)
        ],
        # Recent quizzes - good performance
        *[
            {
                "totalQuestions": 10,
                "correctAnswers": 9,
                "completedAt": datetime.now() - timedelta(days=i)
            }
            for i in range(5)
        ]
    ]
    
    accuracy_metrics = analyzer.analyze_quiz_accuracy(quiz_results)
    
    # Recent accuracy should be higher than overall
    assert accuracy_metrics["recent_accuracy"] > accuracy_metrics["overall_accuracy"]


def test_empty_quiz_results():
    """Test handling of empty quiz results"""
    calculator = ImprovementCurveCalculator()
    analyzer = PerformanceAnalyzer()
    
    empty_results = []
    
    velocity = calculator.calculate_learning_velocity(empty_results)
    trend = calculator.calculate_improvement_trend(empty_results)
    weak_topics = analyzer.detect_weak_topics(empty_results)
    
    assert velocity == 0.0
    assert trend == "insufficient_data"
    assert weak_topics == []
