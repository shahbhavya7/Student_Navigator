"""Content analytics and feedback loop system."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

try:
    from prisma import Prisma
    PRISMA_AVAILABLE = True
except ImportError:
    PRISMA_AVAILABLE = False
    Prisma = None

logger = logging.getLogger(__name__)


class ContentAnalytics:
    """Track content effectiveness and create feedback loops."""
    
    def __init__(self):
        """Initialize content analytics."""
        if not PRISMA_AVAILABLE:
            logger.warning("Prisma not available, ContentAnalytics will operate in mock mode")
            self.prisma = None
        else:
            self.prisma = Prisma()
        logger.info("ContentAnalytics initialized")
    
    async def connect(self):
        """Connect to database."""
        if self.prisma and not self.prisma.is_connected():
            await self.prisma.connect()
    
    async def disconnect(self):
        """Disconnect from database."""
        if self.prisma and self.prisma.is_connected():
            await self.prisma.disconnect()
        if not self.prisma.is_connected():
            await self.prisma.connect()
    
    async def disconnect(self):
        """Disconnect from database."""
        if self.prisma.is_connected():
            await self.prisma.disconnect()
    
    async def track_content_usage(
        self,
        content_id: str,
        student_id: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track when content is delivered or interacted with.
        
        Args:
            content_id: Content module ID
            student_id: Student ID
            event_type: Type of event (delivered, started, completed, abandoned)
            metadata: Additional event metadata
        
        Returns:
            True if tracked successfully
        """
        try:
            await self.connect()
            
            # Record usage event (could be in a separate analytics table)
            # For now, we'll update or create student progress
            
            if event_type == 'delivered':
                # Content delivered to student
                logger.info(f"Content {content_id} delivered to student {student_id}")
            
            elif event_type == 'started':
                # Student started content
                await self.prisma.studentprogress.upsert(
                    where={
                        'studentId_moduleId': {
                            'studentId': student_id,
                            'moduleId': content_id
                        }
                    },
                    data={
                        'create': {
                            'studentId': student_id,
                            'moduleId': content_id,
                            'completed': False,
                            'startedAt': datetime.utcnow()
                        },
                        'update': {
                            'startedAt': datetime.utcnow()
                        }
                    }
                )
            
            elif event_type == 'completed':
                # Student completed content
                await self.prisma.studentprogress.upsert(
                    where={
                        'studentId_moduleId': {
                            'studentId': student_id,
                            'moduleId': content_id
                        }
                    },
                    data={
                        'create': {
                            'studentId': student_id,
                            'moduleId': content_id,
                            'completed': True,
                            'completedAt': datetime.utcnow()
                        },
                        'update': {
                            'completed': True,
                            'completedAt': datetime.utcnow()
                        }
                    }
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking content usage: {str(e)}")
            return False
    
    async def track_quiz_performance(
        self,
        content_id: str,
        student_id: str,
        score: float,
        total_questions: int,
        time_spent_minutes: int
    ) -> bool:
        """
        Track quiz performance metrics.
        
        Args:
            content_id: Quiz content ID
            student_id: Student ID
            score: Score achieved (0-1)
            total_questions: Total questions in quiz
            time_spent_minutes: Time spent on quiz
        
        Returns:
            True if tracked successfully
        """
        try:
            await self.connect()
            
            # Update student progress with quiz score
            await self.prisma.studentprogress.upsert(
                where={
                    'studentId_moduleId': {
                        'studentId': student_id,
                        'moduleId': content_id
                    }
                },
                data={
                    'create': {
                        'studentId': student_id,
                        'moduleId': content_id,
                        'completed': True,
                        'score': score,
                        'timeSpent': time_spent_minutes,
                        'completedAt': datetime.utcnow()
                    },
                    'update': {
                        'completed': True,
                        'score': score,
                        'timeSpent': time_spent_minutes,
                        'completedAt': datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Tracked quiz performance for content {content_id}: score={score}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking quiz performance: {str(e)}")
            return False
    
    async def calculate_content_effectiveness_score(
        self,
        content_id: str
    ) -> float:
        """
        Calculate effectiveness score for content (0-100).
        
        Based on:
        - Completion rate
        - Average quiz scores
        - Time-to-complete accuracy
        - Student engagement
        
        Args:
            content_id: Content module ID
        
        Returns:
            Effectiveness score (0-100)
        """
        try:
            await self.connect()
            
            # Get content module
            content_module = await self.prisma.contentmodule.find_unique(
                where={'id': content_id},
                include={'studentProgress': True}
            )
            
            if not content_module or not content_module.studentProgress:
                return 50.0  # Default neutral score
            
            progress_records = content_module.studentProgress
            total_students = len(progress_records)
            
            if total_students == 0:
                return 50.0
            
            # Completion rate (0-40 points)
            completed_count = sum(1 for p in progress_records if p.completed)
            completion_rate = completed_count / total_students
            completion_score = completion_rate * 40
            
            # Average quiz performance (0-40 points)
            scores = [p.score for p in progress_records if p.score is not None]
            avg_score = sum(scores) / len(scores) if scores else 0.5
            performance_score = avg_score * 40
            
            # Time accuracy (0-20 points)
            time_accuracy_score = 0
            if content_module.estimatedMinutes:
                times = [p.timeSpent for p in progress_records if p.timeSpent]
                if times:
                    avg_time = sum(times) / len(times)
                    ratio = avg_time / content_module.estimatedMinutes
                    # Perfect score if within 20% of estimate
                    if 0.8 <= ratio <= 1.2:
                        time_accuracy_score = 20
                    elif 0.6 <= ratio <= 1.4:
                        time_accuracy_score = 15
                    else:
                        time_accuracy_score = 10
            
            effectiveness = completion_score + performance_score + time_accuracy_score
            
            logger.info(f"Content {content_id} effectiveness score: {effectiveness:.2f}")
            return round(effectiveness, 2)
            
        except Exception as e:
            logger.error(f"Error calculating effectiveness score: {str(e)}")
            return 50.0
    
    async def identify_low_performing_content(
        self,
        threshold: float = 40.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Identify content with poor effectiveness scores.
        
        Args:
            threshold: Effectiveness threshold (below this is "low performing")
            limit: Maximum results to return
        
        Returns:
            List of low-performing content items
        """
        try:
            await self.connect()
            
            # Get all content modules with progress data
            content_modules = await self.prisma.contentmodule.find_many(
                include={'studentProgress': True},
                take=100  # Analyze recent content
            )
            
            low_performing = []
            
            for module in content_modules:
                if module.studentProgress and len(module.studentProgress) >= 5:  # Minimum sample size
                    effectiveness = await self.calculate_content_effectiveness_score(module.id)
                    
                    if effectiveness < threshold:
                        low_performing.append({
                            'content_id': module.id,
                            'title': module.title,
                            'module_type': module.moduleType,
                            'difficulty': module.difficulty,
                            'effectiveness_score': effectiveness,
                            'student_count': len(module.studentProgress)
                        })
            
            # Sort by lowest effectiveness
            low_performing.sort(key=lambda x: x['effectiveness_score'])
            
            logger.info(f"Identified {len(low_performing)} low-performing content items")
            return low_performing[:limit]
            
        except Exception as e:
            logger.error(f"Error identifying low-performing content: {str(e)}")
            return []
    
    async def get_content_quality_trends(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze content quality trends over time.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with trend analysis
        """
        try:
            await self.connect()
            
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent content
            recent_content = await self.prisma.contentmodule.find_many(
                where={
                    'createdAt': {
                        'gte': since_date
                    }
                },
                include={'studentProgress': True}
            )
            
            if not recent_content:
                return {'error': 'No recent content found'}
            
            # Calculate average effectiveness
            effectiveness_scores = []
            for module in recent_content:
                if module.studentProgress:
                    score = await self.calculate_content_effectiveness_score(module.id)
                    effectiveness_scores.append(score)
            
            avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores) if effectiveness_scores else 0
            
            # Count by type
            type_counts = {}
            for module in recent_content:
                module_type = module.moduleType
                type_counts[module_type] = type_counts.get(module_type, 0) + 1
            
            # Completion rate
            total_progress = sum(len(m.studentProgress or []) for m in recent_content)
            total_completed = sum(
                sum(1 for p in (m.studentProgress or []) if p.completed)
                for m in recent_content
            )
            overall_completion_rate = (total_completed / total_progress * 100) if total_progress > 0 else 0
            
            return {
                'period_days': days,
                'total_content_created': len(recent_content),
                'average_effectiveness': round(avg_effectiveness, 2),
                'overall_completion_rate_percent': round(overall_completion_rate, 2),
                'content_by_type': type_counts,
                'total_student_interactions': total_progress
            }
            
        except Exception as e:
            logger.error(f"Error analyzing quality trends: {str(e)}")
            return {'error': str(e)}
    
    async def generate_improvement_recommendations(
        self,
        content_id: str
    ) -> List[str]:
        """
        Generate recommendations for improving content based on analytics.
        
        Args:
            content_id: Content module ID
        
        Returns:
            List of improvement recommendations
        """
        try:
            await self.connect()
            
            recommendations = []
            
            # Get content and analytics
            content_module = await self.prisma.contentmodule.find_unique(
                where={'id': content_id},
                include={'studentProgress': True}
            )
            
            if not content_module or not content_module.studentProgress:
                return ["Insufficient data for recommendations"]
            
            progress_records = content_module.studentProgress
            
            # Analyze completion rate
            completed = sum(1 for p in progress_records if p.completed)
            completion_rate = completed / len(progress_records)
            
            if completion_rate < 0.5:
                recommendations.append(
                    "Low completion rate detected. Consider: "
                    "1) Simplifying content, 2) Breaking into smaller chunks, "
                    "3) Adding more engaging examples"
                )
            
            # Analyze quiz scores
            scores = [p.score for p in progress_records if p.score is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                if avg_score < 0.6:
                    recommendations.append(
                        "Low quiz scores indicate difficulty may be too high. "
                        "Consider adjusting to easier difficulty or adding more explanations."
                    )
                elif avg_score > 0.9:
                    recommendations.append(
                        "Very high quiz scores suggest content may be too easy. "
                        "Consider increasing difficulty or depth."
                    )
            
            # Analyze time spent
            times = [p.timeSpent for p in progress_records if p.timeSpent]
            if times and content_module.estimatedMinutes:
                avg_time = sum(times) / len(times)
                ratio = avg_time / content_module.estimatedMinutes
                
                if ratio > 1.5:
                    recommendations.append(
                        f"Students taking {ratio:.1f}x longer than estimated. "
                        "Content may be too dense or complex. Consider simplification."
                    )
                elif ratio < 0.5:
                    recommendations.append(
                        f"Students completing much faster than estimated. "
                        "Consider adding more depth or practice problems."
                    )
            
            if not recommendations:
                recommendations.append("Content performing well. No immediate changes recommended.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return ["Error analyzing content"]
