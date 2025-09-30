"""
Lambda Performance Monitoring System
===================================

Comprehensive performance monitoring for Lambda cold starts, execution times,
and optimization effectiveness. Integrates with CloudWatch for metrics and alerting.
"""

import json
import boto3
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics."""
    COLD_START = "cold_start"
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    COST = "cost"


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    function_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    dimensions: Dict[str, str]
    unit: str = "Count"


@dataclass
class ColdStartEvent:
    """Cold start event details."""
    function_name: str
    timestamp: datetime
    init_duration: float
    first_request_duration: float
    memory_allocated: int
    runtime: str
    optimization_enabled: bool


@dataclass
class ExecutionMetrics:
    """Execution performance metrics."""
    function_name: str
    timestamp: datetime
    duration: float
    billed_duration: float
    memory_used: int
    memory_allocated: int
    is_cold_start: bool
    error: Optional[str] = None


class PerformanceCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.metrics_buffer = deque(maxlen=buffer_size)
        self.cold_starts = deque(maxlen=buffer_size)
        self.executions = deque(maxlen=buffer_size)
        
        # Thread-safe access
        self._lock = threading.Lock()
        
        # Aggregated statistics
        self.function_stats = defaultdict(lambda: {
            'total_invocations': 0,
            'cold_starts': 0,
            'total_duration': 0.0,
            'total_memory_used': 0,
            'errors': 0,
            'last_updated': datetime.utcnow()
        })
    
    def record_cold_start(self, event: ColdStartEvent):
        """Record a cold start event."""
        with self._lock:
            self.cold_starts.append(event)
            
            # Update function stats
            stats = self.function_stats[event.function_name]
            stats['cold_starts'] += 1
            stats['last_updated'] = datetime.utcnow()
            
            # Create metric
            metric = PerformanceMetric(
                function_name=event.function_name,
                metric_type=MetricType.COLD_START,
                value=1.0,
                timestamp=event.timestamp,
                dimensions={
                    'FunctionName': event.function_name,
                    'Runtime': event.runtime,
                    'OptimizationEnabled': str(event.optimization_enabled)
                },
                unit="Count"
            )
            self.metrics_buffer.append(metric)
    
    def record_execution(self, metrics: ExecutionMetrics):
        """Record execution metrics."""
        with self._lock:
            self.executions.append(metrics)
            
            # Update function stats
            stats = self.function_stats[metrics.function_name]
            stats['total_invocations'] += 1
            stats['total_duration'] += metrics.duration
            stats['total_memory_used'] += metrics.memory_used
            
            if metrics.error:
                stats['errors'] += 1
            
            stats['last_updated'] = datetime.utcnow()
            
            # Create metrics
            execution_metric = PerformanceMetric(
                function_name=metrics.function_name,
                metric_type=MetricType.EXECUTION_TIME,
                value=metrics.duration,
                timestamp=metrics.timestamp,
                dimensions={
                    'FunctionName': metrics.function_name,
                    'ColdStart': str(metrics.is_cold_start)
                },
                unit="Milliseconds"
            )
            self.metrics_buffer.append(execution_metric)
            
            memory_metric = PerformanceMetric(
                function_name=metrics.function_name,
                metric_type=MetricType.MEMORY_USAGE,
                value=metrics.memory_used,
                timestamp=metrics.timestamp,
                dimensions={
                    'FunctionName': metrics.function_name
                },
                unit="Megabytes"
            )
            self.metrics_buffer.append(memory_metric)
    
    def get_function_statistics(self, function_name: str, 
                              time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get statistics for a specific function."""
        cutoff_time = datetime.utcnow() - time_window
        
        with self._lock:
            # Filter recent executions
            recent_executions = [
                exec_metrics for exec_metrics in self.executions
                if (exec_metrics.function_name == function_name and 
                    exec_metrics.timestamp >= cutoff_time)
            ]
            
            recent_cold_starts = [
                cold_start for cold_start in self.cold_starts
                if (cold_start.function_name == function_name and 
                    cold_start.timestamp >= cutoff_time)
            ]
            
            if not recent_executions:
                return {'function_name': function_name, 'no_data': True}
            
            # Calculate statistics
            durations = [exec_metrics.duration for exec_metrics in recent_executions]
            memory_usage = [exec_metrics.memory_used for exec_metrics in recent_executions]
            
            cold_start_count = len(recent_cold_starts)
            total_invocations = len(recent_executions)
            error_count = sum(1 for exec_metrics in recent_executions if exec_metrics.error)
            
            return {
                'function_name': function_name,
                'time_window_hours': time_window.total_seconds() / 3600,
                'total_invocations': total_invocations,
                'cold_starts': cold_start_count,
                'cold_start_percentage': (cold_start_count / total_invocations) * 100 if total_invocations > 0 else 0,
                'error_count': error_count,
                'error_rate': (error_count / total_invocations) * 100 if total_invocations > 0 else 0,
                'execution_time': {
                    'average': statistics.mean(durations),
                    'median': statistics.median(durations),
                    'p95': statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations),
                    'p99': statistics.quantiles(durations, n=100)[98] if len(durations) >= 100 else max(durations),
                    'min': min(durations),
                    'max': max(durations)
                },
                'memory_usage': {
                    'average': statistics.mean(memory_usage),
                    'median': statistics.median(memory_usage),
                    'max': max(memory_usage)
                },
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_optimization_effectiveness(self) -> Dict[str, Any]:
        """Analyze optimization effectiveness across all functions."""
        with self._lock:
            # Group executions by optimization status
            optimized_executions = []
            unoptimized_executions = []
            
            for exec_metrics in self.executions:
                # Check if function uses optimization (based on function name pattern)
                is_optimized = any(
                    opt_func in exec_metrics.function_name 
                    for opt_func in ['healthcare-agent-router', 'healthcare-illness-monitor', 
                                   'healthcare-mental-health', 'healthcare-safety-guardian',
                                   'healthcare-wellness-coach']
                )
                
                if is_optimized:
                    optimized_executions.append(exec_metrics)
                else:
                    unoptimized_executions.append(exec_metrics)
            
            # Calculate comparison metrics
            def calculate_metrics(executions):
                if not executions:
                    return None
                
                durations = [e.duration for e in executions]
                cold_starts = sum(1 for e in executions if e.is_cold_start)
                errors = sum(1 for e in executions if e.error)
                
                return {
                    'total_invocations': len(executions),
                    'cold_starts': cold_starts,
                    'cold_start_percentage': (cold_starts / len(executions)) * 100,
                    'error_rate': (errors / len(executions)) * 100,
                    'avg_duration': statistics.mean(durations),
                    'p95_duration': statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations)
                }
            
            optimized_metrics = calculate_metrics(optimized_executions)
            unoptimized_metrics = calculate_metrics(unoptimized_executions)
            
            # Calculate improvement percentages
            improvements = {}
            if optimized_metrics and unoptimized_metrics:
                improvements = {
                    'cold_start_reduction': (
                        (unoptimized_metrics['cold_start_percentage'] - optimized_metrics['cold_start_percentage']) /
                        unoptimized_metrics['cold_start_percentage'] * 100
                    ) if unoptimized_metrics['cold_start_percentage'] > 0 else 0,
                    'duration_improvement': (
                        (unoptimized_metrics['avg_duration'] - optimized_metrics['avg_duration']) /
                        unoptimized_metrics['avg_duration'] * 100
                    ) if unoptimized_metrics['avg_duration'] > 0 else 0,
                    'error_rate_improvement': (
                        (unoptimized_metrics['error_rate'] - optimized_metrics['error_rate']) /
                        unoptimized_metrics['error_rate'] * 100
                    ) if unoptimized_metrics['error_rate'] > 0 else 0
                }
            
            return {
                'optimized_functions': optimized_metrics,
                'unoptimized_functions': unoptimized_metrics,
                'improvements': improvements,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }


class CloudWatchPublisher:
    """Publishes performance metrics to CloudWatch."""
    
    def __init__(self, namespace: str = "HealthcareAI/Lambda"):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
        self.batch_size = 20  # CloudWatch limit
    
    def publish_metrics(self, metrics: List[PerformanceMetric]) -> bool:
        """Publish metrics to CloudWatch in batches."""
        try:
            # Process metrics in batches
            for i in range(0, len(metrics), self.batch_size):
                batch = metrics[i:i + self.batch_size]
                metric_data = []
                
                for metric in batch:
                    metric_data.append({
                        'MetricName': metric.metric_type.value,
                        'Dimensions': [
                            {'Name': key, 'Value': value}
                            for key, value in metric.dimensions.items()
                        ],
                        'Value': metric.value,
                        'Unit': metric.unit,
                        'Timestamp': metric.timestamp
                    })
                
                # Publish batch
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=metric_data
                )
            
            logger.info(f"Published {len(metrics)} metrics to CloudWatch")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish metrics to CloudWatch: {e}")
            return False
    
    def create_dashboard(self, dashboard_name: str, function_names: List[str]) -> bool:
        """Create CloudWatch dashboard for Lambda performance monitoring."""
        try:
            # Dashboard configuration
            dashboard_body = {
                "widgets": [
                    {
                        "type": "metric",
                        "x": 0, "y": 0, "width": 12, "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "cold_start", "FunctionName", func_name]
                                for func_name in function_names
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": "us-east-1",
                            "title": "Cold Starts by Function"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12, "y": 0, "width": 12, "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "execution_time", "FunctionName", func_name]
                                for func_name in function_names
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": "us-east-1",
                            "title": "Average Execution Time"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0, "y": 6, "width": 12, "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "memory_usage", "FunctionName", func_name]
                                for func_name in function_names
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": "us-east-1",
                            "title": "Memory Usage"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12, "y": 6, "width": 12, "height": 6,
                        "properties": {
                            "metrics": [
                                ["AWS/Lambda", "Errors", "FunctionName", func_name]
                                for func_name in function_names
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": "us-east-1",
                            "title": "Error Count"
                        }
                    }
                ]
            }
            
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            logger.info(f"Created CloudWatch dashboard: {dashboard_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create CloudWatch dashboard: {e}")
            return False


class PerformanceMonitor:
    """Main performance monitoring coordinator."""
    
    def __init__(self, namespace: str = "HealthcareAI/Lambda"):
        self.collector = PerformanceCollector()
        self.publisher = CloudWatchPublisher(namespace)
        
        # Monitoring configuration
        self.publish_interval = 60  # seconds
        self.last_publish = time.time()
        
        # Performance thresholds
        self.thresholds = {
            'cold_start_percentage': 20.0,  # Alert if > 20% cold starts
            'avg_duration': 5000.0,         # Alert if > 5 seconds average
            'error_rate': 5.0,              # Alert if > 5% error rate
            'p95_duration': 10000.0         # Alert if P95 > 10 seconds
        }
    
    def record_lambda_execution(self, function_name: str, duration: float, 
                              memory_used: int, memory_allocated: int,
                              is_cold_start: bool, error: str = None):
        """Record Lambda execution metrics."""
        metrics = ExecutionMetrics(
            function_name=function_name,
            timestamp=datetime.utcnow(),
            duration=duration,
            billed_duration=duration,  # Simplified
            memory_used=memory_used,
            memory_allocated=memory_allocated,
            is_cold_start=is_cold_start,
            error=error
        )
        
        self.collector.record_execution(metrics)
        
        # Record cold start if applicable
        if is_cold_start:
            cold_start_event = ColdStartEvent(
                function_name=function_name,
                timestamp=datetime.utcnow(),
                init_duration=duration * 0.3,  # Estimate
                first_request_duration=duration,
                memory_allocated=memory_allocated,
                runtime="python3.9",
                optimization_enabled=True  # Assume optimized functions
            )
            self.collector.record_cold_start(cold_start_event)
        
        # Publish metrics periodically
        if time.time() - self.last_publish > self.publish_interval:
            self.publish_pending_metrics()
    
    def publish_pending_metrics(self):
        """Publish pending metrics to CloudWatch."""
        with self.collector._lock:
            metrics_to_publish = list(self.collector.metrics_buffer)
            self.collector.metrics_buffer.clear()
        
        if metrics_to_publish:
            success = self.publisher.publish_metrics(metrics_to_publish)
            if success:
                self.last_publish = time.time()
    
    def get_performance_report(self, function_name: str = None) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        if function_name:
            return self.collector.get_function_statistics(function_name)
        else:
            # Get report for all functions
            all_functions = set(
                exec_metrics.function_name 
                for exec_metrics in self.collector.executions
            )
            
            reports = {}
            for func_name in all_functions:
                reports[func_name] = self.collector.get_function_statistics(func_name)
            
            # Add optimization effectiveness analysis
            reports['optimization_analysis'] = self.collector.get_optimization_effectiveness()
            
            return reports
    
    def check_performance_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance threshold violations."""
        alerts = []
        
        # Get recent statistics for all functions
        all_functions = set(
            exec_metrics.function_name 
            for exec_metrics in self.collector.executions
        )
        
        for function_name in all_functions:
            stats = self.collector.get_function_statistics(function_name)
            
            if stats.get('no_data'):
                continue
            
            # Check thresholds
            if stats['cold_start_percentage'] > self.thresholds['cold_start_percentage']:
                alerts.append({
                    'type': 'high_cold_start_rate',
                    'function_name': function_name,
                    'value': stats['cold_start_percentage'],
                    'threshold': self.thresholds['cold_start_percentage'],
                    'severity': 'warning'
                })
            
            if stats['execution_time']['average'] > self.thresholds['avg_duration']:
                alerts.append({
                    'type': 'high_average_duration',
                    'function_name': function_name,
                    'value': stats['execution_time']['average'],
                    'threshold': self.thresholds['avg_duration'],
                    'severity': 'warning'
                })
            
            if stats['error_rate'] > self.thresholds['error_rate']:
                alerts.append({
                    'type': 'high_error_rate',
                    'function_name': function_name,
                    'value': stats['error_rate'],
                    'threshold': self.thresholds['error_rate'],
                    'severity': 'critical'
                })
        
        return alerts
    
    def setup_monitoring_dashboard(self, function_names: List[str]) -> bool:
        """Set up CloudWatch dashboard for monitoring."""
        dashboard_name = "HealthcareAI-Lambda-Performance"
        return self.publisher.create_dashboard(dashboard_name, function_names)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Decorator for automatic performance monitoring
def monitor_performance(func):
    """Decorator to automatically monitor Lambda function performance."""
    def wrapper(event, context):
        start_time = time.time()
        is_cold_start = not hasattr(context, '_performance_monitor_initialized')
        error = None
        
        try:
            # Mark as initialized to detect future cold starts
            if is_cold_start:
                context._performance_monitor_initialized = True
            
            # Execute function
            result = func(event, context)
            
            return result
            
        except Exception as e:
            error = str(e)
            raise
            
        finally:
            # Record performance metrics
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            performance_monitor.record_lambda_execution(
                function_name=context.function_name,
                duration=duration,
                memory_used=context.memory_limit_in_mb,  # Simplified
                memory_allocated=context.memory_limit_in_mb,
                is_cold_start=is_cold_start,
                error=error
            )
    
    return wrapper