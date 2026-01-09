"""
Advanced Pattern Recognition Module for Cognitive Load Detection

This module implements ML-based pattern recognition for detecting mental strain signals
beyond simple weighted averages. It analyzes behavioral sequences to identify:
- Task-switching patterns
- Error clustering
- Procrastination loops
- Browsing drift patterns
- Avoidance behavior
- Micro-break patterns
- Night productivity degradation
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import math


class PatternFeatureExtractor:
    """Converts raw behavioral events into feature vectors for pattern detection."""
    
    def __init__(self):
        self.event_buffer = deque(maxlen=1000)  # Keep last 1000 events
        
    def extract_features(self, events: List[Dict]) -> Dict:
        """
        Extract comprehensive features from behavioral events.
        
        Args:
            events: List of behavioral event dictionaries
            
        Returns:
            Dictionary of extracted features
        """
        if not events:
            return self._empty_features()
            
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.get('timestamp', 0))
        
        # Time-based features
        time_features = self._extract_time_features(sorted_events)
        
        # Sequence features
        sequence_features = self._extract_sequence_features(sorted_events)
        
        # Statistical features
        statistical_features = self._extract_statistical_features(sorted_events)
        
        # Contextual features
        contextual_features = self._extract_contextual_features(sorted_events)
        
        return {
            **time_features,
            **sequence_features,
            **statistical_features,
            **contextual_features
        }
    
    def _extract_time_features(self, events: List[Dict]) -> Dict:
        """Extract time-based features."""
        if not events:
            return {}
            
        timestamps = [e.get('timestamp', 0) for e in events]
        first_time = datetime.fromtimestamp(timestamps[0] / 1000)
        last_time = datetime.fromtimestamp(timestamps[-1] / 1000)
        
        return {
            'hour_of_day': first_time.hour,
            'day_of_week': first_time.weekday(),
            'session_duration_minutes': (last_time - first_time).total_seconds() / 60,
            'is_night_hours': 22 <= first_time.hour or first_time.hour <= 6
        }
    
    def _extract_sequence_features(self, events: List[Dict]) -> Dict:
        """Extract sequence-based features."""
        if len(events) < 2:
            return {}
            
        event_types = [e.get('type', '') for e in events]
        
        # Calculate transitions
        transitions = []
        for i in range(len(event_types) - 1):
            transitions.append(f"{event_types[i]}->{event_types[i+1]}")
        
        # Calculate inter-event timing
        timestamps = [e.get('timestamp', 0) for e in events]
        inter_event_times = []
        for i in range(len(timestamps) - 1):
            time_diff = (timestamps[i+1] - timestamps[i]) / 1000  # Convert to seconds
            inter_event_times.append(time_diff)
        
        return {
            'unique_event_types': len(set(event_types)),
            'total_transitions': len(transitions),
            'avg_inter_event_time': statistics.mean(inter_event_times) if inter_event_times else 0,
            'max_inter_event_time': max(inter_event_times) if inter_event_times else 0
        }
    
    def _extract_statistical_features(self, events: List[Dict]) -> Dict:
        """Extract statistical features."""
        if not events:
            return {}
            
        # Extract numerical values from events
        durations = [e.get('duration', 0) for e in events if 'duration' in e]
        
        if not durations:
            return {}
        
        return {
            'avg_duration': statistics.mean(durations),
            'std_duration': statistics.stdev(durations) if len(durations) > 1 else 0,
            'min_duration': min(durations),
            'max_duration': max(durations),
            'median_duration': statistics.median(durations)
        }
    
    def _extract_contextual_features(self, events: List[Dict]) -> Dict:
        """Extract contextual features from event metadata."""
        # Count specific event types
        event_type_counts = defaultdict(int)
        for event in events:
            event_type_counts[event.get('type', 'unknown')] += 1
        
        return {
            'navigation_count': event_type_counts.get('NAVIGATION', 0),
            'click_count': event_type_counts.get('CLICK', 0),
            'scroll_count': event_type_counts.get('SCROLL', 0),
            'typing_count': event_type_counts.get('TYPING_PATTERN', 0),
            'idle_count': event_type_counts.get('IDLE', 0)
        }
    
    def _empty_features(self) -> Dict:
        """Return empty feature set."""
        return {
            'hour_of_day': 0,
            'day_of_week': 0,
            'session_duration_minutes': 0,
            'is_night_hours': False,
            'unique_event_types': 0,
            'total_transitions': 0,
            'avg_inter_event_time': 0,
            'max_inter_event_time': 0
        }


class CognitivePatternDetector:
    """Detects mental strain patterns from behavioral sequences."""
    
    def __init__(self):
        self.pattern_history = defaultdict(list)
        
    def detect_patterns(self, events: List[Dict], features: Dict) -> Dict:
        """
        Detect all cognitive load patterns from events and features.
        
        Args:
            events: List of behavioral events
            features: Extracted features from events
            
        Returns:
            Dictionary of detected patterns with scores
        """
        patterns = {}
        
        # Detect each pattern type
        patterns['task_switching'] = self._detect_task_switching(events)
        patterns['error_clustering'] = self._detect_error_clustering(events)
        patterns['procrastination_loops'] = self._detect_procrastination_loops(events)
        patterns['browsing_drift'] = self._detect_browsing_drift(events)
        patterns['avoidance_behavior'] = self._detect_avoidance_behavior(events)
        patterns['micro_breaks'] = self._detect_micro_break_patterns(events)
        patterns['night_degradation'] = self._detect_night_degradation(events, features)
        
        return patterns
    
    def _detect_task_switching(self, events: List[Dict]) -> Dict:
        """
        Detect rapid context switching indicating cognitive overload.
        Threshold: >5 switches in 2 minutes
        """
        if len(events) < 5:
            return {'detected': False, 'score': 0, 'details': 'Insufficient data'}
        
        # Look for navigation events within 2-minute windows
        nav_events = [e for e in events if e.get('type') == 'NAVIGATION']
        
        if len(nav_events) < 5:
            return {'detected': False, 'score': 0, 'details': 'No rapid switching'}
        
        # Check for switches in 2-minute windows
        rapid_switches = 0
        window_size = 120000  # 2 minutes in milliseconds
        
        for i in range(len(nav_events) - 4):
            window_start = nav_events[i].get('timestamp', 0)
            window_end = nav_events[i + 4].get('timestamp', 0)
            
            if window_end - window_start <= window_size:
                rapid_switches += 1
        
        detected = rapid_switches > 0
        score = min(rapid_switches * 15, 100)  # Scale score
        
        return {
            'detected': detected,
            'score': score,
            'details': f'Detected {rapid_switches} rapid switching windows',
            'switch_count': rapid_switches
        }
    
    def _detect_error_clustering(self, events: List[Dict]) -> Dict:
        """
        Detect error bursts suggesting mental fatigue.
        Threshold: 3+ errors within 5 minutes
        """
        error_events = [e for e in events if 
                       e.get('type') == 'ERROR' or 
                       e.get('metadata', {}).get('hasError', False)]
        
        if len(error_events) < 3:
            return {'detected': False, 'score': 0, 'details': 'No error clustering'}
        
        # Check for error clusters in 5-minute windows
        clusters = 0
        window_size = 300000  # 5 minutes in milliseconds
        
        for i in range(len(error_events) - 2):
            window_start = error_events[i].get('timestamp', 0)
            window_end = error_events[i + 2].get('timestamp', 0)
            
            if window_end - window_start <= window_size:
                clusters += 1
        
        detected = clusters > 0
        score = min(clusters * 20, 100)
        
        return {
            'detected': detected,
            'score': score,
            'details': f'Detected {clusters} error clusters',
            'cluster_count': clusters,
            'total_errors': len(error_events)
        }
    
    def _detect_procrastination_loops(self, events: List[Dict]) -> Dict:
        """
        Recognize repeated idle-navigation-idle cycles.
        """
        if len(events) < 3:
            return {'detected': False, 'score': 0, 'details': 'Insufficient data'}
        
        # Look for idle -> navigation -> idle patterns
        loop_count = 0
        
        for i in range(len(events) - 2):
            if (events[i].get('type') == 'IDLE' and
                events[i + 1].get('type') == 'NAVIGATION' and
                events[i + 2].get('type') == 'IDLE'):
                loop_count += 1
        
        detected = loop_count >= 2
        score = min(loop_count * 15, 100)
        
        return {
            'detected': detected,
            'score': score,
            'details': f'Detected {loop_count} procrastination loops',
            'loop_count': loop_count
        }
    
    def _detect_browsing_drift(self, events: List[Dict]) -> Dict:
        """
        Track navigation away from learning content with quick returns.
        """
        nav_events = [e for e in events if e.get('type') == 'NAVIGATION']
        
        if len(nav_events) < 2:
            return {'detected': False, 'score': 0, 'details': 'Insufficient navigation'}
        
        # Look for quick back-and-forth navigation
        drift_count = 0
        quick_return_threshold = 30000  # 30 seconds
        
        for i in range(len(nav_events) - 1):
            time_diff = nav_events[i + 1].get('timestamp', 0) - nav_events[i].get('timestamp', 0)
            
            if time_diff < quick_return_threshold:
                drift_count += 1
        
        detected = drift_count >= 3
        score = min(drift_count * 10, 100)
        
        return {
            'detected': detected,
            'score': score,
            'details': f'Detected {drift_count} browsing drift instances',
            'drift_count': drift_count
        }
    
    def _detect_avoidance_behavior(self, events: List[Dict]) -> Dict:
        """
        Identify topics with consistently low engagement time.
        Threshold: <30% of average time
        """
        # Group events by module/topic
        topic_times = defaultdict(float)
        
        for event in events:
            metadata = event.get('metadata', {})
            topic = metadata.get('moduleId') or metadata.get('topicId')
            duration = event.get('duration', 0)
            
            if topic:
                topic_times[topic] += duration
        
        if len(topic_times) < 2:
            return {'detected': False, 'score': 0, 'details': 'Insufficient topic data'}
        
        # Calculate average time per topic
        avg_time = statistics.mean(topic_times.values())
        threshold = avg_time * 0.3
        
        # Find avoided topics
        avoided_topics = [topic for topic, time in topic_times.items() if time < threshold]
        
        detected = len(avoided_topics) > 0
        score = min(len(avoided_topics) * 20, 100)
        
        return {
            'detected': detected,
            'score': score,
            'details': f'Detected avoidance of {len(avoided_topics)} topics',
            'avoided_topics': avoided_topics,
            'total_topics': len(topic_times)
        }
    
    def _detect_micro_break_patterns(self, events: List[Dict]) -> Dict:
        """
        Analyze break frequency and duration.
        Optimal: 5-10 min breaks every 25-50 min
        """
        idle_events = [e for e in events if e.get('type') == 'IDLE']
        
        if len(idle_events) < 2:
            return {'detected': False, 'score': 0, 'details': 'No break data'}
        
        # Analyze break durations
        break_durations = []
        break_intervals = []
        
        for i, event in enumerate(idle_events):
            duration = event.get('duration', 0) / 1000  # Convert to seconds
            if duration >= 60:  # At least 1 minute idle counts as break
                break_durations.append(duration / 60)  # Convert to minutes
                
                if i > 0:
                    interval = (event.get('timestamp', 0) - 
                               idle_events[i-1].get('timestamp', 0)) / 60000  # Minutes
                    break_intervals.append(interval)
        
        if not break_durations:
            return {'detected': True, 'score': 30, 'details': 'No breaks detected - concerning'}
        
        # Calculate break quality score
        avg_duration = statistics.mean(break_durations)
        avg_interval = statistics.mean(break_intervals) if break_intervals else 0
        
        # Optimal break: 5-10 minutes every 25-50 minutes
        duration_optimal = 5 <= avg_duration <= 10
        interval_optimal = 25 <= avg_interval <= 50
        
        if duration_optimal and interval_optimal:
            score = 0  # Good break pattern
            details = 'Healthy break pattern'
        elif avg_interval > 100:
            score = 60  # Too few breaks
            details = 'Insufficient break frequency'
        elif avg_duration < 3:
            score = 40  # Breaks too short
            details = 'Breaks too short'
        else:
            score = 20
            details = 'Suboptimal break pattern'
        
        return {
            'detected': score > 0,
            'score': score,
            'details': details,
            'avg_break_duration': avg_duration,
            'avg_break_interval': avg_interval,
            'total_breaks': len(break_durations)
        }
    
    def _detect_night_degradation(self, events: List[Dict], features: Dict) -> Dict:
        """
        Compare performance metrics during night hours vs day hours.
        Night hours: 10 PM - 6 AM
        """
        is_night = features.get('is_night_hours', False)
        
        if not is_night:
            return {'detected': False, 'score': 0, 'details': 'Daytime session'}
        
        # During night hours, apply degradation factor
        hour = features.get('hour_of_day', 0)
        
        # Peak degradation at 2-4 AM
        if 2 <= hour <= 4:
            score = 80
            details = 'Peak night degradation period'
        elif 22 <= hour or hour <= 6:
            score = 50
            details = 'Night hours - reduced cognitive capacity'
        else:
            score = 0
            details = 'Normal hours'
        
        return {
            'detected': score > 0,
            'score': score,
            'details': details,
            'hour': hour
        }


class MentalStrainClassifier:
    """Classifies mental strain levels using rule-based heuristics."""
    
    STRAIN_LEVELS = {
        'minimal': (0, 25),
        'moderate': (25, 50),
        'high': (50, 75),
        'critical': (75, 100)
    }
    
    def __init__(self):
        self.decay_half_life = 15  # minutes
        
    def classify(self, pattern_scores: Dict) -> Dict:
        """
        Combine multiple pattern signals with weighted scoring.
        
        Args:
            pattern_scores: Dictionary of pattern detection results
            
        Returns:
            Classification result with strain level and score
        """
        # Extract scores from patterns
        scores = []
        detected_patterns = []
        
        for pattern_name, pattern_data in pattern_scores.items():
            if pattern_data.get('detected', False):
                score = pattern_data.get('score', 0)
                scores.append(score)
                detected_patterns.append(pattern_name)
        
        if not scores:
            combined_score = 0
        else:
            # Combine scores with weighted average
            combined_score = statistics.mean(scores)
        
        # Determine strain level
        strain_level = self._get_strain_level(combined_score)
        
        return {
            'mental_strain_score': combined_score,
            'strain_level': strain_level,
            'detected_patterns': detected_patterns,
            'pattern_count': len(detected_patterns),
            'individual_scores': {k: v.get('score', 0) for k, v in pattern_scores.items()}
        }
    
    def _get_strain_level(self, score: float) -> str:
        """Determine strain level from score."""
        for level, (min_score, max_score) in self.STRAIN_LEVELS.items():
            if min_score <= score < max_score:
                return level
        return 'critical'
    
    def apply_temporal_decay(self, score: float, minutes_elapsed: float) -> float:
        """
        Apply exponential decay to older pattern scores.
        Half-life: 15 minutes
        """
        decay_factor = math.exp(-0.693 * minutes_elapsed / self.decay_half_life)
        return score * decay_factor


class HistoricalBaselineTracker:
    """Establishes student-specific normal patterns and detects anomalies."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.baseline_window = 7  # days
        
    def calculate_baseline(self, student_id: str, historical_data: List[Dict]) -> Dict:
        """
        Calculate baseline metrics from historical data.
        
        Args:
            student_id: Student identifier
            historical_data: List of historical cognitive load measurements
            
        Returns:
            Baseline metrics dictionary
        """
        if not historical_data:
            return self._default_baseline()
        
        # Extract metrics
        cognitive_loads = [d.get('cognitive_load_score', 0) for d in historical_data]
        task_switches = [d.get('task_switching_count', 0) for d in historical_data]
        error_rates = [d.get('error_rate', 0) for d in historical_data]
        productivity_scores = [d.get('productivity_score', 0) for d in historical_data]
        
        baseline = {
            'avg_cognitive_load': statistics.mean(cognitive_loads) if cognitive_loads else 0,
            'std_cognitive_load': statistics.stdev(cognitive_loads) if len(cognitive_loads) > 1 else 0,
            'avg_task_switching': statistics.mean(task_switches) if task_switches else 0,
            'avg_error_rate': statistics.mean(error_rates) if error_rates else 0,
            'avg_productivity': statistics.mean(productivity_scores) if productivity_scores else 0,
            'data_points': len(historical_data),
            'calculated_at': datetime.now().isoformat()
        }
        
        return baseline
    
    def detect_anomaly(self, current_value: float, baseline: Dict, metric_name: str = 'cognitive_load') -> Dict:
        """
        Detect if current value is anomalous compared to baseline.
        Uses z-score threshold of 2.0 (2 standard deviations)
        """
        avg_key = f'avg_{metric_name}'
        std_key = f'std_{metric_name}'
        
        avg = baseline.get(avg_key, 0)
        std = baseline.get(std_key, 0)
        
        if std == 0:
            z_score = 0
        else:
            z_score = (current_value - avg) / std
        
        is_anomaly = abs(z_score) > 2.0
        
        return {
            'is_anomaly': is_anomaly,
            'z_score': z_score,
            'current_value': current_value,
            'baseline_avg': avg,
            'baseline_std': std,
            'deviation_direction': 'above' if z_score > 0 else 'below'
        }
    
    def _default_baseline(self) -> Dict:
        """Return default baseline when no historical data exists."""
        return {
            'avg_cognitive_load': 40.0,
            'std_cognitive_load': 15.0,
            'avg_task_switching': 3.0,
            'avg_error_rate': 0.1,
            'avg_productivity': 0.7,
            'data_points': 0,
            'calculated_at': datetime.now().isoformat()
        }
