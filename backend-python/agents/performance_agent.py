"""
Performance Agent Implementation

Analyzes student quiz performance, calculates learning velocity, identifies improvement trends,
and detects weak topics requiring additional support.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base_agent import BaseAgent
from agents.state import AgentState
from analytics.improvement_curves import ImprovementCurveCalculator, PerformanceAnalyzer
from config.database import get_async_db
from config.redis_client import redis_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import json


class PerformanceAgent(BaseAgent):
    """Agent for analyzing student performance and learning progression"""
    
    def __init__(self, name: str = "performance_agent"):
        super().__init__(name)
        self.curve_calculator = ImprovementCurveCalculator()
        self.performance_analyzer = PerformanceAnalyzer()
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.7)
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze student performance and calculate improvement metrics.
        
        Args:
            state: Current agent state with student_id and session_id
            
        Returns:
            Dictionary with performance metrics and insights
        """
        self.logger.info(f"[{self.name}] Analyzing performance for student {state.get('student_id')}")
        
        student_id = state.get("student_id")
        session_id = state.get("session_id")
        
        if not student_id:
            self.logger.warning(f"[{self.name}] No student_id provided")
            return self._get_default_metrics()
        
        try:
            # Fetch quiz results from database
            quiz_results = await self._fetch_quiz_results(student_id, days=30)
            
            if not quiz_results:
                self.logger.info(f"[{self.name}] No quiz data found for student {student_id}")
                return self._get_default_metrics()
            
            # Calculate improvement metrics
            learning_velocity = self.curve_calculator.calculate_learning_velocity(quiz_results)
            improvement_trend = self.curve_calculator.calculate_improvement_trend(quiz_results)
            plateau_detected = self.curve_calculator.detect_learning_plateau(quiz_results)
            retention_rate = self.curve_calculator.calculate_retention_rate(quiz_results)
            predicted_score = self.curve_calculator.predict_next_performance(quiz_results)
            
            # Analyze quiz accuracy
            accuracy_metrics = self.performance_analyzer.analyze_quiz_accuracy(quiz_results)
            
            # Analyze time efficiency
            efficiency_metrics = self.performance_analyzer.analyze_time_efficiency(quiz_results)
            
            # Detect weak topics
            weak_topics = self.performance_analyzer.detect_weak_topics(quiz_results)
            
            # Calculate consistency score
            consistency_score = self.performance_analyzer.calculate_consistency_score(quiz_results)
            
            # Calculate task completion rate
            task_completion_rate = await self._calculate_task_completion_rate(student_id)
            
            # Generate LLM-powered insights
            performance_insights = await self._generate_performance_insights({
                "quiz_accuracy": accuracy_metrics["overall_accuracy"],
                "recent_accuracy": accuracy_metrics["recent_accuracy"],
                "learning_velocity": learning_velocity,
                "improvement_trend": improvement_trend,
                "weak_topics": weak_topics,
                "time_efficiency": efficiency_metrics["time_efficiency_score"],
                "consistency_score": consistency_score,
                "plateau_detected": plateau_detected
            })
            
            # Prepare complete performance data for storage and API compatibility
            complete_performance_data = {
                "student_id": student_id,
                "quiz_accuracy": accuracy_metrics["overall_accuracy"],
                "recent_accuracy": accuracy_metrics["recent_accuracy"],
                "accuracy_by_difficulty": accuracy_metrics["accuracy_by_difficulty"],
                "learning_velocity": learning_velocity,
                "improvement_trend": improvement_trend,
                "plateau_detected": plateau_detected,
                "retention_rate": retention_rate,
                "predicted_next_score": predicted_score,
                "consistency_score": consistency_score,
                "task_completion_rate": task_completion_rate,
                "weak_topics": weak_topics,
                "performance_insights": performance_insights,
                "timestamp": int(datetime.now().timestamp())
            }
            
            # Store in Redis
            await self._store_performance_metrics(student_id, complete_performance_data)
            
            # Prepare performance_metrics for state (backward compatibility)
            performance_metrics = {
                "student_id": student_id,
                "learning_velocity": learning_velocity,
                "improvement_trend": improvement_trend,
                "plateau_detected": plateau_detected,
                "retention_rate": retention_rate,
                "predicted_next_score": predicted_score,
                "consistency_score": consistency_score,
                "timestamp": int(datetime.now().timestamp())
            }
            
            # Publish event
            await self.publish_event("performance_analyzed", {
                "student_id": student_id,
                "session_id": session_id,
                "learning_velocity": learning_velocity,
                "improvement_trend": improvement_trend,
                "weak_topics": weak_topics
            })
            
            self.logger.info(f"[{self.name}] Performance analysis complete for student {student_id}")
            
            return {
                "performance_metrics": performance_metrics,
                "quiz_accuracy": accuracy_metrics["overall_accuracy"],
                "recent_accuracy": accuracy_metrics["recent_accuracy"],
                "accuracy_by_difficulty": accuracy_metrics["accuracy_by_difficulty"],
                "learning_velocity": learning_velocity,
                "improvement_trend": improvement_trend,
                "weak_topics": weak_topics,
                "time_efficiency": efficiency_metrics["time_efficiency_score"],
                "consistency_score": consistency_score,
                "task_completion_rate": task_completion_rate,
                "performance_insights": performance_insights,
                "plateau_detected": plateau_detected,
                "retention_rate": retention_rate
            }
            
        except Exception as e:
            self.logger.error(f"[{self.name}] Error analyzing performance: {str(e)}")
            return self._get_default_metrics()
    
    async def _fetch_quiz_results(self, student_id: str, days: int = 30) -> List[Dict]:
        """
        Fetch quiz results from database for the specified time period.
        
        Args:
            student_id: Student identifier
            days: Number of days to look back
            
        Returns:
            List of quiz result dictionaries
        """
        results = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            async for db in get_async_db():
                # Query quiz_results table with JOIN to content_modules for topic
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
                
                break  # Exit after first iteration
                
        except Exception as e:
            self.logger.error(f"[{self.name}] Error fetching quiz results: {str(e)}")
        
        return results
    
    async def _calculate_task_completion_rate(self, student_id: str) -> float:
        """
        Calculate task completion rate from learning paths.
        
        Args:
            student_id: Student identifier
            
        Returns:
            Completion rate as percentage (0-100)
        """
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
            self.logger.error(f"[{self.name}] Error calculating task completion rate: {str(e)}")
        
        return 0.0
    
    async def _generate_performance_insights(self, metrics: Dict[str, Any]) -> str:
        """
        Generate LLM-powered performance insights.
        
        Args:
            metrics: Performance metrics dictionary
            
        Returns:
            Insights text
        """
        try:
            system_message = SystemMessage(
                content="You are an educational performance analyst. Analyze student performance data and provide 2-3 specific, actionable insights."
            )
            
            human_message = HumanMessage(
                content=f"""Analyze the following student performance metrics:

Quiz Accuracy: {metrics['quiz_accuracy']:.1f}% (Recent: {metrics['recent_accuracy']:.1f}%)
Learning Velocity: {metrics['learning_velocity']:.2f} percentage points per day
Improvement Trend: {metrics['improvement_trend']}
Weak Topics: {', '.join(metrics['weak_topics']) if metrics['weak_topics'] else 'None'}
Time Efficiency Score: {metrics['time_efficiency']:.2f} correct answers per minute
Consistency Score: {metrics['consistency_score']:.1f}/100
Plateau Detected: {'Yes' if metrics['plateau_detected'] else 'No'}

Provide 2-3 specific insights and recommendations."""
            )
            
            response = await self.llm.ainvoke([system_message, human_message])
            return response.content
            
        except Exception as e:
            self.logger.error(f"[{self.name}] Error generating insights: {str(e)}")
            return "Performance analysis complete. Continue monitoring progress."
    
    async def _store_performance_metrics(self, student_id: str, metrics: Dict[str, Any]):
        """Store performance metrics in Redis with 24-hour TTL"""
        try:
            redis_client = await get_redis_client()
            key = f"performance:{student_id}"
            
            # Store as hash - flatten all fields for API compatibility
            store_data = {}
            for k, v in metrics.items():
                if isinstance(v, (dict, list)):
                    store_data[k] = json.dumps(v)
                else:
                    store_data[k] = str(v)
            
            await redis_client.cache_client.hset(key, mapping=store_data)
            
            # Set TTL to 24 hours
            await redis_client.cache_client.expire(key, 86400)
            
        except Exception as e:
            self.logger.error(f"[{self.name}] Error storing metrics in Redis: {str(e)}")
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default metrics when no data is available"""
        return {
            "performance_metrics": {
                "learning_velocity": 0.0,
                "improvement_trend": "insufficient_data",
                "plateau_detected": False,
                "retention_rate": 100.0,
                "predicted_next_score": 50.0,
                "consistency_score": 100.0,
                "timestamp": int(datetime.now().timestamp())
            },
            "quiz_accuracy": 0.0,
            "recent_accuracy": 0.0,
            "accuracy_by_difficulty": {},
            "learning_velocity": 0.0,
            "improvement_trend": "insufficient_data",
            "weak_topics": [],
            "time_efficiency": 0.0,
            "consistency_score": 100.0,
            "task_completion_rate": 0.0,
            "performance_insights": "Insufficient performance data available.",
            "plateau_detected": False,
            "retention_rate": 100.0
        }
