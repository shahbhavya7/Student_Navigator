"""
Improvement Curves and Performance Analytics Module

This module provides sophisticated analytics for tracking student learning progression,
calculating improvement curves, and analyzing performance metrics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import statistics
from collections import defaultdict


class ImprovementCurveCalculator:
    """Calculate learning velocity, improvement trends, and mastery levels"""
    
    def __init__(self):
        self.min_data_points = 3
    
    def calculate_learning_velocity(self, quiz_results: List[Dict]) -> float:
        """
        Calculate rate of improvement over time using linear regression on quiz scores.
        Returns velocity as percentage points per day.
        """
        if len(quiz_results) < self.min_data_points:
            return 0.0
        
        # Sort by date
        sorted_results = sorted(quiz_results, key=lambda x: x.get('completedAt', datetime.now()))
        
        # Extract scores as percentages
        scores = []
        dates = []
        for result in sorted_results:
            total = result.get('totalQuestions', 1)
            correct = result.get('correctAnswers', 0)
            score_pct = (correct / total * 100) if total > 0 else 0
            scores.append(score_pct)
            dates.append(result.get('completedAt', datetime.now()))
        
        if not dates or len(set(dates)) < 2:
            return 0.0
        
        # Simple linear regression
        n = len(scores)
        
        # Convert dates to days from first date
        first_date = dates[0]
        x_values = [(date - first_date).days for date in dates]
        y_values = scores
        
        # Calculate slope (velocity)
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        velocity = numerator / denominator
        return round(velocity, 2)
    
    def calculate_improvement_trend(self, quiz_results: List[Dict]) -> str:
        """
        Determine trend (improving, stable, declining) based on recent performance.
        Compares last 3 quizzes with previous 3 quizzes.
        """
        if len(quiz_results) < 3:
            return "insufficient_data"
        
        # Sort by date
        sorted_results = sorted(quiz_results, key=lambda x: x.get('completedAt', datetime.now()))
        
        # Calculate scores
        scores = []
        for result in sorted_results:
            total = result.get('totalQuestions', 1)
            correct = result.get('correctAnswers', 0)
            score_pct = (correct / total * 100) if total > 0 else 0
            scores.append(score_pct)
        
        # Compare recent vs previous
        if len(scores) >= 6:
            recent_avg = sum(scores[-3:]) / 3
            previous_avg = sum(scores[-6:-3]) / 3
        else:
            recent_avg = sum(scores[-min(3, len(scores)):]) / min(3, len(scores))
            previous_avg = sum(scores[:min(3, len(scores))]) / min(3, len(scores))
        
        diff = recent_avg - previous_avg
        
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        else:
            return "stable"
    
    def calculate_mastery_level(self, quiz_results: List[Dict], topic: str) -> float:
        """
        Calculate topic-specific mastery (0-100).
        Weighted average favoring recent performance.
        """
        topic_results = [r for r in quiz_results if r.get('topic') == topic]
        
        if not topic_results:
            return 0.0
        
        # Sort by date
        sorted_results = sorted(topic_results, key=lambda x: x.get('completedAt', datetime.now()))
        
        # Calculate weighted average (recent quizzes weighted higher)
        total_weight = 0
        weighted_sum = 0
        
        for idx, result in enumerate(sorted_results):
            weight = idx + 1  # Linear weight increase
            total = result.get('totalQuestions', 1)
            correct = result.get('correctAnswers', 0)
            score = (correct / total * 100) if total > 0 else 0
            
            weighted_sum += score * weight
            total_weight += weight
        
        mastery = weighted_sum / total_weight if total_weight > 0 else 0
        return round(mastery, 2)
    
    def detect_learning_plateau(self, quiz_results: List[Dict]) -> bool:
        """
        Detect if student has plateaued (no improvement over N attempts).
        Returns True if last 5 scores show no significant improvement.
        """
        if len(quiz_results) < 5:
            return False
        
        # Sort by date and get last 5
        sorted_results = sorted(quiz_results, key=lambda x: x.get('completedAt', datetime.now()))
        recent_results = sorted_results[-5:]
        
        scores = []
        for result in recent_results:
            total = result.get('totalQuestions', 1)
            correct = result.get('correctAnswers', 0)
            score_pct = (correct / total * 100) if total > 0 else 0
            scores.append(score_pct)
        
        # Check if variance is very low and mean is not improving
        if len(scores) < 2:
            return False
        
        variance = statistics.variance(scores)
        first_half_avg = sum(scores[:2]) / 2
        second_half_avg = sum(scores[-2:]) / 2
        improvement = second_half_avg - first_half_avg
        
        # Plateau if low variance and no improvement
        return variance < 25 and improvement < 2
    
    def calculate_retention_rate(self, quiz_results: List[Dict]) -> float:
        """
        Measure knowledge retention over time.
        Compare performance on repeated topics.
        """
        if len(quiz_results) < 2:
            return 100.0
        
        # Group by topic
        topic_scores = defaultdict(list)
        for result in quiz_results:
            topic = result.get('topic', 'unknown')
            total = result.get('totalQuestions', 1)
            correct = result.get('correctAnswers', 0)
            score = (correct / total * 100) if total > 0 else 0
            completed = result.get('completedAt', datetime.now())
            topic_scores[topic].append((completed, score))
        
        # Calculate retention for topics with multiple attempts
        retention_rates = []
        for topic, scores in topic_scores.items():
            if len(scores) < 2:
                continue
            
            # Sort by date
            scores.sort(key=lambda x: x[0])
            
            # Compare last attempt with first
            first_score = scores[0][1]
            last_score = scores[-1][1]
            
            if first_score > 0:
                retention = (last_score / first_score) * 100
                retention_rates.append(min(retention, 100))
        
        if not retention_rates:
            return 100.0
        
        return round(sum(retention_rates) / len(retention_rates), 2)
    
    def predict_next_performance(self, quiz_results: List[Dict]) -> float:
        """
        Simple linear extrapolation for next quiz score.
        Returns predicted score (0-100).
        """
        velocity = self.calculate_learning_velocity(quiz_results)
        
        if not quiz_results:
            return 50.0
        
        # Get most recent score
        sorted_results = sorted(quiz_results, key=lambda x: x.get('completedAt', datetime.now()))
        last_result = sorted_results[-1]
        
        total = last_result.get('totalQuestions', 1)
        correct = last_result.get('correctAnswers', 0)
        last_score = (correct / total * 100) if total > 0 else 0
        
        # Predict based on velocity (assume 7 days to next quiz)
        predicted = last_score + (velocity * 7)
        
        # Clamp to 0-100
        return round(max(0, min(100, predicted)), 2)


class PerformanceAnalyzer:
    """Analyze quiz performance patterns and identify areas for improvement"""
    
    def analyze_quiz_accuracy(self, quiz_results: List[Dict]) -> Dict[str, Any]:
        """
        Calculate overall accuracy, recent accuracy (last 5 quizzes), accuracy by difficulty.
        Returns dictionary with accuracy metrics.
        """
        if not quiz_results:
            return {
                "overall_accuracy": 0.0,
                "recent_accuracy": 0.0,
                "accuracy_by_difficulty": {},
                "total_quizzes": 0
            }
        
        # Calculate overall accuracy
        total_questions = sum(r.get('totalQuestions', 0) for r in quiz_results)
        total_correct = sum(r.get('correctAnswers', 0) for r in quiz_results)
        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        # Calculate recent accuracy (last 5)
        sorted_results = sorted(quiz_results, key=lambda x: x.get('completedAt', datetime.now()))
        recent_results = sorted_results[-5:]
        
        recent_questions = sum(r.get('totalQuestions', 0) for r in recent_results)
        recent_correct = sum(r.get('correctAnswers', 0) for r in recent_results)
        recent_accuracy = (recent_correct / recent_questions * 100) if recent_questions > 0 else 0
        
        # Accuracy by difficulty (if available)
        difficulty_stats = defaultdict(lambda: {"correct": 0, "total": 0})
        for result in quiz_results:
            difficulty = result.get('difficulty', 'medium')
            difficulty_stats[difficulty]["correct"] += result.get('correctAnswers', 0)
            difficulty_stats[difficulty]["total"] += result.get('totalQuestions', 0)
        
        accuracy_by_difficulty = {}
        for difficulty, stats in difficulty_stats.items():
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            accuracy_by_difficulty[difficulty] = round(accuracy, 2)
        
        return {
            "overall_accuracy": round(overall_accuracy, 2),
            "recent_accuracy": round(recent_accuracy, 2),
            "accuracy_by_difficulty": accuracy_by_difficulty,
            "total_quizzes": len(quiz_results)
        }
    
    def analyze_time_efficiency(self, quiz_results: List[Dict]) -> Dict[str, Any]:
        """
        Calculate average time per question, time efficiency score (accuracy/time ratio).
        Returns dictionary with time efficiency metrics.
        """
        if not quiz_results:
            return {
                "avg_time_per_question": 0.0,
                "time_efficiency_score": 0.0,
                "total_time_spent": 0
            }
        
        total_time = sum(r.get('timeSpentSeconds', 0) for r in quiz_results)
        total_questions = sum(r.get('totalQuestions', 0) for r in quiz_results)
        total_correct = sum(r.get('correctAnswers', 0) for r in quiz_results)
        
        avg_time_per_question = (total_time / total_questions) if total_questions > 0 else 0
        
        # Time efficiency: correct answers per minute
        time_in_minutes = total_time / 60 if total_time > 0 else 1
        time_efficiency = total_correct / time_in_minutes
        
        return {
            "avg_time_per_question": round(avg_time_per_question, 2),
            "time_efficiency_score": round(time_efficiency, 2),
            "total_time_spent": total_time
        }
    
    def detect_weak_topics(self, quiz_results: List[Dict]) -> List[str]:
        """
        Identify topics with consistently low scores (< 60%).
        Returns list of topic names.
        """
        if not quiz_results:
            return []
        
        # Group by topic
        topic_performance = defaultdict(lambda: {"correct": 0, "total": 0})
        for result in quiz_results:
            topic = result.get('topic', 'unknown')
            topic_performance[topic]["correct"] += result.get('correctAnswers', 0)
            topic_performance[topic]["total"] += result.get('totalQuestions', 0)
        
        # Identify weak topics
        weak_topics = []
        for topic, stats in topic_performance.items():
            if stats["total"] > 0:
                accuracy = (stats["correct"] / stats["total"]) * 100
                if accuracy < 60:
                    weak_topics.append(topic)
        
        return weak_topics
    
    def calculate_consistency_score(self, quiz_results: List[Dict]) -> float:
        """
        Measure performance consistency (inverse of standard deviation).
        Returns consistency score (0-100, higher is more consistent).
        """
        if len(quiz_results) < 2:
            return 100.0
        
        # Calculate scores
        scores = []
        for result in quiz_results:
            total = result.get('totalQuestions', 1)
            correct = result.get('correctAnswers', 0)
            score = (correct / total * 100) if total > 0 else 0
            scores.append(score)
        
        # Calculate standard deviation
        std_dev = statistics.stdev(scores)
        
        # Convert to consistency score (lower std_dev = higher consistency)
        # Map 0 std_dev to 100, 50 std_dev to 0
        consistency = max(0, 100 - (std_dev * 2))
        
        return round(consistency, 2)
