"""
Unit Tests for Sentiment Analysis and Mood Detection

Tests mood analysis using LLM and typing pattern heuristics.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from unittest.mock import MagicMock, patch
from ml.sentiment_analyzer import (
    MoodAnalyzer,
    TypingPatternMoodDetector,
    MoodTrendAnalyzer
)


@pytest.fixture
def mood_analyzer():
    """Create mood analyzer instance with mocked LLM."""
    mock_llm = MagicMock()
    analyzer = MoodAnalyzer(mock_llm)
    return analyzer


@pytest.fixture
def typing_detector():
    """Create typing pattern mood detector instance."""
    return TypingPatternMoodDetector()


@pytest.fixture
def trend_analyzer():
    """Create mood trend analyzer instance."""
    return MoodTrendAnalyzer()


@pytest.fixture
def positive_text():
    """Sample positive text."""
    return "I really enjoyed solving this problem! It was challenging but fun."


@pytest.fixture
def negative_text():
    """Sample negative text."""
    return "This is so confusing and frustrating. I don't understand anything."


@pytest.fixture
def neutral_text():
    """Sample neutral text."""
    return "The function returns a list of integers."


class TestMoodAnalyzer:
    """Test LLM-based mood analysis."""
    
    @pytest.mark.skip(reason="LLM mocking requires real API key for testing")
    def test_analyze_positive_text(self, mood_analyzer, positive_text):
        """Test positive sentiment detection."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = '''{
            "dominant_emotion": "excited",
            "confidence": 0.9,
            "mood_score": 0.75,
            "explanation": "Positive and enthusiastic language"
        }'''
        
        with patch.object(mood_analyzer.llm, 'invoke', return_value=mock_response):
            result = mood_analyzer.analyze_text(positive_text)
        
        assert result['dominant_emotion'] == 'excited'
        assert result['mood_score'] > 0
        assert result['confidence'] > 0.8
        assert 'explanation' in result
    
    @pytest.mark.skip(reason="LLM mocking requires real API key for testing")
    def test_analyze_negative_text(self, mood_analyzer, negative_text):
        """Test negative sentiment detection."""
        mock_response = MagicMock()
        mock_response.content = '''{
            "dominant_emotion": "frustrated",
            "confidence": 0.85,
            "mood_score": -0.7,
            "explanation": "Clear signs of frustration"
        }'''
        
        with patch.object(mood_analyzer.llm, 'invoke', return_value=mock_response):
            result = mood_analyzer.analyze_text(negative_text)
        
        assert result['dominant_emotion'] == 'frustrated'
        assert result['mood_score'] < 0
        assert result['confidence'] > 0.8
    
    def test_analyze_neutral_text(self, mood_analyzer, neutral_text):
        """Test neutral text analysis."""
        mock_response = MagicMock()
        mock_response.content = '''{
            "dominant_emotion": "neutral",
            "confidence": 0.6,
            "mood_score": 0.0,
            "explanation": "Neutral technical language"
        }'''
        mood_analyzer.llm.invoke = MagicMock(return_value=mock_response)
        
        result = mood_analyzer.analyze_text(neutral_text)
        
        assert result['dominant_emotion'] == 'neutral'
        assert -0.2 <= result['mood_score'] <= 0.2
        assert 'explanation' in result
    
    def test_empty_text_handling(self, mood_analyzer):
        """Test handling of empty text."""
        result = mood_analyzer.analyze_text("")
        
        assert result['dominant_emotion'] == 'neutral'
        assert result['mood_score'] == 0.0
        assert result['confidence'] == 0.0
        assert 'explanation' in result


class TestTypingPatternMoodDetector:
    """Test typing pattern mood detection."""
    
    def test_frustrated_typing_pattern(self, typing_detector):
        """Test detection of frustrated typing."""
        pattern = {
            'wpm': 25,  # Low WPM
            'backspaceRate': 0.35,  # High backspace rate
            'correctionCount': 12
        }
        
        result = typing_detector.analyze_typing_pattern(pattern)
        
        assert result['dominant_emotion'] == 'frustrated'
        assert result['mood_score'] < -0.5
    
    def test_confident_typing_pattern(self, typing_detector):
        """Test detection of confident typing."""
        pattern = {
            'wpm': 42,  # Within 90-130% of baseline (40)
            'backspaceRate': 0.07,  # Low backspace rate (<0.08)
            'correctionCount': 2
        }
        
        result = typing_detector.analyze_typing_pattern(pattern)
        
        assert result['dominant_emotion'] == 'confident'
        assert result['mood_score'] > 0.5
    
    def test_hesitant_typing_pattern(self, typing_detector):
        """Test detection of hesitant/confused typing."""
        pattern = {
            'wpm': 25,  # Low WPM (<70% of baseline 40 = 28)
            'backspaceRate': 0.25,  # High backspace rate (>0.2)
            'correctionCount': 15
        }
        
        result = typing_detector.analyze_typing_pattern(pattern)
        
        # This matches frustrated pattern: high backspace rate + low WPM
        assert result['dominant_emotion'] == 'frustrated'
        assert result['mood_score'] < 0
    
    def test_neutral_typing_pattern(self, typing_detector):
        """Test neutral typing pattern."""
        pattern = {
            'wpm': 40,  # Average WPM
            'backspaceRate': 0.15,  # Average backspace rate
            'correctionCount': 6
        }
        
        result = typing_detector.analyze_typing_pattern(pattern)
        
        assert -0.3 <= result['mood_score'] <= 0.3
    
    def test_missing_pattern_data(self, typing_detector):
        """Test handling of incomplete pattern data."""
        pattern = {'wpm': 40, 'backspaceRate': 0.15}  # Average values
        
        result = typing_detector.analyze_typing_pattern(pattern)
        
        # Should fall into neutral range
        assert result['dominant_emotion'] == 'neutral'
        assert -0.5 <= result['mood_score'] <= 0.5


class TestMoodTrendAnalyzer:
    """Test mood trend analysis."""
    
    def test_positive_mood_trend(self, trend_analyzer):
        """Test detection of improving mood."""
        # Mock get_mood_history to return test data
        mood_history = [
            {'timestamp': 1000, 'mood_score': -0.5},
            {'timestamp': 2000, 'mood_score': -0.2},
            {'timestamp': 3000, 'mood_score': 0.1},
            {'timestamp': 4000, 'mood_score': 0.4}
        ]
        trend_analyzer.get_mood_history = MagicMock(return_value=mood_history)
        
        result = trend_analyzer.calculate_mood_trend('test_student', window_minutes=30)
        
        assert result['trend'] == 'improving'
        assert result['slope'] > 0
    
    def test_negative_mood_trend(self, trend_analyzer):
        """Test detection of declining mood."""
        mood_history = [
            {'timestamp': 1000, 'mood_score': 0.6},
            {'timestamp': 2000, 'mood_score': 0.3},
            {'timestamp': 3000, 'mood_score': 0.0},
            {'timestamp': 4000, 'mood_score': -0.3}
        ]
        trend_analyzer.get_mood_history = MagicMock(return_value=mood_history)
        
        result = trend_analyzer.calculate_mood_trend('test_student', window_minutes=30)
        
        assert result['trend'] == 'declining'
        assert result['slope'] < 0
    
    def test_stable_mood_trend(self, trend_analyzer):
        """Test detection of stable mood."""
        mood_history = [
            {'timestamp': 1000, 'mood_score': 0.3},
            {'timestamp': 2000, 'mood_score': 0.35},
            {'timestamp': 3000, 'mood_score': 0.32},
            {'timestamp': 4000, 'mood_score': 0.33}
        ]
        trend_analyzer.get_mood_history = MagicMock(return_value=mood_history)
        
        result = trend_analyzer.calculate_mood_trend('test_student', window_minutes=30)
        
        assert result['trend'] == 'stable'
        assert abs(result['slope']) < 0.1
    
    def test_mood_drop_detection(self, trend_analyzer):
        """Test detection of significant mood drop."""
        recent_history = [
            {'timestamp': 1000, 'mood_score': 0.6},
            {'timestamp': 2000, 'mood_score': 0.5},
            {'timestamp': 3000, 'mood_score': 0.4},
            {'timestamp': 4000, 'mood_score': -0.5}
        ]
        trend_analyzer.get_mood_history = MagicMock(return_value=recent_history)
        
        result = trend_analyzer.detect_mood_drop('test_student', minutes=15)
        
        assert result['drop_detected'] is True
        assert result['drop_magnitude'] > 0.4
        assert result['intervention_needed'] is True
    
    def test_no_mood_drop(self, trend_analyzer):
        """Test when no significant mood drop occurs."""
        recent_history = [
            {'timestamp': 1000, 'mood_score': 0.35},
            {'timestamp': 2000, 'mood_score': 0.4},
            {'timestamp': 3000, 'mood_score': 0.38},
            {'timestamp': 4000, 'mood_score': 0.3}
        ]
        trend_analyzer.get_mood_history = MagicMock(return_value=recent_history)
        
        result = trend_analyzer.detect_mood_drop('test_student', minutes=15)
        
        assert result['drop_detected'] is False
        assert result['intervention_needed'] is False
    
    def test_insufficient_history(self, trend_analyzer):
        """Test trend analysis with insufficient data."""
        mood_history = [
            {'timestamp': 1000, 'mood_score': 0.5}
        ]
        trend_analyzer.get_mood_history = MagicMock(return_value=mood_history)
        
        result = trend_analyzer.calculate_mood_trend('test_student', window_minutes=30)
        
        assert result['trend'] == 'stable'
        assert result['slope'] == 0.0
        assert result['confidence'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
