"""
Engagement API Endpoints

Provides REST API endpoints for accessing student engagement metrics,
dropout risk assessment, and session activity patterns.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime, timedelta

from models.schemas import EngagementMetricsResponse
from config.redis_client import redis_client
from config.database import get_async_db
import json

router = APIRouter(prefix="/api/engagement", tags=["engagement"])


@router.get("/{student_id}/metrics", response_model=EngagementMetricsResponse)
async def get_engagement_metrics(student_id: str):
    """
    Get comprehensive engagement metrics for a student.
    
    Returns engagement score, session patterns, interaction depth, and dropout risk.
    """
    try:
        # Try to get from Redis cache first
        redis_client = await get_redis_client()
        cache_key = f"engagement:{student_id}"
        
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
            
            return EngagementMetricsResponse(
                student_id=student_id,
                engagement_score=float(parsed_data.get("engagement_score", 0)),
                session_duration_avg=int(parsed_data.get("session_duration_avg", 0)),
                interaction_depth=float(parsed_data.get("interaction_depth", 0)),
                dropout_risk=float(parsed_data.get("dropout_risk", 0)),
                return_frequency=parsed_data.get("return_frequency", {}),
                engagement_insights=parsed_data.get("engagement_insights", ""),
                dropout_signals=parsed_data.get("dropout_signals", []),
                timestamp=int(parsed_data.get("timestamp", datetime.now().timestamp()))
            )
        
        # If not cached, calculate from database
        sessions = await _fetch_recent_sessions(student_id, days=14)
        
        if not sessions:
            raise HTTPException(status_code=404, detail="No engagement data found for student")
        
        # Calculate metrics
        session_metrics = _calculate_session_metrics(sessions)
        return_frequency = _calculate_return_frequency(sessions)
        dropout_signals = _detect_dropout_signals(sessions, session_metrics)
        
        # Calculate engagement score
        engagement_score = _calculate_engagement_score(
            session_metrics,
            0.0,  # interaction_depth placeholder
            return_frequency
        )
        
        # Calculate dropout risk
        dropout_risk = _calculate_dropout_risk(engagement_score, dropout_signals, sessions)
        
        return EngagementMetricsResponse(
            student_id=student_id,
            engagement_score=engagement_score,
            session_duration_avg=session_metrics["avg_session_duration"],
            interaction_depth=0.0,  # Placeholder
            dropout_risk=dropout_risk,
            return_frequency=return_frequency,
            engagement_insights="Engagement metrics calculated from recent session data.",
            dropout_signals=dropout_signals,
            timestamp=int(datetime.now().timestamp())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching engagement metrics: {str(e)}")


@router.get("/{student_id}/dropout-risk")
async def get_dropout_risk(student_id: str):
    """
    Get dropout risk assessment with contributing factors.
    
    Returns dropout risk score, early warning signals, and recommended interventions.
    """
    try:
        sessions = await _fetch_recent_sessions(student_id, days=14)
        
        if not sessions:
            raise HTTPException(status_code=404, detail="No session data found for student")
        
        session_metrics = _calculate_session_metrics(sessions)
        return_frequency = _calculate_return_frequency(sessions)
        dropout_signals = _detect_dropout_signals(sessions, session_metrics)
        
        engagement_score = _calculate_engagement_score(
            session_metrics, 0.0, return_frequency
        )
        dropout_risk = _calculate_dropout_risk(engagement_score, dropout_signals, sessions)
        
        # Determine risk level
        if dropout_risk > 0.7:
            risk_level = "critical"
            intervention = "Immediate outreach required - student at high risk of dropping out"
        elif dropout_risk > 0.5:
            risk_level = "high"
            intervention = "Schedule check-in within 48 hours - engagement declining"
        elif dropout_risk > 0.3:
            risk_level = "medium"
            intervention = "Monitor closely - some warning signs present"
        else:
            risk_level = "low"
            intervention = "Continue normal engagement strategies"
        
        # Contributing factors
        factors = []
        if engagement_score < 50:
            factors.append({"factor": "Low overall engagement", "impact": "high"})
        if session_metrics["session_frequency"] < 2:
            factors.append({"factor": "Infrequent sessions", "impact": "medium"})
        if return_frequency["last_7_days"] < 3:
            factors.append({"factor": "Low return frequency", "impact": "high"})
        if len(dropout_signals) > 2:
            factors.append({"factor": "Multiple warning signals", "impact": "high"})
        
        return {
            "student_id": student_id,
            "dropout_risk": dropout_risk,
            "risk_level": risk_level,
            "early_warning_signals": dropout_signals,
            "contributing_factors": factors,
            "recommended_intervention": intervention,
            "timestamp": int(datetime.now().timestamp())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assessing dropout risk: {str(e)}")


@router.get("/{student_id}/session-history")
async def get_session_history(student_id: str, days: int = 30):
    """
    Get session history with duration, frequency, and patterns.
    
    Returns visualizable time-series data for session activity.
    """
    try:
        sessions = await _fetch_recent_sessions(student_id, days=days)
        
        if not sessions:
            raise HTTPException(status_code=404, detail="No session data found for student")
        
        # Format for visualization
        session_data = []
        for session in sessions:
            session_data.append({
                "session_id": session["id"],
                "start_time": session["startTime"].isoformat(),
                "end_time": session["endTime"].isoformat() if session["endTime"] else None,
                "duration_seconds": session["durationSeconds"],
                "duration_minutes": round(session["durationSeconds"] / 60, 1)
            })
        
        # Calculate weekly patterns
        weekly_pattern = _calculate_weekly_pattern(sessions)
        
        # Calculate time-of-day distribution
        time_distribution = _calculate_time_distribution(sessions)
        
        session_metrics = _calculate_session_metrics(sessions)
        
        return {
            "student_id": student_id,
            "total_sessions": len(sessions),
            "date_range_days": days,
            "sessions": session_data,
            "metrics": {
                "avg_duration_seconds": session_metrics["avg_session_duration"],
                "avg_duration_minutes": round(session_metrics["avg_session_duration"] / 60, 1),
                "total_study_time_seconds": session_metrics["total_study_time"],
                "total_study_time_hours": round(session_metrics["total_study_time"] / 3600, 1),
                "sessions_per_week": session_metrics["session_frequency"]
            },
            "weekly_pattern": weekly_pattern,
            "time_of_day_distribution": time_distribution,
            "timestamp": int(datetime.now().timestamp())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching session history: {str(e)}")


# Helper functions

async def _fetch_recent_sessions(student_id: str, days: int = 14) -> List[Dict]:
    """Fetch recent sessions from database"""
    sessions = []
    cutoff_date = datetime.now() - timedelta(days=days)
    
    try:
        async for db in get_async_db():
            query = """
                SELECT 
                    id,
                    "studentId",
                    "startTime",
                    "endTime",
                    "durationSeconds"
                FROM sessions
                WHERE "studentId" = :student_id
                AND "startTime" >= :cutoff_date
                ORDER BY "startTime" DESC
            """
            
            result = await db.execute(
                query,
                {"student_id": student_id, "cutoff_date": cutoff_date}
            )
            rows = result.fetchall()
            
            for row in rows:
                sessions.append({
                    "id": row[0],
                    "studentId": row[1],
                    "startTime": row[2],
                    "endTime": row[3],
                    "durationSeconds": row[4]
                })
            
            break
            
    except Exception as e:
        print(f"Error fetching sessions: {str(e)}")
    
    return sessions


def _calculate_session_metrics(sessions: List[Dict]) -> Dict[str, Any]:
    """Calculate session duration and frequency metrics"""
    if not sessions:
        return {
            "avg_session_duration": 0,
            "total_study_time": 0,
            "session_frequency": 0.0
        }
    
    durations = [s["durationSeconds"] for s in sessions if s["durationSeconds"]]
    avg_duration = sum(durations) / len(durations) if durations else 0
    total_time = sum(durations)
    
    # Calculate session frequency (sessions per week)
    if len(sessions) > 0:
        first_session = min(s["startTime"] for s in sessions)
        last_session = max(s["startTime"] for s in sessions)
        days_span = max((last_session - first_session).days, 1)
        weeks_span = days_span / 7
        frequency = len(sessions) / weeks_span if weeks_span > 0 else len(sessions)
    else:
        frequency = 0.0
    
    return {
        "avg_session_duration": round(avg_duration, 2),
        "total_study_time": total_time,
        "session_frequency": round(frequency, 2)
    }


def _calculate_return_frequency(sessions: List[Dict]) -> Dict[str, int]:
    """Calculate return frequency for different time periods"""
    now = datetime.now()
    
    days_7 = set()
    days_14 = set()
    days_30 = set()
    
    for session in sessions:
        start_time = session["startTime"]
        days_ago = (now - start_time).days
        day_key = start_time.date()
        
        if days_ago <= 7:
            days_7.add(day_key)
        if days_ago <= 14:
            days_14.add(day_key)
        if days_ago <= 30:
            days_30.add(day_key)
    
    return {
        "last_7_days": len(days_7),
        "last_14_days": len(days_14),
        "last_30_days": len(days_30)
    }


def _detect_dropout_signals(sessions: List[Dict], session_metrics: Dict) -> List[str]:
    """Detect dropout warning signals"""
    signals = []
    
    if not sessions:
        return ["No recent session activity"]
    
    sorted_sessions = sorted(sessions, key=lambda x: x["startTime"])
    
    # Check for declining session frequency
    if len(sorted_sessions) >= 4:
        mid_point = len(sorted_sessions) // 2
        recent_count = len(sorted_sessions[mid_point:])
        older_count = len(sorted_sessions[:mid_point])
        
        if recent_count < older_count * 0.7:
            signals.append("Declining session frequency detected")
    
    # Check for long gaps
    now = datetime.now()
    last_session = max(s["startTime"] for s in sessions)
    days_since_last = (now - last_session).days
    
    if days_since_last > 3:
        signals.append(f"No activity for {days_since_last} days")
    
    # Check for low session frequency
    if session_metrics["session_frequency"] < 2:
        signals.append("Low session frequency (< 2 per week)")
    
    return signals


def _calculate_engagement_score(
    session_metrics: Dict,
    interaction_depth: float,
    return_frequency: Dict
) -> float:
    """Calculate overall engagement score (0-100)"""
    freq_score = min(session_metrics["session_frequency"] / 4 * 100, 100)
    duration_score = min(session_metrics["avg_session_duration"] / 1800 * 100, 100)
    interaction_score = interaction_depth
    return_score = min(return_frequency["last_7_days"] / 5 * 100, 100)
    
    engagement = (
        freq_score * 0.30 +
        duration_score * 0.25 +
        interaction_score * 0.25 +
        return_score * 0.20
    )
    
    return round(engagement, 2)


def _calculate_dropout_risk(
    engagement_score: float,
    dropout_signals: List[str],
    sessions: List[Dict]
) -> float:
    """Calculate dropout risk (0-1)"""
    risk = 0.0
    
    if engagement_score < 40:
        risk += 0.4
    elif engagement_score < 60:
        risk += 0.2
    
    signal_risk = min(len(dropout_signals) * 0.15, 0.5)
    risk += signal_risk
    
    if sessions:
        now = datetime.now()
        last_session = max(s["startTime"] for s in sessions)
        days_since = (now - last_session).days
        
        if days_since > 5:
            risk += 0.3
        elif days_since > 3:
            risk += 0.1
    
    return round(min(risk, 1.0), 2)


def _calculate_weekly_pattern(sessions: List[Dict]) -> Dict[str, int]:
    """Calculate sessions per day of week"""
    from collections import defaultdict
    
    day_counts = defaultdict(int)
    for session in sessions:
        day_name = session["startTime"].strftime("%A")
        day_counts[day_name] += 1
    
    return dict(day_counts)


def _calculate_time_distribution(sessions: List[Dict]) -> Dict[str, int]:
    """Calculate time-of-day distribution"""
    from collections import defaultdict
    
    time_buckets = defaultdict(int)
    for session in sessions:
        hour = session["startTime"].hour
        
        if 6 <= hour < 12:
            time_buckets["Morning (6AM-12PM)"] += 1
        elif 12 <= hour < 18:
            time_buckets["Afternoon (12PM-6PM)"] += 1
        elif 18 <= hour < 24:
            time_buckets["Evening (6PM-12AM)"] += 1
        else:
            time_buckets["Night (12AM-6AM)"] += 1
    
    return dict(time_buckets)
