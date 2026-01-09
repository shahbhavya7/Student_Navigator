"""
CLR Monitoring Service

Tracks and monitors CLR Agent performance metrics:
- Execution counts and durations
- Pattern detection accuracy
- LLM API usage
- Error rates
"""

import time
from typing import Dict, List
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CLRMonitoringService:
    """Service for monitoring CLR Agent performance."""
    
    def __init__(self):
        # Execution metrics
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.error_count = 0
        self.last_execution_time = None
        
        # Pattern detection metrics
        self.pattern_detections = defaultdict(int)
        self.total_patterns_detected = 0
        
        # LLM metrics
        self.llm_calls = 0
        self.llm_errors = 0
        self.llm_cache_hits = 0
        self.llm_total_cost = 0.0  # Estimated cost in USD
        
        # Performance tracking
        self.execution_times: List[float] = []
        self.max_execution_time = 0.0
        self.min_execution_time = float('inf')
        
        # Service start time
        self.start_time = datetime.now()
    
    def record_execution(self, duration_ms: float, success: bool = True, patterns: List[str] = None):
        """
        Record a CLR Agent execution.
        
        Args:
            duration_ms: Execution duration in milliseconds
            success: Whether execution was successful
            patterns: List of detected patterns
        """
        self.execution_count += 1
        self.last_execution_time = datetime.now()
        
        duration_seconds = duration_ms / 1000.0
        self.total_execution_time += duration_seconds
        self.execution_times.append(duration_seconds)
        
        # Keep only last 1000 execution times
        if len(self.execution_times) > 1000:
            self.execution_times.pop(0)
        
        # Update min/max
        self.max_execution_time = max(self.max_execution_time, duration_seconds)
        if duration_seconds > 0:
            self.min_execution_time = min(self.min_execution_time, duration_seconds)
        
        if not success:
            self.error_count += 1
        
        # Record pattern detections
        if patterns:
            for pattern in patterns:
                self.pattern_detections[pattern] += 1
                self.total_patterns_detected += 1
        
        logger.debug(f"CLR execution recorded: {duration_ms:.2f}ms, success={success}")
    
    def record_llm_call(self, success: bool = True, cached: bool = False, cost: float = 0.0):
        """
        Record an LLM API call.
        
        Args:
            success: Whether call was successful
            cached: Whether result was from cache
            cost: Estimated cost in USD
        """
        self.llm_calls += 1
        
        if cached:
            self.llm_cache_hits += 1
        
        if not success:
            self.llm_errors += 1
        
        self.llm_total_cost += cost
        
        logger.debug(f"LLM call recorded: success={success}, cached={cached}, cost=${cost:.4f}")
    
    def get_metrics(self) -> Dict:
        """Get comprehensive monitoring metrics."""
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate average execution time
        avg_execution_time = (
            self.total_execution_time / self.execution_count 
            if self.execution_count > 0 
            else 0.0
        )
        
        # Calculate error rate
        error_rate = (
            self.error_count / self.execution_count 
            if self.execution_count > 0 
            else 0.0
        )
        
        # Calculate LLM cache hit rate
        cache_hit_rate = (
            self.llm_cache_hits / self.llm_calls 
            if self.llm_calls > 0 
            else 0.0
        )
        
        # Calculate executions per hour
        executions_per_hour = (
            (self.execution_count / uptime_seconds) * 3600 
            if uptime_seconds > 0 
            else 0.0
        )
        
        # Get top patterns
        top_patterns = sorted(
            self.pattern_detections.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'uptime_seconds': uptime_seconds,
            'uptime_hours': uptime_seconds / 3600,
            'execution_metrics': {
                'total_executions': self.execution_count,
                'successful_executions': self.execution_count - self.error_count,
                'failed_executions': self.error_count,
                'error_rate': error_rate,
                'executions_per_hour': executions_per_hour,
                'last_execution': self.last_execution_time.isoformat() if self.last_execution_time else None
            },
            'performance_metrics': {
                'avg_execution_time_seconds': avg_execution_time,
                'min_execution_time_seconds': self.min_execution_time if self.min_execution_time != float('inf') else 0.0,
                'max_execution_time_seconds': self.max_execution_time,
                'recent_avg_execution_time': self._calculate_recent_average()
            },
            'pattern_metrics': {
                'total_patterns_detected': self.total_patterns_detected,
                'unique_patterns': len(self.pattern_detections),
                'top_patterns': dict(top_patterns),
                'patterns_per_execution': (
                    self.total_patterns_detected / self.execution_count
                    if self.execution_count > 0
                    else 0.0
                )
            },
            'llm_metrics': {
                'total_calls': self.llm_calls,
                'cache_hits': self.llm_cache_hits,
                'cache_hit_rate': cache_hit_rate,
                'errors': self.llm_errors,
                'error_rate': self.llm_errors / self.llm_calls if self.llm_calls > 0 else 0.0,
                'estimated_total_cost_usd': self.llm_total_cost,
                'avg_cost_per_call': self.llm_total_cost / self.llm_calls if self.llm_calls > 0 else 0.0
            }
        }
    
    def _calculate_recent_average(self) -> float:
        """Calculate average of last 100 execution times."""
        if not self.execution_times:
            return 0.0
        
        recent_times = self.execution_times[-100:]
        return sum(recent_times) / len(recent_times)
    
    def get_health_status(self) -> Dict:
        """Get health status for health check endpoint."""
        metrics = self.get_metrics()
        
        # Determine health status
        error_rate = metrics['execution_metrics']['error_rate']
        recent_avg_time = metrics['performance_metrics']['recent_avg_execution_time']
        
        if error_rate > 0.2:  # More than 20% errors
            status = 'unhealthy'
            message = f'High error rate: {error_rate:.1%}'
        elif recent_avg_time > 10.0:  # More than 10 seconds average
            status = 'degraded'
            message = f'Slow performance: {recent_avg_time:.2f}s average'
        elif self.execution_count == 0:
            status = 'idle'
            message = 'No executions yet'
        else:
            status = 'healthy'
            message = 'Operating normally'
        
        return {
            'status': status,
            'message': message,
            'metrics': {
                'total_executions': self.execution_count,
                'error_rate': error_rate,
                'avg_execution_time': metrics['performance_metrics']['avg_execution_time_seconds'],
                'uptime_hours': metrics['uptime_hours']
            }
        }
    
    def reset_metrics(self):
        """Reset all metrics (for testing or manual reset)."""
        logger.info("Resetting CLR monitoring metrics")
        
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.error_count = 0
        self.last_execution_time = None
        
        self.pattern_detections.clear()
        self.total_patterns_detected = 0
        
        self.llm_calls = 0
        self.llm_errors = 0
        self.llm_cache_hits = 0
        self.llm_total_cost = 0.0
        
        self.execution_times.clear()
        self.max_execution_time = 0.0
        self.min_execution_time = float('inf')
        
        self.start_time = datetime.now()


# Singleton instance
clr_monitoring_service = CLRMonitoringService()
