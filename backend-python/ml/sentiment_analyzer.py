"""
Sentiment Analysis and Mood Tracking Module

This module provides sentiment analysis capabilities for mood tracking from:
- Text inputs (quiz answers, search queries)
- Typing patterns (WPM, backspace rate, pauses)
- Temporal mood trends
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import json


class MoodAnalyzer:
    """Analyzes mood from text inputs using LLM-based sentiment analysis."""
    
    def __init__(self, llm: ChatGoogleGenerativeAI):
        """
        Initialize mood analyzer with LLM.
        
        Args:
            llm: Google Generative AI LLM instance
        """
        self.llm = llm
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing student emotional states from their text.
Analyze the emotional tone considering: frustration, confidence, confusion, and engagement.
Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{
    "mood_score": <float between -1 and 1>,
    "dominant_emotion": "<emotion name>",
    "confidence": <float between 0 and 1>,
    "explanation": "<brief explanation>"
}"""),
            ("human", "Analyze this student's text: {text}")
        ])
    
    def analyze_text(self, text: str, context: str = "") -> Dict:
        """
        Analyze mood from text input.
        
        Args:
            text: Text to analyze
            context: Optional context about where text came from
            
        Returns:
            Dictionary with mood analysis results
        """
        if not text or not text.strip():
            return self._neutral_mood("Empty text")
        
        try:
            # Create prompt
            messages = self.prompt_template.format_messages(text=text)
            
            # Get LLM response
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            # Parse JSON response
            result = json.loads(response_text)
            
            # Validate structure
            if not all(k in result for k in ['mood_score', 'dominant_emotion', 'confidence', 'explanation']):
                return self._neutral_mood("Invalid LLM response structure")
            
            # Clamp values
            result['mood_score'] = max(-1.0, min(1.0, float(result['mood_score'])))
            result['confidence'] = max(0.0, min(1.0, float(result['confidence'])))
            
            return result
            
        except json.JSONDecodeError:
            return self._neutral_mood("Failed to parse LLM response")
        except Exception as e:
            return self._neutral_mood(f"Analysis error: {str(e)}")
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        Analyze mood for multiple texts efficiently.
        
        Args:
            texts: List of text strings to analyze
            
        Returns:
            List of mood analysis results
        """
        results = []
        for text in texts:
            result = self.analyze_text(text)
            results.append(result)
        return results
    
    def _neutral_mood(self, reason: str) -> Dict:
        """Return neutral mood result."""
        return {
            'mood_score': 0.0,
            'dominant_emotion': 'neutral',
            'confidence': 0.0,
            'explanation': reason
        }


class TypingPatternMoodDetector:
    """Infers mood from typing behavior patterns."""
    
    def __init__(self):
        self.baseline_wpm = 40.0  # Average typing speed
        self.baseline_backspace_rate = 0.1  # 10% corrections
    
    def analyze_typing_pattern(self, typing_data: Dict) -> Dict:
        """
        Analyze mood from typing pattern data.
        
        Args:
            typing_data: Dictionary with typing metrics (wpm, backspaceRate, pauses, etc.)
            
        Returns:
            Mood analysis based on typing behavior
        """
        wpm = typing_data.get('wpm', 0)
        backspace_rate = typing_data.get('backspaceRate', 0)
        pauses = typing_data.get('pauses', 0)
        corrections = typing_data.get('corrections', 0)
        
        # Calculate mood indicators
        mood_score = 0.0
        confidence = 0.5
        emotion = 'neutral'
        explanation_parts = []
        
        # High backspace rate + low WPM → frustration/confusion
        if backspace_rate > 0.2 and wpm < self.baseline_wpm * 0.7:
            mood_score = -0.65
            emotion = 'frustrated'
            explanation_parts.append("High correction rate with slow typing suggests frustration")
            confidence = 0.7
        
        # Consistent WPM + low corrections → confidence
        elif backspace_rate < 0.08 and self.baseline_wpm * 0.9 <= wpm <= self.baseline_wpm * 1.3:
            mood_score = 0.65
            emotion = 'confident'
            explanation_parts.append("Consistent typing with few corrections indicates confidence")
            confidence = 0.8
        
        # Erratic typing with long pauses → cognitive overload
        elif pauses > 10 and backspace_rate > 0.15:
            mood_score = -0.45
            emotion = 'overwhelmed'
            explanation_parts.append("Frequent pauses and corrections suggest cognitive overload")
            confidence = 0.75
        
        # Very fast typing → engagement
        elif wpm > self.baseline_wpm * 1.4 and backspace_rate < 0.12:
            mood_score = 0.5
            emotion = 'engaged'
            explanation_parts.append("Fast, accurate typing indicates high engagement")
            confidence = 0.7
        
        # Very slow typing → confusion or fatigue
        elif wpm < self.baseline_wpm * 0.5:
            mood_score = -0.3
            emotion = 'confused'
            explanation_parts.append("Very slow typing may indicate confusion or fatigue")
            confidence = 0.6
        
        else:
            explanation_parts.append("Typing pattern within normal range")
        
        # Calculate typing consistency score
        consistency_score = self._calculate_consistency(typing_data)
        explanation_parts.append(f"Consistency: {consistency_score:.2f}")
        
        return {
            'mood_score': mood_score,
            'dominant_emotion': emotion,
            'confidence': confidence,
            'explanation': '; '.join(explanation_parts),
            'typing_metrics': {
                'wpm': wpm,
                'backspace_rate': backspace_rate,
                'pauses': pauses,
                'consistency_score': consistency_score
            }
        }
    
    def _calculate_consistency(self, typing_data: Dict) -> float:
        """
        Calculate typing consistency score from WPM variance.
        Returns value between 0 (inconsistent) and 1 (very consistent).
        """
        wpm_variance = typing_data.get('wpmVariance', 0)
        
        # Lower variance = higher consistency
        # Normalize: variance of 0-100 maps to consistency of 1.0-0.0
        if wpm_variance <= 0:
            return 1.0
        
        consistency = max(0.0, 1.0 - (wpm_variance / 100.0))
        return consistency


class MoodTrendAnalyzer:
    """Analyzes temporal mood trends and detects significant changes."""
    
    def __init__(self, redis_client=None):
        """
        Initialize mood trend analyzer.
        
        Args:
            redis_client: Redis client for storing mood history
        """
        self.redis_client = redis_client
        self.mood_drop_threshold = 0.4  # Trigger intervention if mood drops by 0.4
        self.trend_window_minutes = 30
    
    def store_mood_score(self, student_id: str, mood_score: float, timestamp: int = None):
        """
        Store mood score in Redis sorted set.
        
        Args:
            student_id: Student identifier
            mood_score: Mood score (-1 to 1)
            timestamp: Unix timestamp in milliseconds (defaults to current time)
        """
        if not self.redis_client:
            return
        
        if timestamp is None:
            timestamp = int(datetime.now().timestamp() * 1000)
        
        # Store in Redis sorted set: mood:{student_id}
        key = f"mood:{student_id}"
        self.redis_client.zadd(key, {str(mood_score): timestamp})
        
        # Set TTL of 7 days
        self.redis_client.expire(key, 7 * 24 * 60 * 60)
    
    def get_mood_history(self, student_id: str, minutes: int = 30) -> List[Dict]:
        """
        Get mood history for specified time window.
        
        Args:
            student_id: Student identifier
            minutes: Time window in minutes
            
        Returns:
            List of mood scores with timestamps
        """
        if not self.redis_client:
            return []
        
        key = f"mood:{student_id}"
        cutoff_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp() * 1000)
        
        # Get scores from Redis
        results = self.redis_client.zrangebyscore(key, cutoff_time, '+inf', withscores=True)
        
        mood_history = []
        for score_str, timestamp in results:
            mood_history.append({
                'mood_score': float(score_str),
                'timestamp': int(timestamp)
            })
        
        return sorted(mood_history, key=lambda x: x['timestamp'])
    
    def calculate_mood_trend(self, student_id: str, window_minutes: int = 30) -> Dict:
        """
        Calculate mood trend over specified time window using linear regression.
        
        Args:
            student_id: Student identifier
            window_minutes: Time window in minutes
            
        Returns:
            Trend analysis with slope and direction
        """
        mood_history = self.get_mood_history(student_id, window_minutes)
        
        if len(mood_history) < 2:
            return {
                'trend': 'stable',
                'slope': 0.0,
                'confidence': 0.0,
                'data_points': len(mood_history)
            }
        
        # Calculate linear regression slope
        n = len(mood_history)
        x_values = list(range(n))
        y_values = [entry['mood_score'] for entry in mood_history]
        
        # Calculate means
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        # Calculate slope
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator
        
        # Determine trend direction
        if slope > 0.01:
            trend = 'improving'
        elif slope < -0.01:
            trend = 'declining'
        else:
            trend = 'stable'
        
        # Calculate confidence based on data points
        confidence = min(1.0, n / 10.0)  # Full confidence at 10+ data points
        
        return {
            'trend': trend,
            'slope': slope,
            'confidence': confidence,
            'data_points': n,
            'current_mood': y_values[-1] if y_values else 0.0,
            'avg_mood': y_mean
        }
    
    def detect_mood_drop(self, student_id: str, minutes: int = 15) -> Dict:
        """
        Detect significant mood drops that require intervention.
        
        Args:
            student_id: Student identifier
            minutes: Time window to check for drops
            
        Returns:
            Detection result with intervention flag
        """
        mood_history = self.get_mood_history(student_id, minutes)
        
        if len(mood_history) < 2:
            return {
                'drop_detected': False,
                'drop_magnitude': 0.0,
                'intervention_needed': False
            }
        
        # Compare first and last mood scores
        initial_mood = mood_history[0]['mood_score']
        current_mood = mood_history[-1]['mood_score']
        drop_magnitude = initial_mood - current_mood
        
        drop_detected = drop_magnitude >= self.mood_drop_threshold
        intervention_needed = drop_magnitude >= 0.6  # Severe drop
        
        return {
            'drop_detected': drop_detected,
            'drop_magnitude': drop_magnitude,
            'initial_mood': initial_mood,
            'current_mood': current_mood,
            'intervention_needed': intervention_needed,
            'time_window_minutes': minutes
        }
    
    def get_mood_summary(self, student_id: str) -> Dict:
        """
        Get comprehensive mood summary for student.
        
        Args:
            student_id: Student identifier
            
        Returns:
            Summary with current mood, trends, and alerts
        """
        # Get recent history
        history_30min = self.get_mood_history(student_id, 30)
        
        if not history_30min:
            return {
                'current_mood': 0.0,
                'avg_mood_30min': 0.0,
                'trend': 'unknown',
                'mood_drop_alert': False
            }
        
        # Current mood
        current_mood = history_30min[-1]['mood_score']
        
        # Average mood
        avg_mood = statistics.mean([entry['mood_score'] for entry in history_30min])
        
        # Trend
        trend_data = self.calculate_mood_trend(student_id, 30)
        
        # Drop detection
        drop_data = self.detect_mood_drop(student_id, 15)
        
        return {
            'current_mood': current_mood,
            'avg_mood_30min': avg_mood,
            'trend': trend_data['trend'],
            'trend_slope': trend_data['slope'],
            'mood_drop_alert': drop_data['drop_detected'],
            'intervention_needed': drop_data['intervention_needed'],
            'data_points': len(history_30min)
        }
