"""
CLR Maintenance Service

Background tasks for CLR system maintenance:
- Daily baseline updates
- Data cleanup
- Weekly report generation
"""

import asyncio
from datetime import datetime, time
from typing import Dict, List
import logging

from services.clr_storage import clr_storage_service
from config.redis_client import redis_client

logger = logging.getLogger(__name__)


class CLRMaintenanceService:
    """Service for background maintenance tasks."""
    
    def __init__(self):
        self.tasks: List[asyncio.Task] = []
        self.is_running = False
    
    async def start(self):
        """Start all maintenance tasks."""
        if self.is_running:
            logger.warning("Maintenance service already running")
            return
        
        self.is_running = True
        logger.info("🔧 Starting CLR maintenance service")
        
        # Schedule tasks
        self.tasks.append(asyncio.create_task(self._daily_baseline_update_scheduler()))
        self.tasks.append(asyncio.create_task(self._daily_cleanup_scheduler()))
        self.tasks.append(asyncio.create_task(self._weekly_report_scheduler()))
    
    async def stop(self):
        """Stop all maintenance tasks."""
        self.is_running = False
        logger.info("🛑 Stopping CLR maintenance service")
        
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
    
    async def _daily_baseline_update_scheduler(self):
        """Schedule baseline updates to run daily at 2 AM."""
        while self.is_running:
            try:
                # Calculate time until next 2 AM
                now = datetime.now()
                target_time = datetime.combine(now.date(), time(2, 0))
                
                # If it's past 2 AM today, schedule for tomorrow
                if now >= target_time:
                    from datetime import timedelta
                    target_time += timedelta(days=1)
                
                # Wait until target time
                wait_seconds = (target_time - now).total_seconds()
                logger.info(f"⏰ Next baseline update in {wait_seconds / 3600:.1f} hours")
                
                await asyncio.sleep(wait_seconds)
                
                # Run baseline update task
                await self.update_baselines_task()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in baseline update scheduler: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)
    
    async def _daily_cleanup_scheduler(self):
        """Schedule cleanup to run daily at 3 AM."""
        while self.is_running:
            try:
                # Calculate time until next 3 AM
                now = datetime.now()
                target_time = datetime.combine(now.date(), time(3, 0))
                
                # If it's past 3 AM today, schedule for tomorrow
                if now >= target_time:
                    from datetime import timedelta
                    target_time += timedelta(days=1)
                
                # Wait until target time
                wait_seconds = (target_time - now).total_seconds()
                logger.info(f"⏰ Next cleanup in {wait_seconds / 3600:.1f} hours")
                
                await asyncio.sleep(wait_seconds)
                
                # Run cleanup task
                await self.cleanup_old_data_task()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)
    
    async def _weekly_report_scheduler(self):
        """Schedule weekly reports to run on Sunday at midnight."""
        while self.is_running:
            try:
                # Calculate time until next Sunday midnight
                now = datetime.now()
                days_until_sunday = (6 - now.weekday()) % 7
                
                if days_until_sunday == 0 and now.hour >= 0:
                    days_until_sunday = 7
                
                from datetime import timedelta
                target_time = datetime.combine(
                    now.date() + timedelta(days=days_until_sunday),
                    time(0, 0)
                )
                
                # Wait until target time
                wait_seconds = (target_time - now).total_seconds()
                logger.info(f"⏰ Next weekly report in {wait_seconds / 86400:.1f} days")
                
                await asyncio.sleep(wait_seconds)
                
                # Run weekly report task
                await self.generate_weekly_reports_task()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in weekly report scheduler: {e}")
                # Wait 1 day before retrying
                await asyncio.sleep(86400)
    
    async def update_baselines_task(self):
        """
        Recalculate baseline metrics for all active students.
        Runs daily at 2 AM.
        """
        logger.info("🔄 Starting baseline update task")
        
        try:
            # Get list of all students with CLR data
            # This would require querying Redis for all clr:* keys
            # For now, use a placeholder implementation
            
            updated_count = 0
            error_count = 0
            
            # Example: Get students from Redis pattern scan
            cursor = 0
            student_ids = set()
            
            while True:
                cursor, keys = redis_client.scan(cursor, match="clr:*", count=100)
                for key in keys:
                    # Extract student_id from key pattern "clr:{student_id}"
                    student_id = key.decode('utf-8').split(':', 1)[1] if isinstance(key, bytes) else key.split(':', 1)[1]
                    student_ids.add(student_id)
                
                if cursor == 0:
                    break
            
            logger.info(f"Found {len(student_ids)} students with CLR data")
            
            # Update baseline for each student
            for student_id in student_ids:
                try:
                    baseline = clr_storage_service.calculate_baseline_metrics(student_id, days=7)
                    updated_count += 1
                    
                    if updated_count % 100 == 0:
                        logger.info(f"Updated baselines for {updated_count} students...")
                        
                except Exception as e:
                    logger.error(f"Error updating baseline for student {student_id}: {e}")
                    error_count += 1
            
            logger.info(f"✅ Baseline update complete: {updated_count} updated, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Baseline update task failed: {e}")
    
    async def cleanup_old_data_task(self):
        """
        Remove old data from Redis and compress PostgreSQL data.
        Runs daily at 3 AM.
        """
        logger.info("🧹 Starting cleanup task")
        
        try:
            from datetime import timedelta
            
            # Calculate cutoff time (30 days ago)
            cutoff_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
            
            cleaned_count = 0
            
            # Get all CLR keys
            cursor = 0
            clr_keys = []
            
            while True:
                cursor, keys = redis_client.scan(cursor, match="clr:*", count=100)
                clr_keys.extend(keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"Found {len(clr_keys)} CLR keys to check")
            
            # Clean old entries from each key
            for key in clr_keys:
                try:
                    # Remove entries older than cutoff
                    removed = redis_client.zremrangebyscore(key, '-inf', cutoff_time)
                    cleaned_count += removed
                    
                except Exception as e:
                    logger.error(f"Error cleaning key {key}: {e}")
            
            logger.info(f"✅ Cleanup complete: Removed {cleaned_count} old entries from Redis")
            
            # TODO: Implement PostgreSQL compression for data older than 90 days
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
    
    async def generate_weekly_reports_task(self):
        """
        Generate weekly summary reports for students.
        Runs weekly on Sunday at midnight.
        """
        logger.info("📊 Starting weekly report generation")
        
        try:
            from datetime import timedelta
            
            # Get all students with CLR data from past week
            week_ago = datetime.now() - timedelta(days=7)
            
            report_count = 0
            
            # Get student IDs
            cursor = 0
            student_ids = set()
            
            while True:
                cursor, keys = redis_client.scan(cursor, match="clr:*", count=100)
                for key in keys:
                    student_id = key.decode('utf-8').split(':', 1)[1] if isinstance(key, bytes) else key.split(':', 1)[1]
                    student_ids.add(student_id)
                
                if cursor == 0:
                    break
            
            logger.info(f"Generating reports for {len(student_ids)} students")
            
            # Generate report for each student
            for student_id in student_ids:
                try:
                    # Get week's data
                    history_data = clr_storage_service.get_cognitive_load_history(
                        student_id, 'last_week'
                    )
                    
                    if not history_data.get('history'):
                        continue
                    
                    # Generate summary report
                    report = self._generate_student_report(student_id, history_data)
                    
                    # Store report in Redis with 30-day TTL
                    report_key = f"clr_report:{student_id}:{datetime.now().strftime('%Y-%m-%d')}"
                    import json
                    redis_client.setex(
                        report_key,
                        30 * 24 * 60 * 60,
                        json.dumps(report)
                    )
                    
                    report_count += 1
                    
                except Exception as e:
                    logger.error(f"Error generating report for student {student_id}: {e}")
            
            logger.info(f"✅ Weekly reports generated: {report_count} reports")
            
        except Exception as e:
            logger.error(f"Weekly report task failed: {e}")
    
    def _generate_student_report(self, student_id: str, history_data: Dict) -> Dict:
        """Generate summary report from history data."""
        stats = history_data.get('statistics', {})
        history = history_data.get('history', [])
        
        # Identify concerning patterns
        high_load_count = sum(1 for entry in history if entry.get('score', 0) > 75)
        concerning = high_load_count > len(history) * 0.2  # More than 20% high load
        
        report = {
            'student_id': student_id,
            'week_ending': datetime.now().strftime('%Y-%m-%d'),
            'avg_cognitive_load': stats.get('average', 0),
            'max_cognitive_load': stats.get('max', 0),
            'min_cognitive_load': stats.get('min', 0),
            'high_load_sessions': high_load_count,
            'total_sessions': len(history),
            'concerning_pattern': concerning,
            'generated_at': datetime.now().isoformat()
        }
        
        return report


# Singleton instance
clr_maintenance_service = CLRMaintenanceService()
