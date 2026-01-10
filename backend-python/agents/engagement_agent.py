"""
Engagement Agent Implementation

Analyzes student engagement patterns, session duration, interaction depth,
and detects dropout risk signals for early intervention.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from agents.base_agent import BaseAgent
from agents.state import AgentState
from config.database import get_async_db
from config.redis_client import redis_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import json


class EngagementAgent(BaseAgent):
    """Agent for analyzing student engagement and detecting dropout risk"""
    
    def __init__(self, name: str = "engagement_agent"):
        super().__init__(name)
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.7)
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze student engagement patterns and calculate dropout risk.
        
        Args:
            state: Current agent state with student_id and behavioral data
            
        Returns:
            Dictionary with engagement metrics and insights
        """
        self.logger.info(f"[{self.name}] Analyzing engagement for student {state.get('student_id')}")
        
        student_id = state.get("student_id")
        session_id = state.get("session_id")
        aggregated_metrics = state.get("aggregated_metrics", {})
        
        if not student_id:
            self.logger.warning(f"[{self.name}] No student_id provided")
            return self._get_default_metrics()
        
        try:
            # Fetch recent sessions
            sessions = await self._fetch_recent_sessions(student_id, days=14)
            
            if not sessions:
                self.logger.info(f"[{self.name}] No session data found for student {student_id}")
                return self._get_default_metrics()
            
            # Calculate session duration metrics
            session_metrics = self._calculate_session_metrics(sessions)
            
            # Calculate content interaction depth from behavioral events
            behavioral_events = state.get("behavioral_events", [])
            interaction_depth = self._calculate_interaction_depth(behavioral_events)
            
            # Calculate return frequency
            return_frequency = self._calculate_return_frequency(sessions)
            
            # Detect dropout signals
            dropout_signals = self._detect_dropout_signals(sessions, session_metrics)
            
            # Calculate engagement score (0-100)
            engagement_score = self._calculate_engagement_score(
                session_metrics,
                interaction_depth,
                return_frequency
            )
            
            # Calculate dropout risk (0-1)
            dropout_risk = self._calculate_dropout_risk(
                engagement_score,
                dropout_signals,
                sessions
            )
            
            # Generate LLM-powered engagement insights
            engagement_insights = await self._generate_engagement_insights({
                "engagement_score": engagement_score,
                "session_frequency": session_metrics["session_frequency"],
                "avg_session_duration": session_metrics["avg_session_duration"],
                "interaction_depth": interaction_depth,
                "dropout_risk": dropout_risk,
                "dropout_signals": dropout_signals,
                "return_frequency": return_frequency
            })
            
            # Prepare complete engagement data for storage and API compatibility
            complete_engagement_data = {
                "student_id": student_id,
                "engagement_score": engagement_score,
                "session_duration_avg": session_metrics["avg_session_duration"],
                "total_study_time": session_metrics["total_study_time"],
                "session_frequency": session_metrics["session_frequency"],
                "interaction_depth": interaction_depth,
                "dropout_risk": dropout_risk,
                "return_frequency": return_frequency,
                "engagement_insights": engagement_insights,
                "dropout_signals": dropout_signals,
                "timestamp": int(datetime.now().timestamp())
            }
            
            # Store in Redis
            await self._store_engagement_metrics(student_id, complete_engagement_data)
            
            # Prepare engagement data for backward compatibility
            engagement_data = {
                "student_id": student_id,
                "engagement_score": engagement_score,
                "dropout_risk": dropout_risk,
                "timestamp": int(datetime.now().timestamp())
            }
            
            # Publish event
            await self.publish_event("engagement_analyzed", {
                "student_id": student_id,
                "session_id": session_id,
                "engagement_score": engagement_score,
                "dropout_risk": dropout_risk,
                "dropout_signals": dropout_signals
            })
            
            self.logger.info(f"[{self.name}] Engagement analysis complete for student {student_id}")
            
            return {
                "engagement_score": engagement_score,
                "session_duration": session_metrics["avg_session_duration"],
                "total_study_time": session_metrics["total_study_time"],
                "session_frequency": session_metrics["session_frequency"],
                "interaction_depth": interaction_depth,
                "dropout_risk": dropout_risk,
                "return_frequency": return_frequency,
                "engagement_insights": engagement_insights,
                "dropout_signals": dropout_signals
            }
            
        except Exception as e:
            self.logger.error(f"[{self.name}] Error analyzing engagement: {str(e)}")
            return self._get_default_metrics()
    
    async def _fetch_recent_sessions(self, student_id: str, days: int = 14) -> List[Dict]:
        """
        Fetch recent sessions from database.
        
        Args:
            student_id: Student identifier
            days: Number of days to look back
            
        Returns:
            List of session dictionaries
        """
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
            self.logger.error(f"[{self.name}] Error fetching sessions: {str(e)}")
        
        return sessions
    
    def _calculate_session_metrics(self, sessions: List[Dict]) -> Dict[str, Any]:
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
    
    def _calculate_interaction_depth(self, behavioral_events: List[Dict]) -> float:
        """
        Calculate content interaction depth from behavioral events.
        
        Args:
            behavioral_events: List of behavioral event dictionaries
            
        Returns:
            Interaction depth score (0-100)
        """
        if not behavioral_events:
            return 0.0
        
        # Count meaningful interactions
        meaningful_types = ["CONTENT_INTERACTION", "SCROLL_BEHAVIOR", "TIME_TRACKING"]
        meaningful_events = [e for e in behavioral_events if e.get("type") in meaningful_types]
        
        if not behavioral_events:
            return 0.0
        
        # Calculate ratio of active events
        interaction_ratio = len(meaningful_events) / len(behavioral_events)
        
        # Weight by event duration (if available)
        total_duration = sum(e.get("duration", 0) for e in meaningful_events)
        avg_duration = total_duration / len(meaningful_events) if meaningful_events else 0
        
        # Normalize duration score (30 seconds = good interaction)
        duration_score = min(avg_duration / 30, 1.0) if avg_duration > 0 else 0
        
        # Combined depth score
        depth_score = (interaction_ratio * 0.6 + duration_score * 0.4) * 100
        
        return round(depth_score, 2)
    
    def _calculate_return_frequency(self, sessions: List[Dict]) -> Dict[str, int]:
        """
        Calculate return frequency for different time periods.
        
        Args:
            sessions: List of session dictionaries
            
        Returns:
            Dictionary with days active in last 7/14/30 days
        """
        now = datetime.now()
        
        # Get unique days active
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
    
    def _detect_dropout_signals(self, sessions: List[Dict], session_metrics: Dict) -> List[str]:
        """
        Detect dropout warning signals.
        
        Args:
            sessions: List of session dictionaries
            session_metrics: Calculated session metrics
            
        Returns:
            List of detected signal descriptions
        """
        signals = []
        
        if not sessions:
            return ["No recent session activity"]
        
        # Sort sessions by date
        sorted_sessions = sorted(sessions, key=lambda x: x["startTime"])
        
        # Check for declining session frequency
        if len(sorted_sessions) >= 4:
            mid_point = len(sorted_sessions) // 2
            recent_sessions = sorted_sessions[mid_point:]
            older_sessions = sorted_sessions[:mid_point]
            
            recent_count = len(recent_sessions)
            older_count = len(older_sessions)
            
            if recent_count < older_count * 0.7:
                signals.append("Declining session frequency detected")
        
        # Check for decreasing session duration
        if len(sorted_sessions) >= 3:
            recent_durations = [s["durationSeconds"] for s in sorted_sessions[-3:]]
            avg_recent = sum(recent_durations) / len(recent_durations)
            
            if session_metrics["avg_session_duration"] > 0:
                if avg_recent < session_metrics["avg_session_duration"] * 0.7:
                    signals.append("Session duration declining")
        
        # Check for long gaps between sessions
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
        self,
        session_metrics: Dict,
        interaction_depth: float,
        return_frequency: Dict
    ) -> float:
        """
        Calculate overall engagement score (0-100) using weighted formula.
        
        Weights:
        - Session frequency: 30%
        - Average session duration: 25%
        - Content interaction depth: 25%
        - Return frequency: 20%
        """
        # Normalize session frequency (4+ sessions/week = 100)
        freq_score = min(session_metrics["session_frequency"] / 4 * 100, 100)
        
        # Normalize session duration (30+ minutes = 100)
        duration_score = min(session_metrics["avg_session_duration"] / 1800 * 100, 100)
        
        # Interaction depth already 0-100
        interaction_score = interaction_depth
        
        # Normalize return frequency (5+ days in last 7 = 100)
        return_score = min(return_frequency["last_7_days"] / 5 * 100, 100)
        
        # Weighted average
        engagement = (
            freq_score * 0.30 +
            duration_score * 0.25 +
            interaction_score * 0.25 +
            return_score * 0.20
        )
        
        return round(engagement, 2)
    
    def _calculate_dropout_risk(
        self,
        engagement_score: float,
        dropout_signals: List[str],
        sessions: List[Dict]
    ) -> float:
        """
        Calculate dropout risk (0-1) based on engagement and signals.
        
        Risk levels:
        - 0.0-0.3: Low risk
        - 0.3-0.6: Medium risk
        - 0.6-0.8: High risk
        - 0.8-1.0: Critical risk
        """
        risk = 0.0
        
        # Base risk from low engagement score
        if engagement_score < 40:
            risk += 0.4
        elif engagement_score < 60:
            risk += 0.2
        
        # Add risk from dropout signals
        signal_risk = min(len(dropout_signals) * 0.15, 0.5)
        risk += signal_risk
        
        # Add risk from declining trend
        if len(sessions) >= 4:
            sorted_sessions = sorted(sessions, key=lambda x: x["startTime"])
            mid_point = len(sorted_sessions) // 2
            recent_avg = sum(s["durationSeconds"] for s in sorted_sessions[mid_point:]) / mid_point
            older_avg = sum(s["durationSeconds"] for s in sorted_sessions[:mid_point]) / mid_point
            
            if older_avg > 0 and recent_avg < older_avg * 0.7:
                risk += 0.2
        
        # Check for long gaps
        if sessions:
            now = datetime.now()
            last_session = max(s["startTime"] for s in sessions)
            days_since = (now - last_session).days
            
            if days_since > 5:
                risk += 0.3
            elif days_since > 3:
                risk += 0.1
        
        return round(min(risk, 1.0), 2)
    
    async def _generate_engagement_insights(self, metrics: Dict[str, Any]) -> str:
        """
        Generate LLM-powered engagement insights.
        
        Args:
            metrics: Engagement metrics dictionary
            
        Returns:
            Insights text
        """
        try:
            system_message = SystemMessage(
                content="You are a student engagement specialist. Analyze engagement patterns and suggest interventions."
            )
            
            human_message = HumanMessage(
                content=f"""Analyze the following student engagement metrics:

Engagement Score: {metrics['engagement_score']:.1f}/100
Session Frequency: {metrics['session_frequency']:.1f} sessions per week
Average Session Duration: {metrics['avg_session_duration']/60:.1f} minutes
Interaction Depth: {metrics['interaction_depth']:.1f}/100
Dropout Risk: {metrics['dropout_risk']:.1%}
Days Active (Last 7): {metrics['return_frequency']['last_7_days']}

Dropout Signals:
{chr(10).join('- ' + signal for signal in metrics['dropout_signals']) if metrics['dropout_signals'] else '- None detected'}

Provide 2-3 specific recommendations for maintaining or improving engagement."""
            )
            
            response = await self.llm.ainvoke([system_message, human_message])
            return response.content
            
        except Exception as e:
            self.logger.error(f"[{self.name}] Error generating insights: {str(e)}")
            return "Engagement analysis complete. Monitor activity patterns."
    
    async def _store_engagement_metrics(self, student_id: str, metrics: Dict[str, Any]):
        """Store engagement metrics in Redis with 24-hour TTL"""
        try:
            redis_client = await get_redis_client()
            key = f"engagement:{student_id}"
            
            # Store as hash - flatten all fields for API compatibility
            store_data = {}
            for k, v in metrics.items():
                if isinstance(v, (dict, list)):
                    store_data[k] = json.dumps(v)
                else:
                    store_data[k] = str(v)
            
            await redis_client.hset(key, mapping=store_data)
            
            # Set TTL to 24 hours
            await redis_client.expire(key, 86400)
            
        except Exception as e:
            self.logger.error(f"[{self.name}] Error storing metrics in Redis: {str(e)}")
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default metrics when no data is available"""
        return {
            "engagement_score": 0.0,
            "session_duration": 0,
            "total_study_time": 0,
            "session_frequency": 0.0,
            "interaction_depth": 0.0,
            "dropout_risk": 0.5,
            "return_frequency": {
                "last_7_days": 0,
                "last_14_days": 0,
                "last_30_days": 0
            },
            "engagement_insights": "Insufficient engagement data available.",
            "dropout_signals": ["No recent activity data"]
        }
