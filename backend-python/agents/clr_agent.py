"""
Enhanced Cognitive Load Radar (CLR) Agent

This module provides an advanced CLR Agent that combines:
1. Basic weighted metrics (existing calculation)
2. ML-based pattern recognition
3. Mood analysis from text and typing patterns
4. Historical baseline comparison
5. LLM-powered insights
6. Predictive analytics
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics
from langchain_core.prompts import ChatPromptTemplate

from agents.base_agent import BaseAgent
from agents.state import AgentState
from ml.cognitive_patterns import (
    CognitivePatternDetector,
    PatternFeatureExtractor,
    MentalStrainClassifier,
    HistoricalBaselineTracker
)
from ml.sentiment_analyzer import MoodAnalyzer, TypingPatternMoodDetector, MoodTrendAnalyzer
from ml.text_processor import TextProcessor


class CognitiveLoadRadarAgent(BaseAgent):
    """Enhanced CLR Agent with multi-layered cognitive load analysis."""
    
    def __init__(self):
        super().__init__("clr_agent")
        
        # Initialize pattern recognition components
        self.pattern_detector = CognitivePatternDetector()
        self.feature_extractor = PatternFeatureExtractor()
        self.strain_classifier = MentalStrainClassifier()
        self.baseline_tracker = HistoricalBaselineTracker()
        
        # Initialize mood analysis components
        self.mood_analyzer = MoodAnalyzer(self.llm)
        self.typing_mood_detector = TypingPatternMoodDetector()
        self.mood_trend_analyzer = MoodTrendAnalyzer()
        
        # LLM prompt for insights generation
        self.insights_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert educational psychologist analyzing student cognitive load data.
Generate 2-3 personalized insights about the student's learning state and provide specific, actionable recommendations.
Be empathetic but concise. Focus on practical advice."""),
            ("human", """Student cognitive load data:
- Cognitive Load Score: {score}/100
- Mental Fatigue Level: {fatigue_level}
- Detected Patterns: {patterns}
- Mood Indicators: {mood}
- Session Duration: {duration} minutes

Generate insights and recommendations:""")
        ])
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute enhanced cognitive load analysis.
        
        Args:
            state: Current agent state with behavioral data
            
        Returns:
            Updated state with CLR results
        """
        try:
            student_id = state.get("student_id", "unknown")
            session_id = state.get("session_id", "unknown")
            events = state.get("behavioral_events", [])
            
            if not events:
                return self._empty_result(state)
            
            # Calculate comprehensive cognitive load
            clr_result = await self.calculate_cognitive_load_detailed(events, student_id, session_id)
            
            # Generate personalized insights
            insights = self.generate_personalized_insights(clr_result)
            clr_result['insights'] = insights
            
            # Store results in Redis time-series
            await self._store_clr_result(student_id, session_id, clr_result)
            
            # Publish update via Redis pub/sub
            await self.publish_event('clr_update', {
                'student_id': student_id,
                'session_id': session_id,
                'cognitive_load_score': clr_result['cognitive_load_score'],
                'mental_fatigue_level': clr_result['mental_fatigue_level'],
                'detected_patterns': clr_result['detected_patterns'],
                'recommendations': clr_result['recommendations'],
                'timestamp': int(datetime.now().timestamp() * 1000)
            })
            
            # Update state
            state["clr_result"] = clr_result
            state["status"] = "completed"
            
            return state
            
        except Exception as e:
            self.logger.error(f"CLR Agent execution error: {str(e)}")
            state["status"] = "error"
            state["error"] = str(e)
            return state
    
    async def calculate_cognitive_load_detailed(self, events: List[Dict], student_id: str, session_id: str) -> Dict:
        """
        Multi-layered cognitive load calculation.
        
        Combines:
        - Layer 1: Basic weighted metrics
        - Layer 2: Pattern recognition
        - Layer 3: Mood analysis
        - Layer 4: Historical baseline comparison
        
        Args:
            events: Behavioral events
            student_id: Student identifier
            session_id: Session identifier
            
        Returns:
            Comprehensive CLR breakdown
        """
        # Layer 1: Basic Metrics (existing weighted calculation)
        basic_score = self._calculate_basic_metrics(events)
        
        # Layer 2: Pattern Recognition
        features = self.feature_extractor.extract_features(events)
        patterns = self.pattern_detector.detect_patterns(events, features)
        strain_result = self.strain_classifier.classify(patterns)
        pattern_adjustment = self._calculate_pattern_adjustment(strain_result)
        
        # Layer 3: Mood Analysis
        mood_result = self._analyze_mood(events)
        mood_adjustment = self._calculate_mood_adjustment(mood_result)
        
        # Layer 4: Historical Baseline Comparison
        baseline = await self._get_baseline(student_id)
        baseline_deviation = self._calculate_baseline_deviation(basic_score, baseline)
        
        # Combine all layers
        final_score = min(100, max(0, 
            basic_score + pattern_adjustment + mood_adjustment + baseline_deviation
        ))
        
        # Determine fatigue level
        fatigue_level = self._determine_fatigue_level(final_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            final_score, patterns, mood_result, baseline_deviation
        )
        
        # Determine intervention urgency
        intervention_urgency = self._determine_intervention_urgency(
            final_score, strain_result, mood_result
        )
        
        return {
            'cognitive_load_score': final_score,
            'mental_fatigue_level': fatigue_level,
            'component_scores': {
                'basic_metrics': basic_score,
                'pattern_adjustment': pattern_adjustment,
                'mood_adjustment': mood_adjustment,
                'baseline_deviation': baseline_deviation
            },
            'detected_patterns': [p for p, d in patterns.items() if d.get('detected', False)],
            'pattern_details': patterns,
            'mood_indicators': mood_result,
            'baseline_comparison': {
                'current_vs_baseline': baseline_deviation,
                'baseline_metrics': baseline
            },
            'recommendations': recommendations,
            'intervention_urgency': intervention_urgency,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
    
    def _calculate_basic_metrics(self, events: List[Dict]) -> float:
        """
        Calculate basic weighted cognitive load (existing algorithm).
        
        Weights:
        - Task switching: 25%
        - Error rate: 20%
        - Procrastination: 20%
        - Browsing drift: 15%
        - Time per concept: 10%
        - Productivity: 10%
        """
        if not events:
            return 0.0
        
        # Count event types
        event_counts = {}
        for event in events:
            event_type = event.get('type', 'unknown')
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        total_events = len(events)
        
        # Task switching frequency (navigation events)
        task_switching_score = min(100, (event_counts.get('NAVIGATION', 0) / total_events) * 200)
        
        # Error rate
        error_count = sum(1 for e in events if e.get('metadata', {}).get('hasError', False))
        error_score = min(100, (error_count / total_events) * 300)
        
        # Procrastination (idle events)
        idle_count = event_counts.get('IDLE', 0)
        procrastination_score = min(100, (idle_count / total_events) * 250)
        
        # Browsing drift (rapid navigation)
        nav_events = [e for e in events if e.get('type') == 'NAVIGATION']
        if len(nav_events) > 1:
            rapid_nav = sum(1 for i in range(len(nav_events) - 1)
                          if (nav_events[i+1].get('timestamp', 0) - 
                              nav_events[i].get('timestamp', 0)) < 30000)
            browsing_drift_score = min(100, (rapid_nav / len(nav_events)) * 200)
        else:
            browsing_drift_score = 0
        
        # Time per concept (average duration)
        durations = [e.get('duration', 0) for e in events if e.get('duration', 0) > 0]
        if durations:
            avg_duration = statistics.mean(durations) / 1000  # Convert to seconds
            # Short durations indicate rushing/overload
            if avg_duration < 10:
                time_score = 80
            elif avg_duration < 30:
                time_score = 50
            else:
                time_score = 20
        else:
            time_score = 50
        
        # Productivity (inverse of idle time)
        active_time = sum(e.get('duration', 0) for e in events if e.get('type') != 'IDLE')
        total_time = sum(e.get('duration', 0) for e in events)
        if total_time > 0:
            productivity_ratio = active_time / total_time
            productivity_score = (1 - productivity_ratio) * 100
        else:
            productivity_score = 50
        
        # Weighted combination
        weighted_score = (
            task_switching_score * 0.25 +
            error_score * 0.20 +
            procrastination_score * 0.20 +
            browsing_drift_score * 0.15 +
            time_score * 0.10 +
            productivity_score * 0.10
        )
        
        return weighted_score
    
    def _calculate_pattern_adjustment(self, strain_result: Dict) -> float:
        """Calculate adjustment based on detected patterns."""
        strain_level = strain_result.get('strain_level', 'minimal')
        
        adjustments = {
            'minimal': 0,
            'moderate': 5,
            'high': 10,
            'critical': 15
        }
        
        return adjustments.get(strain_level, 0)
    
    def _analyze_mood(self, events: List[Dict]) -> Dict:
        """Analyze mood from events."""
        # Extract text from events
        texts = TextProcessor.extract_text_from_events(events)
        preprocessed_texts = TextProcessor.batch_preprocess(texts)
        
        mood_scores = []
        
        # Analyze text mood
        if preprocessed_texts:
            for text in preprocessed_texts[:3]:  # Analyze up to 3 texts to reduce LLM calls
                mood_result = self.mood_analyzer.analyze_text(text)
                mood_scores.append(mood_result['mood_score'])
        
        # Analyze typing patterns
        typing_events = [e for e in events if e.get('type') == 'TYPING_PATTERN']
        for typing_event in typing_events[-3:]:  # Last 3 typing events
            typing_data = typing_event.get('metadata', {})
            typing_mood = self.typing_mood_detector.analyze_typing_pattern(typing_data)
            mood_scores.append(typing_mood['mood_score'])
        
        # Calculate overall mood
        if mood_scores:
            avg_mood = statistics.mean(mood_scores)
            dominant_emotion = self._determine_dominant_emotion(avg_mood)
        else:
            avg_mood = 0.0
            dominant_emotion = 'neutral'
        
        return {
            'mood_score': avg_mood,
            'dominant_emotion': dominant_emotion,
            'text_analyzed': len(preprocessed_texts),
            'typing_patterns_analyzed': min(3, len(typing_events))
        }
    
    def _determine_dominant_emotion(self, mood_score: float) -> str:
        """Determine emotion from mood score."""
        if mood_score > 0.5:
            return 'confident'
        elif mood_score > 0.2:
            return 'engaged'
        elif mood_score > -0.2:
            return 'neutral'
        elif mood_score > -0.5:
            return 'confused'
        else:
            return 'frustrated'
    
    def _calculate_mood_adjustment(self, mood_result: Dict) -> float:
        """Calculate cognitive load adjustment based on mood."""
        mood_score = mood_result.get('mood_score', 0.0)
        
        # Negative mood increases cognitive load
        if mood_score < -0.5:
            return 20
        elif mood_score < -0.2:
            return 10
        elif mood_score < 0:
            return 5
        else:
            return 0
    
    async def _get_baseline(self, student_id: str) -> Dict:
        """Get student's baseline metrics from Redis or calculate default."""
        try:
            from config.redis_client import redis_client
            
            # Try to get cached baseline from Redis
            baseline_key = f"baseline:{student_id}"
            baseline_data = await redis_client.data_client.hgetall(baseline_key)
            
            if baseline_data and 'avg_load' in baseline_data:
                return {
                    'avg_cognitive_load': float(baseline_data['avg_load']),
                    'std_cognitive_load': float(baseline_data['std_load']),
                    'calculated_at': baseline_data.get('calculated_at', '')
                }
            
            # If not in cache, calculate from storage
            from services.clr_storage import clr_storage_service
            baseline = await clr_storage_service.calculate_baseline_metrics(student_id, days=7)
            return baseline
            
        except Exception as e:
            self.logger.warning(f"Failed to retrieve baseline, using default: {str(e)}")
            return self.baseline_tracker._default_baseline()
    
    def _calculate_baseline_deviation(self, current_score: float, baseline: Dict) -> float:
        """Calculate deviation from baseline."""
        baseline_avg = baseline.get('avg_cognitive_load', 40.0)
        baseline_std = baseline.get('std_cognitive_load', 15.0)
        
        if baseline_std == 0:
            return 0.0
        
        z_score = (current_score - baseline_avg) / baseline_std
        
        # Add points if significantly above baseline
        if z_score > 2.0:
            return 15  # Significantly higher than normal
        elif z_score > 1.0:
            return 8   # Moderately higher than normal
        else:
            return 0
    
    def _determine_fatigue_level(self, score: float) -> str:
        """Determine fatigue level from score."""
        if score < 25:
            return 'low'
        elif score < 50:
            return 'medium'
        elif score < 75:
            return 'high'
        else:
            return 'critical'
    
    def _generate_recommendations(self, score: float, patterns: Dict, 
                                  mood: Dict, baseline_dev: float) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Score-based recommendations
        if score >= 75:
            recommendations.append("Take a break immediately - cognitive load is critical")
        elif score >= 50:
            recommendations.append("Consider taking a 5-10 minute break soon")
        
        # Pattern-based recommendations
        if patterns.get('task_switching', {}).get('detected', False):
            recommendations.append("Try to focus on one topic at a time to reduce task switching")
        
        if patterns.get('error_clustering', {}).get('detected', False):
            recommendations.append("Error patterns detected - review recent material or seek help")
        
        if patterns.get('procrastination_loops', {}).get('detected', False):
            recommendations.append("Break down tasks into smaller chunks to maintain engagement")
        
        if patterns.get('night_degradation', {}).get('detected', False):
            recommendations.append("Cognitive performance is reduced during night hours - consider studying earlier")
        
        micro_breaks = patterns.get('micro_breaks', {})
        if micro_breaks.get('score', 0) > 30:
            recommendations.append("Take regular 5-10 minute breaks every 25-50 minutes")
        
        # Mood-based recommendations
        mood_score = mood.get('mood_score', 0)
        if mood_score < -0.5:
            recommendations.append("Frustration detected - try a different learning approach or ask for help")
        
        # Baseline deviation recommendations
        if baseline_dev > 10:
            recommendations.append("Your cognitive load is significantly higher than your usual pattern")
        
        return recommendations
    
    def _determine_intervention_urgency(self, score: float, strain: Dict, mood: Dict) -> str:
        """Determine intervention urgency level."""
        if score >= 85:
            return 'critical'
        elif score >= 70:
            return 'high'
        elif score >= 50:
            return 'medium'
        elif strain.get('strain_level') == 'high' or mood.get('mood_score', 0) < -0.6:
            return 'medium'
        else:
            return 'low'
    
    def generate_personalized_insights(self, clr_data: Dict) -> str:
        """
        Generate personalized insights using LLM.
        
        Args:
            clr_data: Cognitive load data dictionary
            
        Returns:
            AI-generated insights and recommendations
        """
        try:
            # Check cache first (5-minute TTL)
            # TODO: Implement Redis caching
            
            # Prepare data for LLM
            score = clr_data['cognitive_load_score']
            fatigue = clr_data['mental_fatigue_level']
            patterns = ', '.join(clr_data['detected_patterns']) if clr_data['detected_patterns'] else 'none'
            mood = clr_data['mood_indicators'].get('dominant_emotion', 'neutral')
            
            # Calculate session duration
            timestamp = clr_data.get('timestamp', datetime.now().timestamp() * 1000)
            duration = 30  # Default to 30 minutes
            
            # Generate insights
            messages = self.insights_prompt.format_messages(
                score=score,
                fatigue_level=fatigue,
                patterns=patterns,
                mood=mood,
                duration=duration
            )
            
            response = self.llm.invoke(messages)
            insights = response.content.strip()
            
            # Cache result
            # TODO: Cache in Redis with 5-minute TTL
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to generate insights: {str(e)}")
            return "Unable to generate personalized insights at this time."
    
    async def predict_cognitive_load_trajectory(self, student_id: str) -> Dict:
        """
        Predict cognitive load for next 15-30 minutes.
        
        Args:
            student_id: Student identifier
            
        Returns:
            Prediction with trajectory and recommendations
        """
        try:
            from services.clr_storage import clr_storage_service
            
            # Get recent trend data
            trend_15min = await clr_storage_service.get_cognitive_load_trend(student_id, window_minutes=15)
            trend_30min = await clr_storage_service.get_cognitive_load_trend(student_id, window_minutes=30)
            
            # Get current load
            history_data = await clr_storage_service.get_cognitive_load_history(student_id, 'last_hour')
            history = history_data.get('history', [])
            
            if not history:
                return {
                    'predicted_load_15min': 0.0,
                    'predicted_load_30min': 0.0,
                    'trend': 'unknown',
                    'confidence': 0.0,
                    'early_intervention_needed': False,
                    'recommendations': ['Insufficient data for prediction']
                }
            
            current_score = history[-1]['score']
            slope_15 = trend_15min.get('slope', 0.0)
            slope_30 = trend_30min.get('slope', 0.0)
            
            # Simple linear extrapolation
            predicted_15min = min(100, max(0, current_score + (slope_15 * 15)))
            predicted_30min = min(100, max(0, current_score + (slope_30 * 30)))
            
            # Determine overall trend
            if slope_30 > 0.5:
                trend = 'increasing'
            elif slope_30 < -0.5:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Check if intervention is needed
            early_intervention_needed = predicted_15min > 75 or predicted_30min > 80
            
            # Generate recommendations
            recommendations = []
            if early_intervention_needed:
                recommendations.append("High cognitive load predicted - consider taking a break soon")
            if trend == 'increasing':
                recommendations.append("Cognitive load is trending upward - monitor fatigue levels")
            if predicted_30min > 90:
                recommendations.append("Critical load predicted within 30 minutes - immediate break recommended")
            
            confidence = min(trend_30min.get('confidence', 0.0), trend_15min.get('confidence', 0.0))
            
            return {
                'predicted_load_15min': predicted_15min,
                'predicted_load_30min': predicted_30min,
                'trend': trend,
                'confidence': confidence,
                'early_intervention_needed': early_intervention_needed,
                'recommendations': recommendations if recommendations else ['Cognitive load appears manageable']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to predict trajectory: {str(e)}")
            return {
                'predicted_load_15min': 0.0,
                'predicted_load_30min': 0.0,
                'trend': 'unknown',
                'confidence': 0.0,
                'early_intervention_needed': False,
                'recommendations': ['Prediction unavailable']
            }
    
    async def _store_clr_result(self, student_id: str, session_id: str, clr_data: Dict):
        """Store CLR result in Redis time-series."""
        try:
            from services.clr_storage import clr_storage_service
            await clr_storage_service.store_cognitive_load(student_id, session_id, clr_data)
        except Exception as e:
            self.logger.error(f"Failed to store CLR result: {str(e)}")
    
    def _empty_result(self, state: AgentState) -> AgentState:
        """Return empty result when no events available."""
        state["clr_result"] = {
            'cognitive_load_score': 0,
            'mental_fatigue_level': 'low',
            'component_scores': {},
            'detected_patterns': [],
            'mood_indicators': {},
            'recommendations': ["No behavioral data available yet"],
            'intervention_urgency': 'none'
        }
        state["status"] = "completed"
        return state
