"""
CLR Dashboard API Endpoints

Comprehensive REST API for Cognitive Load Radar data access and visualization.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from models.schemas import (
    CLRCurrentResponse,
    CLRHistoryResponse,
    CLRInsightsResponse,
    CLRPatternsResponse,
    CLRBaselineResponse,
    CLRPredictionResponse,
    CLRDashboardResponse,
    TextAnalysisRequest,
    TextAnalysisResponse
)
from services.clr_storage import clr_storage_service
from config.redis_client import redis_client
from agents.clr_agent import CognitiveLoadRadarAgent
from ml.sentiment_analyzer import MoodAnalyzer
from ml.text_processor import TextProcessor
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings


router = APIRouter(prefix="/api/clr", tags=["CLR"])

# Initialize components
clr_agent = CognitiveLoadRadarAgent()
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=settings.GOOGLE_API_KEY
)
mood_analyzer = MoodAnalyzer(llm)


@router.get("/current/{student_id}", response_model=CLRCurrentResponse)
async def get_current_clr(student_id: str):
    """
    Get real-time cognitive load for active session.
    
    Args:
        student_id: Student identifier
        
    Returns:
        Current cognitive load data
    """
    try:
        # Get latest entry from Redis
        redis_key = f"clr:{student_id}"
        results = await redis_client.data_client.zrevrange(redis_key, 0, 0, withscores=True)
        
        if not results:
            raise HTTPException(status_code=404, detail="No cognitive load data found")
        
        import json
        value, timestamp = results[0]
        data = json.loads(value)
        
        return CLRCurrentResponse(
            student_id=student_id,
            cognitive_load_score=data.get('score', 0),
            mental_fatigue_level=data.get('fatigue_level', 'low'),
            detected_patterns=data.get('patterns', []),
            mood_indicators=data.get('mood', {}),
            timestamp=int(timestamp),
            session_id=data.get('session_id', '')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving current CLR: {str(e)}")


@router.get("/history/{student_id}", response_model=CLRHistoryResponse)
async def get_clr_history(
    student_id: str,
    time_range: str = Query("hour", regex="^(hour|day|week|month)$"),
    granularity: str = Query("raw", regex="^(raw|hourly|daily)$")
):
    """
    Get cognitive load history for student.
    
    Args:
        student_id: Student identifier
        time_range: Time range (hour/day/week/month)
        granularity: Data granularity (raw/hourly/daily)
        
    Returns:
        Time-series cognitive load data
    """
    try:
        time_range_key = f"last_{time_range}"
        history_data = await clr_storage_service.get_cognitive_load_history(student_id, time_range_key)
        
        # Calculate trend
        trend_data = await clr_storage_service.get_cognitive_load_trend(student_id, window_minutes=30)
        
        return CLRHistoryResponse(
            student_id=student_id,
            time_range=time_range,
            granularity=granularity,
            history=history_data.get('history', []),
            statistics=history_data.get('statistics', {}),
            trend=trend_data.get('trend', 'stable'),
            trend_slope=trend_data.get('slope', 0.0),
            data_points=len(history_data.get('history', []))
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")


@router.get("/session/{session_id}")
async def get_session_clr(session_id: str):
    """
    Get cognitive load data for specific learning session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session cognitive load timeline and analysis
    """
    try:
        session_data = clr_storage_service.get_session_cognitive_load(session_id)
        return session_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving session data: {str(e)}")


@router.get("/insights/{student_id}", response_model=CLRInsightsResponse)
async def get_clr_insights(student_id: str):
    """
    Generate personalized insights using LLM.
    
    Args:
        student_id: Student identifier
        
    Returns:
        AI-generated analysis and recommendations
    """
    try:
        # Check cache first
        cache_key = f"clr_insights:{student_id}"
        cached = await redis_client.cache_client.get(cache_key)
        
        if cached:
            import json
            return CLRInsightsResponse(**json.loads(cached))
        
        # Get current CLR data
        current_data = await get_current_clr(student_id)
        
        # Prepare CLR data for insights generation
        clr_data = {
            'cognitive_load_score': current_data.cognitive_load_score,
            'mental_fatigue_level': current_data.mental_fatigue_level,
            'detected_patterns': current_data.detected_patterns,
            'mood_indicators': current_data.mood_indicators,
            'timestamp': current_data.timestamp
        }
        
        # Generate insights
        insights_text = clr_agent.generate_personalized_insights(clr_data)
        
        # Parse recommendations (simple split by newline)
        recommendations = [line.strip() for line in insights_text.split('\n') if line.strip()]
        
        response = CLRInsightsResponse(
            student_id=student_id,
            insights=insights_text,
            recommendations=recommendations[:5],  # Top 5
            generated_at=int(datetime.now().timestamp() * 1000)
        )
        
        # Cache for 5 minutes
        import json
        await redis_client.cache_client.setex(cache_key, 300, json.dumps(response.dict()))
        
        return response
        
    except HTTPException as he:
        # If no current data, return generic insights
        return CLRInsightsResponse(
            student_id=student_id,
            insights="No cognitive load data available yet. Start learning to generate insights.",
            recommendations=["Begin your learning session to track cognitive load"],
            generated_at=int(datetime.now().timestamp() * 1000)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating insights: {str(e)}")


@router.get("/patterns/{student_id}", response_model=CLRPatternsResponse)
async def get_clr_patterns(
    student_id: str,
    days: int = Query(7, ge=1, le=30)
):
    """
    Analyze detected patterns over time.
    
    Args:
        student_id: Student identifier
        days: Number of days to analyze
        
    Returns:
        Pattern frequency and analysis
    """
    try:
        history_data = await clr_storage_service.get_cognitive_load_history(student_id, f'last_month')
        history = history_data.get('history', [])
        
        # Count pattern frequencies
        pattern_counts = {}
        for entry in history:
            for pattern in entry.get('patterns', []):
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        # Sort by frequency
        sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
        
        return CLRPatternsResponse(
            student_id=student_id,
            days_analyzed=days,
            patterns=dict(sorted_patterns),
            most_common_pattern=sorted_patterns[0][0] if sorted_patterns else None,
            total_pattern_detections=sum(pattern_counts.values())
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing patterns: {str(e)}")


@router.get("/baseline/{student_id}", response_model=CLRBaselineResponse)
async def get_clr_baseline(student_id: str):
    """
    Get student's baseline cognitive load metrics.
    
    Args:
        student_id: Student identifier
        
    Returns:
        Baseline metrics and comparison data
    """
    try:
        baseline = await clr_storage_service.calculate_baseline_metrics(student_id, days=7)
        
        # Get current load for comparison
        try:
            current = await get_current_clr(student_id)
            current_score = current.cognitive_load_score
        except:
            current_score = None
        
        return CLRBaselineResponse(
            student_id=student_id,
            baseline_avg=baseline.get('avg_cognitive_load', 0),
            baseline_std=baseline.get('std_cognitive_load', 0),
            baseline_range={
                'min': baseline.get('min_load', 0),
                'max': baseline.get('max_load', 0)
            },
            current_score=current_score,
            deviation_from_baseline=current_score - baseline.get('avg_cognitive_load', 0) if current_score else None,
            common_patterns=baseline.get('common_patterns', []),
            data_points=baseline.get('data_points', 0),
            calculated_at=baseline.get('calculated_at', '')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving baseline: {str(e)}")


@router.post("/analyze-text", response_model=TextAnalysisResponse)
async def analyze_text_mood(request: TextAnalysisRequest):
    """
    Perform mood analysis on provided text.
    
    Args:
        request: Text analysis request with student_id, text, and context
        
    Returns:
        Mood analysis results
    """
    try:
        # Preprocess text
        cleaned_text = TextProcessor.preprocess_for_sentiment(request.text)
        
        if not cleaned_text:
            return TextAnalysisResponse(
                student_id=request.student_id,
                mood_score=0.0,
                dominant_emotion='neutral',
                confidence=0.0,
                explanation='Text not suitable for sentiment analysis'
            )
        
        # Analyze mood
        mood_result = mood_analyzer.analyze_text(cleaned_text, request.context)
        
        return TextAnalysisResponse(
            student_id=request.student_id,
            mood_score=mood_result.get('mood_score', 0.0),
            dominant_emotion=mood_result.get('dominant_emotion', 'neutral'),
            confidence=mood_result.get('confidence', 0.0),
            explanation=mood_result.get('explanation', '')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text: {str(e)}")


@router.get("/predictions/{student_id}", response_model=CLRPredictionResponse)
async def get_clr_predictions(student_id: str):
    """
    Get cognitive load predictions for next 15-30 minutes.
    
    Args:
        student_id: Student identifier
        
    Returns:
        Predicted trajectory and recommendations
    """
    try:
        predictions = await clr_agent.predict_cognitive_load_trajectory(student_id)
        
        return CLRPredictionResponse(
            student_id=student_id,
            predicted_load_15min=predictions.get('predicted_load_15min', 0.0),
            predicted_load_30min=predictions.get('predicted_load_30min', 0.0),
            trend=predictions.get('trend', 'stable'),
            confidence=predictions.get('confidence', 0.0),
            early_intervention_needed=predictions.get('early_intervention_needed', False),
            recommendations=predictions.get('recommendations', [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(e)}")


@router.get("/dashboard/{student_id}", response_model=CLRDashboardResponse)
async def get_clr_dashboard(student_id: str):
    """
    Comprehensive dashboard data combining all CLR metrics.
    Optimized single endpoint for dashboard UI.
    
    Args:
        student_id: Student identifier
        
    Returns:
        Complete dashboard data
    """
    try:
        # Fetch all data in parallel where possible
        current = await get_current_clr(student_id)
        history = await get_clr_history(student_id, time_range='day', granularity='raw')
        insights = await get_clr_insights(student_id)
        patterns = await get_clr_patterns(student_id, days=7)
        baseline = await get_clr_baseline(student_id)
        predictions = await get_clr_predictions(student_id)
        
        return CLRDashboardResponse(
            student_id=student_id,
            current=current,
            history=history,
            insights=insights,
            patterns=patterns,
            baseline=baseline,
            predictions=predictions,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading dashboard: {str(e)}")
