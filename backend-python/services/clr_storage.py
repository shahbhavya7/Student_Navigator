"""
CLR Storage Service for Time-Series Data Management

Handles storage and retrieval of cognitive load data in both Redis (time-series)
and PostgreSQL (persistent storage).
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import asyncio
from collections import deque

from config.redis_client import redis_client
from config.database import get_db
from sqlalchemy.orm import Session


class CLRStorageService:
    """Service for managing cognitive load time-series data."""
    
    def __init__(self):
        self.batch_buffer = deque(maxlen=100)
        self.last_flush_time = datetime.now()
        self.flush_threshold = 10  # Flush after 10 entries
        self.flush_interval_seconds = 300  # Or after 5 minutes
        
    async def store_cognitive_load(self, student_id: str, session_id: str, clr_data: Dict):
        """
        Store cognitive load data in Redis time-series and batch to PostgreSQL.
        
        Args:
            student_id: Student identifier
            session_id: Session identifier
            clr_data: Cognitive load data dictionary
        """
        timestamp = clr_data.get('timestamp', int(datetime.now().timestamp() * 1000))
        
        # Store in Redis sorted set
        redis_key = f"clr:{student_id}"
        redis_value = json.dumps({
            'session_id': session_id,
            'score': clr_data.get('cognitive_load_score', 0),
            'fatigue_level': clr_data.get('mental_fatigue_level', 'low'),
            'patterns': clr_data.get('detected_patterns', []),
            'mood': clr_data.get('mood_indicators', {}),
            'timestamp': timestamp
        })
        
        await redis_client.data_client.zadd(redis_key, {redis_value: timestamp})
        
        # Set TTL of 30 days
        await redis_client.data_client.expire(redis_key, 30 * 24 * 60 * 60)
        
        # Add to batch buffer for PostgreSQL
        self.batch_buffer.append({
            'student_id': student_id,
            'session_id': session_id,
            'clr_data': clr_data,
            'timestamp': timestamp
        })
        
        # Check if we should flush
        time_since_flush = (datetime.now() - self.last_flush_time).total_seconds()
        if len(self.batch_buffer) >= self.flush_threshold or time_since_flush >= self.flush_interval_seconds:
            self.flush_to_postgres()
    
    def flush_to_postgres(self):
        """Flush batch buffer to PostgreSQL."""
        if not self.batch_buffer:
            return
        
        try:
            # Use asyncio to run batch insert
            asyncio.create_task(self._async_batch_insert(list(self.batch_buffer)))
            self.batch_buffer.clear()
            self.last_flush_time = datetime.now()
        except Exception as e:
            print(f"Error flushing to PostgreSQL: {e}")
    
    async def _async_batch_insert(self, entries: List[Dict]):
        """Async batch insert to PostgreSQL."""
        try:
            db = next(get_db())
            
            # Prepare bulk insert data
            # Note: Actual implementation depends on your CognitiveMetric model
            # This is a placeholder for the bulk insert logic
            
            for entry in entries:
                # Insert into CognitiveMetric table
                # db.execute(insert_query, entry)
                pass
            
            db.commit()
            
        except Exception as e:
            print(f"Batch insert error: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def get_cognitive_load_history(self, student_id: str, time_range: str = 'last_hour') -> Dict:
        """
        Get cognitive load history for specified time range.
        
        Args:
            student_id: Student identifier
            time_range: One of: last_hour, last_day, last_week, last_month
            
        Returns:
            Dictionary with history data and statistics
        """
        # Calculate time range
        now = datetime.now()
        time_ranges = {
            'last_hour': timedelta(hours=1),
            'last_day': timedelta(days=1),
            'last_week': timedelta(weeks=1),
            'last_month': timedelta(days=30)
        }
        
        delta = time_ranges.get(time_range, timedelta(hours=1))
        cutoff_time = int((now - delta).timestamp() * 1000)
        
        # Query Redis sorted set
        redis_key = f"clr:{student_id}"
        results = await redis_client.data_client.zrangebyscore(redis_key, cutoff_time, '+inf', withscores=True)
        
        history = []
        scores = []
        
        for value, timestamp in results:
            try:
                data = json.loads(value)
                score = data.get('score', 0)
                history.append({
                    'timestamp': int(timestamp),
                    'score': score,
                    'fatigue_level': data.get('fatigue_level', 'low'),
                    'patterns': data.get('patterns', []),
                    'session_id': data.get('session_id', '')
                })
                scores.append(score)
            except json.JSONDecodeError:
                continue
        
        # Calculate statistics
        stats = {}
        if scores:
            stats = {
                'min': min(scores),
                'max': max(scores),
                'average': sum(scores) / len(scores),
                'median': sorted(scores)[len(scores) // 2],
                'percentile_95': sorted(scores)[int(len(scores) * 0.95)] if len(scores) > 20 else max(scores)
            }
        
        return {
            'history': history,
            'statistics': stats,
            'data_points': len(history),
            'time_range': time_range
        }
    
    async def get_cognitive_load_trend(self, student_id: str, window_minutes: int = 30) -> Dict:
        """
        Calculate cognitive load trend for specified time window.
        
        Args:
            student_id: Student identifier
            window_minutes: Time window in minutes
            
        Returns:
            Trend analysis with direction and slope
        """
        history_data = await self.get_cognitive_load_history(student_id, 'last_hour')
        history = history_data['history']
        
        # Filter to specified window
        cutoff_time = int((datetime.now() - timedelta(minutes=window_minutes)).timestamp() * 1000)
        window_data = [entry for entry in history if entry['timestamp'] >= cutoff_time]
        
        if len(window_data) < 2:
            return {
                'trend': 'stable',
                'slope': 0.0,
                'confidence': 0.0,
                'data_points': len(window_data)
            }
        
        # Calculate linear regression slope
        n = len(window_data)
        x_values = list(range(n))
        y_values = [entry['score'] for entry in window_data]
        
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator
        
        # Determine trend direction
        if slope > 0.5:
            trend = 'increasing'
        elif slope < -0.5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Calculate confidence based on data consistency
        confidence = min(1.0, n / 10.0)
        
        return {
            'trend': trend,
            'slope': slope,
            'confidence': confidence,
            'data_points': n,
            'window_minutes': window_minutes
        }
    
    def get_session_cognitive_load(self, session_id: str) -> Dict:
        """
        Get all cognitive load measurements for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session cognitive load data with statistics
        """
        # This would require querying across all student CLR data
        # For now, return placeholder
        return {
            'session_id': session_id,
            'measurements': [],
            'statistics': {},
            'peak_load_moment': None,
            'patterns': []
        }
    
    async def calculate_baseline_metrics(self, student_id: str, days: int = 7) -> Dict:
        """
        Calculate baseline cognitive load metrics for student.
        
        Args:
            student_id: Student identifier
            days: Number of days to include in baseline
            
        Returns:
            Baseline metrics dictionary
        """
        # Get history for specified days
        cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        redis_key = f"clr:{student_id}"
        results = await redis_client.data_client.zrangebyscore(redis_key, cutoff_time, '+inf')
        
        if not results:
            return self._default_baseline()
        
        scores = []
        patterns_count = {}
        
        for value in results:
            try:
                data = json.loads(value)
                scores.append(data.get('score', 0))
                
                for pattern in data.get('patterns', []):
                    patterns_count[pattern] = patterns_count.get(pattern, 0) + 1
            except json.JSONDecodeError:
                continue
        
        if not scores:
            return self._default_baseline()
        
        # Calculate baseline statistics
        baseline = {
            'avg_cognitive_load': sum(scores) / len(scores),
            'std_cognitive_load': self._calculate_std(scores),
            'min_load': min(scores),
            'max_load': max(scores),
            'median_load': sorted(scores)[len(scores) // 2],
            'common_patterns': sorted(patterns_count.items(), key=lambda x: x[1], reverse=True)[:5],
            'data_points': len(scores),
            'days_analyzed': days,
            'calculated_at': datetime.now().isoformat()
        }
        
        # Store baseline in Redis
        baseline_key = f"baseline:{student_id}"
        await redis_client.data_client.hset(baseline_key, mapping={
            'avg_load': baseline['avg_cognitive_load'],
            'std_load': baseline['std_cognitive_load'],
            'calculated_at': baseline['calculated_at']
        })
        await redis_client.data_client.expire(baseline_key, 24 * 60 * 60)  # 1 day TTL
        
        return baseline
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _default_baseline(self) -> Dict:
        """Return default baseline when no data exists."""
        return {
            'avg_cognitive_load': 40.0,
            'std_cognitive_load': 15.0,
            'min_load': 0.0,
            'max_load': 100.0,
            'median_load': 40.0,
            'common_patterns': [],
            'data_points': 0,
            'days_analyzed': 0,
            'calculated_at': datetime.now().isoformat()
        }
    
    def batch_write_to_postgres(self, entries: List[Dict]):
        """
        Batch write cognitive load entries to PostgreSQL.
        
        Args:
            entries: List of CLR data entries to write
        """
        if not entries:
            return
        
        try:
            db = next(get_db())
            
            # Bulk insert logic here
            # Using SQLAlchemy bulk operations
            
            db.commit()
            
        except Exception as e:
            print(f"Batch write error: {e}")
            db.rollback()
        finally:
            db.close()


# Singleton instance
clr_storage_service = CLRStorageService()
