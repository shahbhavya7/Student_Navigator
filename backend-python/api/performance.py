"""
Performance API Endpoints

Provides REST API endpoints for accessing student performance metrics,
improvement curves, weak topics, and comprehensive performance profiles.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from models.schemas import (
    PerformanceMetricsResponse,
    ImprovementCurveResponse,
    StudentProfileResponse
)
from analytics.improvement_curves import ImprovementCurveCalculator, PerformanceAnalyzer
from analytics.performance_profile import PerformanceProfileGenerator
from config.redis_client import redis_client
from config.database import get_async_db
import json

router = APIRouter(prefix="/api/performance", tags=["performance"])

curve_calculator = ImprovementCurveCalculator()
performance_analyzer = PerformanceAnalyzer()
profile_generator = PerformanceProfileGenerator()


@router.get("/{student_id}/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(student_id: str):
    """
    Get comprehensive performance metrics for a student.
    
    Returns quiz accuracy, learning velocity, improvement trends, and weak topics.
    """
    try:
        # Try to get from Redis cache first
        redis_client = await get_redis_client()
        cache_key = f"performance:{student_id}"
        
        cached_data = await redis_client.hgetall(cache_key)
        
        if cached_data:
            # Parse cached data
            def parse_value(v):
                try:
                    return json.loads(v.decode() if isinstance(v, bytes) else v)
                except:
                    return v.decode() if isinstance(v, bytes) else v
            
            parsed_data = {
                k.decode() if isinstance(k, bytes) else k: parse_value(v)
                for k, v in cached_data.items()
            }
            
            # Ensure all required fields are present
            return PerformanceMetricsResponse(
                student_id=student_id,
                quiz_accuracy=float(parsed_data.get("quiz_accuracy", 0)),
                learning_velocity=float(parsed_data.get("learning_velocity", 0)),
                improvement_trend=parsed_data.get("improvement_trend", "insufficient_data"),
                task_completion_rate=float(parsed_data.get("task_completion_rate", 0)),
                weak_topics=parsed_data.get("weak_topics", []),
                performance_insights=parsed_data.get("performance_insights", ""),
                timestamp=int(parsed_data.get("timestamp", datetime.now().timestamp()))
            )
        
        # If not cached, calculate from database
        quiz_results = await _fetch_quiz_results(student_id, days=30)
        
        if not quiz_results:
            raise HTTPException(status_code=404, detail="No performance data found for student")
        
        learning_velocity = curve_calculator.calculate_learning_velocity(quiz_results)
        improvement_trend = curve_calculator.calculate_improvement_trend(quiz_results)
        accuracy_metrics = performance_analyzer.analyze_quiz_accuracy(quiz_results)
        weak_topics = performance_analyzer.detect_weak_topics(quiz_results)
        
        # Get task completion rate
        task_completion_rate = await _get_task_completion_rate(student_id)
        
        return PerformanceMetricsResponse(
            student_id=student_id,
            quiz_accuracy=accuracy_metrics["overall_accuracy"],
            learning_velocity=learning_velocity,
            improvement_trend=improvement_trend,
            task_completion_rate=task_completion_rate,
            weak_topics=weak_topics,
            performance_insights="Performance metrics calculated from recent quiz data.",
            timestamp=int(datetime.now().timestamp())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching performance metrics: {str(e)}")


@router.get("/{student_id}/improvement-curve", response_model=ImprovementCurveResponse)
async def get_improvement_curve(student_id: str):
    """
    Get improvement curve data for visualization.
    
    Returns data points, trend line, velocity, and plateau detection.
    """
    try:
        quiz_results = await _fetch_quiz_results(student_id, days=90)
        
        if not quiz_results:
            raise HTTPException(status_code=404, detail="No quiz data found for student")
        
        # Sort by date
        sorted_results = sorted(quiz_results, key=lambda x: x.get('completedAt', datetime.now()))
        
        # Extract data points
        data_points = []
        for result in sorted_results:
            total = result.get('totalQuestions', 1)
            correct = result.get('correctAnswers', 0)
            score = (correct / total * 100) if total > 0 else 0
            
            data_points.append({
                'date': result.get('completedAt', datetime.now()).isoformat(),
                'score': score,
                'topic': result.get('topic', 'General')
            })
        
        # Calculate velocity and trend line
        velocity = curve_calculator.calculate_learning_velocity(quiz_results)
        
        # Simple linear trend line
        n = len(data_points)
        if n > 1:
            scores = [dp['score'] for dp in data_points]
            avg_score = sum(scores) / n
            trend_line = [avg_score + velocity * i for i in range(n)]
        else:
            trend_line = []
        
        # Detect plateau
        plateau_detected = curve_calculator.detect_learning_plateau(quiz_results)
        
        # Calculate confidence based on data points
        confidence = min(n / 10, 1.0)  # Max confidence at 10+ data points
        
        return ImprovementCurveResponse(
            student_id=student_id,
            data_points=data_points,
            trend_line=trend_line,
            velocity=velocity,
            plateau_detected=plateau_detected,
            confidence=confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating improvement curve: {str(e)}")


@router.get("/{student_id}/weak-topics")
async def get_weak_topics(student_id: str):
    """
    Get topics where student is struggling with recommendations.
    
    Returns list of weak topics with accuracy scores and recommendations.
    """
    try:
        quiz_results = await _fetch_quiz_results(student_id, days=30)
        
        if not quiz_results:
            raise HTTPException(status_code=404, detail="No quiz data found for student")
        
        weak_topics = performance_analyzer.detect_weak_topics(quiz_results)
        
        # Calculate detailed stats for each weak topic
        topic_details = []
        for topic in weak_topics:
            topic_results = [r for r in quiz_results if r.get('topic') == topic]
            
            total_qs = sum(r.get('totalQuestions', 0) for r in topic_results)
            correct = sum(r.get('correctAnswers', 0) for r in topic_results)
            accuracy = (correct / total_qs * 100) if total_qs > 0 else 0
            
            mastery = curve_calculator.calculate_mastery_level(quiz_results, topic)
            
            topic_details.append({
                'topic': topic,
                'accuracy': round(accuracy, 2),
                'mastery_level': mastery,
                'attempts': len(topic_results),
                'recommendation': _get_topic_recommendation(accuracy, mastery)
            })
        
        return {
            'student_id': student_id,
            'weak_topics': topic_details,
            'total_weak_topics': len(weak_topics),
            'timestamp': int(datetime.now().timestamp())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error identifying weak topics: {str(e)}")


@router.get("/{student_id}/profile", response_model=StudentProfileResponse)
async def get_student_profile(student_id: str):
    """
    Get comprehensive student performance profile.
    
    Returns combined cognitive load, performance, and engagement summaries
    with health score and risk assessment.
    """
    try:
        # Try to get from Redis cache
        profile = await profile_generator.get_profile(student_id)
        
        if profile:
            return StudentProfileResponse(
                student_id=profile.student_id,
                cognitive_load_summary=profile.cognitive_load_summary,
                performance_summary=profile.performance_summary,
                engagement_summary=profile.engagement_summary,
                combined_health_score=profile.combined_health_score,
                risk_level=profile.risk_level,
                recommended_actions=profile.recommended_actions,
                generated_at=profile.generated_at
            )
        
        raise HTTPException(status_code=404, detail="No profile found for student. Profile will be generated on next session.")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {str(e)}")


# Helper functions

async def _fetch_quiz_results(student_id: str, days: int = 30) -> List[Dict]:
    """Fetch quiz results from database"""
    results = []
    cutoff_date = datetime.now() - timedelta(days=days)
    
    try:
        async for db in get_async_db():
            query = """
                SELECT 
                    qr.id,
                    qr."studentId",
                    qr."moduleId",
                    qr.score,
                    qr."totalQuestions",
                    qr."correctAnswers",
                    qr."timeSpentSeconds",
                    qr."completedAt",
                    cm.title as topic,
                    cm.difficulty
                FROM quiz_results qr
                LEFT JOIN content_modules cm ON qr."moduleId" = cm.id
                WHERE qr."studentId" = :student_id
                AND qr."completedAt" >= :cutoff_date
                ORDER BY qr."completedAt" DESC
            """
            
            result = await db.execute(
                query,
                {"student_id": student_id, "cutoff_date": cutoff_date}
            )
            rows = result.fetchall()
            
            for row in rows:
                results.append({
                    "id": row[0],
                    "studentId": row[1],
                    "moduleId": row[2],
                    "score": row[3],
                    "totalQuestions": row[4],
                    "correctAnswers": row[5],
                    "timeSpentSeconds": row[6],
                    "completedAt": row[7],
                    "topic": row[8] or "General",
                    "difficulty": row[9] or "medium"
                })
            
            break
            
    except Exception as e:
        print(f"Error fetching quiz results: {str(e)}")
    
    return results


async def _get_task_completion_rate(student_id: str) -> float:
    """Get task completion rate from learning paths"""
    try:
        async for db in get_async_db():
            query = """
                SELECT AVG(progress) as avg_progress
                FROM learning_paths
                WHERE "studentId" = :student_id
                AND status = 'active'
            """
            
            result = await db.execute(query, {"student_id": student_id})
            row = result.fetchone()
            
            if row and row[0] is not None:
                return round(float(row[0]), 2)
            
            break
            
    except Exception as e:
        print(f"Error fetching task completion rate: {str(e)}")
    
    return 0.0


def _get_topic_recommendation(accuracy: float, mastery: float) -> str:
    """Generate recommendation for weak topic"""
    if accuracy < 40:
        return "Review fundamental concepts and complete additional practice exercises"
    elif accuracy < 60:
        return "Focus on understanding core principles with guided examples"
    else:
        return "Practice with varied problem types to improve consistency"
