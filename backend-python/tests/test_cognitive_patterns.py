"""
Unit Tests for Cognitive Pattern Detection

Tests pattern recognition algorithms for mental strain detection.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from ml.cognitive_patterns import (
    CognitivePatternDetector,
    PatternFeatureExtractor,
    MentalStrainClassifier,
    HistoricalBaselineTracker
)


@pytest.fixture
def pattern_detector():
    """Create pattern detector instance."""
    return CognitivePatternDetector()


@pytest.fixture
def feature_extractor():
    """Create feature extractor instance."""
    return PatternFeatureExtractor()


@pytest.fixture
def strain_classifier():
    """Create strain classifier instance."""
    return MentalStrainClassifier()


@pytest.fixture
def baseline_tracker():
    """Create baseline tracker instance."""
    return HistoricalBaselineTracker()


@pytest.fixture
def rapid_switching_events():
    """Events with rapid task switching."""
    base_time = int(datetime.now().timestamp() * 1000)
    return [
        {'type': 'NAVIGATION', 'timestamp': base_time + i * 20000}
        for i in range(6)  # 6 navigations in 2 minutes
    ]


@pytest.fixture
def error_cluster_events():
    """Events with error clustering."""
    base_time = int(datetime.now().timestamp() * 1000)
    return [
        {
            'type': 'QUIZ',
            'timestamp': base_time + i * 60000,
            'metadata': {'hasError': True}
        }
        for i in range(4)  # 4 errors in 3 minutes
    ]


class TestPatternFeatureExtractor:
    """Test feature extraction from events."""
    
    def test_time_features_extraction(self, feature_extractor):
        """Test time-based feature extraction."""
        events = [
            {'timestamp': int(datetime.now().timestamp() * 1000), 'type': 'CLICK'}
        ]
        features = feature_extractor.extract_features(events)
        
        assert 'hour_of_day' in features
        assert 0 <= features['hour_of_day'] <= 23
        assert 'day_of_week' in features
        assert 0 <= features['day_of_week'] <= 6
    
    def test_empty_events(self, feature_extractor):
        """Test handling of empty event list."""
        features = feature_extractor.extract_features([])
        
        assert isinstance(features, dict)
        assert 'hour_of_day' in features
    
    def test_sequence_features(self, feature_extractor):
        """Test sequence feature extraction."""
        events = [
            {'timestamp': 1000, 'type': 'CLICK'},
            {'timestamp': 2000, 'type': 'NAVIGATION'},
            {'timestamp': 3000, 'type': 'IDLE'}
        ]
        features = feature_extractor.extract_features(events)
        
        assert 'unique_event_types' in features
        assert features['unique_event_types'] == 3
        assert 'total_transitions' in features


class TestCognitivePatternDetector:
    """Test pattern detection algorithms."""
    
    def test_task_switching_detection(self, pattern_detector, rapid_switching_events):
        """Test rapid task switching detection."""
        result = pattern_detector._detect_task_switching(rapid_switching_events)
        
        assert result['detected'] is True
        assert result['score'] > 0
        assert 'switch_count' in result
    
    def test_no_task_switching(self, pattern_detector):
        """Test when no task switching occurs."""
        events = [
            {'type': 'NAVIGATION', 'timestamp': 1000},
            {'type': 'NAVIGATION', 'timestamp': 300000}  # 5 minutes apart
        ]
        result = pattern_detector._detect_task_switching(events)
        
        assert result['detected'] is False
        assert result['score'] == 0
    
    def test_error_clustering_detection(self, pattern_detector, error_cluster_events):
        """Test error clustering detection."""
        result = pattern_detector._detect_error_clustering(error_cluster_events)
        
        assert result['detected'] is True
        assert result['score'] > 0
        assert 'total_errors' in result
    
    def test_procrastination_loop_detection(self, pattern_detector):
        """Test procrastination loop detection."""
        events = [
            {'type': 'IDLE', 'timestamp': 1000},
            {'type': 'NAVIGATION', 'timestamp': 2000},
            {'type': 'IDLE', 'timestamp': 3000},
            {'type': 'IDLE', 'timestamp': 4000},
            {'type': 'NAVIGATION', 'timestamp': 5000},
            {'type': 'IDLE', 'timestamp': 6000}
        ]
        result = pattern_detector._detect_procrastination_loops(events)
        
        assert result['detected'] is True
        assert result['loop_count'] >= 2
    
    def test_night_degradation_detection(self, pattern_detector):
        """Test night degradation detection."""
        features = {'hour_of_day': 3, 'is_night_hours': True}
        result = pattern_detector._detect_night_degradation([], features)
        
        assert result['detected'] is True
        assert result['score'] == 80  # Peak degradation at 3 AM
    
    def test_micro_break_analysis(self, pattern_detector):
        """Test micro-break pattern analysis."""
        events = [
            {'type': 'IDLE', 'timestamp': 1000, 'duration': 300000},  # 5 min break
            {'type': 'IDLE', 'timestamp': 2000000, 'duration': 360000}  # 6 min break
        ]
        result = pattern_detector._detect_micro_break_patterns(events)
        
        assert 'avg_break_duration' in result
        assert 'avg_break_interval' in result


class TestMentalStrainClassifier:
    """Test strain classification."""
    
    def test_strain_level_classification(self, strain_classifier):
        """Test strain level determination."""
        assert strain_classifier._get_strain_level(15) == 'minimal'
        assert strain_classifier._get_strain_level(35) == 'moderate'
        assert strain_classifier._get_strain_level(60) == 'high'
        assert strain_classifier._get_strain_level(85) == 'critical'
    
    def test_pattern_classification(self, strain_classifier):
        """Test classification from pattern scores."""
        pattern_scores = {
            'task_switching': {'detected': True, 'score': 70},
            'error_clustering': {'detected': True, 'score': 60}
        }
        result = strain_classifier.classify(pattern_scores)
        
        assert 'mental_strain_score' in result
        assert 'strain_level' in result
        assert 'detected_patterns' in result
        assert len(result['detected_patterns']) == 2
    
    def test_empty_patterns(self, strain_classifier):
        """Test classification with no patterns detected."""
        pattern_scores = {
            'task_switching': {'detected': False, 'score': 0}
        }
        result = strain_classifier.classify(pattern_scores)
        
        assert result['mental_strain_score'] == 0
        assert len(result['detected_patterns']) == 0


class TestHistoricalBaselineTracker:
    """Test baseline tracking and anomaly detection."""
    
    def test_baseline_calculation(self, baseline_tracker):
        """Test baseline metrics calculation."""
        historical_data = [
            {'cognitive_load_score': 40, 'task_switching_count': 3},
            {'cognitive_load_score': 45, 'task_switching_count': 4},
            {'cognitive_load_score': 38, 'task_switching_count': 2}
        ]
        
        baseline = baseline_tracker.calculate_baseline('student123', historical_data)
        
        assert 'avg_cognitive_load' in baseline
        assert 'std_cognitive_load' in baseline
        assert baseline['avg_cognitive_load'] > 0
        assert baseline['data_points'] == 3
    
    def test_empty_historical_data(self, baseline_tracker):
        """Test baseline with no historical data."""
        baseline = baseline_tracker.calculate_baseline('student123', [])
        
        assert baseline['avg_cognitive_load'] == 40.0  # Default
        assert baseline['data_points'] == 0
    
    def test_anomaly_detection(self, baseline_tracker):
        """Test anomaly detection from baseline."""
        baseline = {
            'avg_cognitive_load': 40.0,
            'std_cognitive_load': 10.0
        }
        
        # Test normal value
        result = baseline_tracker.detect_anomaly(42, baseline, 'cognitive_load')
        assert result['is_anomaly'] is False
        
        # Test anomalous value (>2 std deviations)
        result = baseline_tracker.detect_anomaly(65, baseline, 'cognitive_load')
        assert result['is_anomaly'] is True
        assert result['z_score'] > 2.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
