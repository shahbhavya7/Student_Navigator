"""
Test Performance Profile

Tests for profile generation with combined data, risk level calculation,
recommended actions generation, and profile storage/retrieval.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from analytics.performance_profile import (
    PerformanceProfileGenerator,
    StudentPerformanceProfile
)


@pytest.fixture
def profile_generator():
    """Create profile generator instance"""
    return PerformanceProfileGenerator()


@pytest.fixture
def mock_clr_data():
    """Mock CLR data"""
    return {
        "cognitive_load_score": 65,
        "average_load": 60,
        "load_trend": "increasing",
        "overload_detected": False
    }


@pytest.fixture
def mock_performance_data():
    """Mock performance data"""
    return {
        "quiz_accuracy": 75.0,
        "learning_velocity": 2.5,
        "improvement_trend": "improving",
        "weak_topics": ["Advanced Math"],
        "task_completion_rate": 80.0,
        "plateau_detected": False
    }


@pytest.fixture
def mock_engagement_data():
    """Mock engagement data"""
    return {
        "engagement_score": 70.0,
        "dropout_risk": 0.2,
        "session_frequency": 4.5,
        "interaction_depth": 75.0,
        "dropout_signals": []
    }


def test_profile_generation(profile_generator, mock_clr_data, mock_performance_data, mock_engagement_data):
    """Test comprehensive profile generation"""
    profile = profile_generator.generate_profile(
        "student_123",
        mock_clr_data,
        mock_performance_data,
        mock_engagement_data
    )
    
    assert isinstance(profile, StudentPerformanceProfile)
    assert profile.student_id == "student_123"
    assert profile.combined_health_score > 0
    assert profile.risk_level in ["low", "medium", "high", "critical"]
    assert len(profile.recommended_actions) > 0


def test_combined_health_score_calculation(profile_generator):
    """Test combined health score calculation"""
    cognitive_load = {
        "current_load": 50,
        "avg_load": 50,
        "trend": "stable",
        "overload_risk": False
    }
    
    performance = {
        "quiz_accuracy": 80,
        "learning_velocity": 3.0,
        "improvement_trend": "improving",
        "weak_topics": [],
        "task_completion_rate": 85,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 80,
        "dropout_risk": 0.1,
        "session_frequency": 5.0,
        "interaction_depth": 85,
        "dropout_signals": []
    }
    
    health_score = profile_generator._calculate_combined_health_score(
        cognitive_load, performance, engagement
    )
    
    # Should be high (good cognitive load, performance, engagement)
    assert health_score > 70


def test_risk_level_critical(profile_generator):
    """Test critical risk level detection"""
    # Critical cognitive load
    cognitive_load = {
        "current_load": 90,  # Very high
        "avg_load": 70,
        "trend": "increasing",
        "overload_risk": True
    }
    
    performance = {
        "quiz_accuracy": 50,
        "learning_velocity": -1.0,
        "improvement_trend": "declining",
        "weak_topics": ["Math", "Science"],
        "task_completion_rate": 40,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 30,
        "dropout_risk": 0.85,  # Very high
        "session_frequency": 1.0,
        "interaction_depth": 25,
        "dropout_signals": ["Low frequency", "Long gaps", "Declining duration"]
    }
    
    risk_level = profile_generator._determine_risk_level(
        30,  # Low combined score
        cognitive_load,
        performance,
        engagement
    )
    
    assert risk_level == "critical"


def test_risk_level_low(profile_generator):
    """Test low risk level for healthy student"""
    cognitive_load = {
        "current_load": 40,
        "avg_load": 45,
        "trend": "stable",
        "overload_risk": False
    }
    
    performance = {
        "quiz_accuracy": 85,
        "learning_velocity": 2.0,
        "improvement_trend": "improving",
        "weak_topics": [],
        "task_completion_rate": 90,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 85,
        "dropout_risk": 0.1,
        "session_frequency": 5.0,
        "interaction_depth": 90,
        "dropout_signals": []
    }
    
    risk_level = profile_generator._determine_risk_level(
        80,  # High combined score
        cognitive_load,
        performance,
        engagement
    )
    
    assert risk_level == "low"


def test_recommended_actions_high_cognitive_load(profile_generator):
    """Test recommendations for high cognitive load"""
    cognitive_load = {
        "current_load": 80,
        "avg_load": 60,
        "trend": "increasing",
        "overload_risk": True
    }
    
    performance = {
        "quiz_accuracy": 70,
        "learning_velocity": 1.0,
        "improvement_trend": "stable",
        "weak_topics": [],
        "task_completion_rate": 75,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 70,
        "dropout_risk": 0.3,
        "session_frequency": 4.0,
        "interaction_depth": 70,
        "dropout_signals": []
    }
    
    actions = profile_generator._generate_recommended_actions(
        "high",
        cognitive_load,
        performance,
        engagement
    )
    
    # Should include cognitive load intervention
    assert any("cognitive" in action.lower() or "pace" in action.lower() for action in actions)


def test_recommended_actions_weak_performance(profile_generator):
    """Test recommendations for weak performance"""
    cognitive_load = {
        "current_load": 50,
        "avg_load": 50,
        "trend": "stable",
        "overload_risk": False
    }
    
    performance = {
        "quiz_accuracy": 45,  # Low
        "learning_velocity": -0.5,
        "improvement_trend": "declining",
        "weak_topics": ["Math", "Physics"],
        "task_completion_rate": 50,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 60,
        "dropout_risk": 0.4,
        "session_frequency": 3.0,
        "interaction_depth": 60,
        "dropout_signals": []
    }
    
    actions = profile_generator._generate_recommended_actions(
        "high",
        cognitive_load,
        performance,
        engagement
    )
    
    # Should include performance-related recommendations
    assert any("topic" in action.lower() or "resource" in action.lower() for action in actions)


def test_recommended_actions_high_dropout_risk(profile_generator):
    """Test recommendations for high dropout risk"""
    cognitive_load = {
        "current_load": 50,
        "avg_load": 50,
        "trend": "stable",
        "overload_risk": False
    }
    
    performance = {
        "quiz_accuracy": 70,
        "learning_velocity": 1.0,
        "improvement_trend": "stable",
        "weak_topics": [],
        "task_completion_rate": 70,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 35,  # Low
        "dropout_risk": 0.75,  # High
        "session_frequency": 1.5,
        "interaction_depth": 30,
        "dropout_signals": ["Long gaps", "Low frequency", "Declining duration"]
    }
    
    actions = profile_generator._generate_recommended_actions(
        "high",
        cognitive_load,
        performance,
        engagement
    )
    
    # Should include dropout-related interventions
    assert any("dropout" in action.lower() or "engagement" in action.lower() for action in actions)


def test_plateau_detection_recommendation(profile_generator):
    """Test recommendations for learning plateau"""
    cognitive_load = {
        "current_load": 50,
        "avg_load": 50,
        "trend": "stable",
        "overload_risk": False
    }
    
    performance = {
        "quiz_accuracy": 70,
        "learning_velocity": 0.0,
        "improvement_trend": "stable",
        "weak_topics": [],
        "task_completion_rate": 70,
        "plateau_detected": True  # Plateau
    }
    
    engagement = {
        "engagement_score": 70,
        "dropout_risk": 0.2,
        "session_frequency": 4.0,
        "interaction_depth": 70,
        "dropout_signals": []
    }
    
    actions = profile_generator._generate_recommended_actions(
        "medium",
        cognitive_load,
        performance,
        engagement
    )
    
    # Should include plateau-related recommendation
    assert any("plateau" in action.lower() for action in actions)


def test_multiple_risk_factors(profile_generator):
    """Test handling of multiple risk factors"""
    cognitive_load = {
        "current_load": 78,  # High
        "avg_load": 60,
        "trend": "increasing",
        "overload_risk": True
    }
    
    performance = {
        "quiz_accuracy": 55,  # Low
        "learning_velocity": -1.0,
        "improvement_trend": "declining",
        "weak_topics": ["Math", "Science", "History"],
        "task_completion_rate": 45,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 40,  # Low
        "dropout_risk": 0.65,  # High
        "session_frequency": 2.0,
        "interaction_depth": 35,
        "dropout_signals": ["Multiple signals"]
    }
    
    actions = profile_generator._generate_recommended_actions(
        "critical",
        cognitive_load,
        performance,
        engagement
    )
    
    # Should have multiple recommendations covering all issues
    assert len(actions) >= 3


def test_healthy_student_profile(profile_generator):
    """Test profile for healthy, well-performing student"""
    cognitive_load = {
        "current_load": 45,
        "avg_load": 45,
        "trend": "stable",
        "overload_risk": False
    }
    
    performance = {
        "quiz_accuracy": 88,
        "learning_velocity": 2.5,
        "improvement_trend": "improving",
        "weak_topics": [],
        "task_completion_rate": 92,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 85,
        "dropout_risk": 0.08,
        "session_frequency": 5.5,
        "interaction_depth": 88,
        "dropout_signals": []
    }
    
    profile = profile_generator.generate_profile(
        "student_healthy",
        cognitive_load,
        performance,
        engagement
    )
    
    assert profile.risk_level == "low"
    assert profile.combined_health_score > 75
    assert any("healthy" in action.lower() or "continue" in action.lower() for action in profile.recommended_actions)


def test_profile_field_structure(profile_generator, mock_clr_data, mock_performance_data, mock_engagement_data):
    """Test that profile has all required fields"""
    profile = profile_generator.generate_profile(
        "student_123",
        mock_clr_data,
        mock_performance_data,
        mock_engagement_data
    )
    
    assert hasattr(profile, "student_id")
    assert hasattr(profile, "cognitive_load_summary")
    assert hasattr(profile, "performance_summary")
    assert hasattr(profile, "engagement_summary")
    assert hasattr(profile, "combined_health_score")
    assert hasattr(profile, "risk_level")
    assert hasattr(profile, "recommended_actions")
    assert hasattr(profile, "generated_at")


def test_declining_trend_recommendation(profile_generator):
    """Test recommendations for declining performance trend"""
    cognitive_load = {
        "current_load": 55,
        "avg_load": 55,
        "trend": "stable",
        "overload_risk": False
    }
    
    performance = {
        "quiz_accuracy": 65,
        "learning_velocity": -2.0,
        "improvement_trend": "declining",  # Declining
        "weak_topics": ["Science"],
        "task_completion_rate": 60,
        "plateau_detected": False
    }
    
    engagement = {
        "engagement_score": 60,
        "dropout_risk": 0.35,
        "session_frequency": 3.0,
        "interaction_depth": 60,
        "dropout_signals": []
    }
    
    actions = profile_generator._generate_recommended_actions(
        "medium",
        cognitive_load,
        performance,
        engagement
    )
    
    # Should include recommendation for declining performance
    assert any("declining" in action.lower() or "check-in" in action.lower() for action in actions)
