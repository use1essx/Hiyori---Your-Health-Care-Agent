"""
Lambda Cold Start Performance Optimizer
======================================

Comprehensive optimization system for minimizing Lambda cold start times and improving performance.
Implements warming strategies, connection pooling, lazy loading, and optimal configuration management.

Requirements: 9.4, 7.2, 4.5
"""

import json
import boto3
import logging
import asyncio
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import os
import sys
from functools import wraps, lru_cache
import weakref

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Optimization levels for different Lambda functions."""
    MINIMAL = "minimal"      # Basic optimizations only
    STANDARD = "standard"    # Balanced optimization
    AGGRESSIVE = "aggressive" # Maximum optimization for critical functions


@dataclass
class LambdaConfig:
    """Lambda function configuration for optimization."""
    function_name: str
    memory_mb: int
    timeout_seconds: int
    optimization_level: OptimizationLevel
    warm_pool_size: int
    connection_pool_size: int
    enable_lazy_loading: bool
    critical_dependencies: List[str]
    optional_dependencies: List[str]


class ConnectionPool:
    """Thread-safe connection pool for AWS services."""
    
    def __init__(self, service_name: str, max_connections: int = 10, 
                 region_name: str = None, **client_kwargs):
        self.service_name = service_name
        self.max_connections = max_connections
        self.region_name = region_name or os.environ.get('AWS_REGION', 'us-east-1')
        self.client_kwargs = client_kwargs
        
        self._pool = []
        self._pool_lock = threading.Lock()
        self._created_connections = 0
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
        # Pre-create initial connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool with initial connections."""
        initial_size = min(3, self.max_connections)  # Start with 3 connections
        
        for _ in range(initial_size):
            try:
                client = self._create_client()
                self._pool.append({
                    'client': client,
                    'created_at': time.time(),
                    'last_used': time.time(),
                    'in_use': False
                })
                self._created_connections += 1
            except Exception as e:
                logger.warning(f"Failed to pre-create {self.service_name} client: {e}")
    
    def _create_client(self):
        """Create a new AWS service client."""
        return boto3.client(
            self.service_name,
            region_name=self.region_name,
            **self.client_kwargs
        )
    
    def get_client(self):
        """Get a client from the pool or create a new one."""
        with self._pool_lock:
            # Clean up old connections periodically
            if time.time() - self._last_cleanup > self._cleanup_interval:
                self._cleanup_old_connections()
            
            # Find available connection
            for conn_info in self._pool:
                if not conn_info['in_use']:
                    conn_info['in_use'] = True
                    conn_info['last_used'] = time.time()
                    return PooledClient(conn_info['client'], self, conn_info)
            
            # Create new connection if under limit
            if self._created_connections < self.max_connections:
                try:
                    client = self._create_client()
                    conn_info = {
                        'client': client,
                        'created_at': time.time(),
                        'last_used': time.time(),
                        'in_use': True
                    }
                    self._pool.append(conn_info)
                    self._created_connections += 1
                    return PooledClient(client, self, conn_info)
                except Exception as e:
                    logger.error(f"Failed to create new {self.service_name} client: {e}")
            
            # Wait for available connection (with timeout)
            return self._wait_for_available_client()
    
    def _wait_for_available_client(self, timeout: float = 5.0):
        """Wait for an available client with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            time.sleep(0.1)  # Short sleep
            
            with self._pool_lock:
                for conn_info in self._pool:
                    if not conn_info['in_use']:
                        conn_info['in_use'] = True
                        conn_info['last_used'] = time.time()
                        return PooledClient(conn_info['client'], self, conn_info)
        
        # Timeout reached, create emergency client
        logger.warning(f"Connection pool timeout for {self.service_name}, creating emergency client")
        return self._create_client()
    
    def return_client(self, conn_info: Dict[str, Any]):
        """Return a client to the pool."""
        with self._pool_lock:
            conn_info['in_use'] = False
    
    def _cleanup_old_connections(self):
        """Clean up old unused connections."""
        current_time = time.time()
        max_age = 1800  # 30 minutes
        
        connections_to_remove = []
        
        for i, conn_info in enumerate(self._pool):
            if (not conn_info['in_use'] and 
                current_time - conn_info['last_used'] > max_age):
                connections_to_remove.append(i)
        
        # Remove old connections (keep at least 1)
        if len(self._pool) - len(connections_to_remove) >= 1:
            for i in reversed(connections_to_remove):
                self._pool.pop(i)
                self._created_connections -= 1
        
        self._last_cleanup = current_time
        
        if connections_to_remove:
            logger.info(f"Cleaned up {len(connections_to_remove)} old {self.service_name} connections")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._pool_lock:
            in_use_count = sum(1 for conn in self._pool if conn['in_use'])
            
            return {
                'service_name': self.service_name,
                'total_connections': len(self._pool),
                'in_use_connections': in_use_count,
                'available_connections': len(self._pool) - in_use_count,
                'max_connections': self.max_connections,
                'created_connections': self._created_connections
            }


class PooledClient:
    """Wrapper for pooled AWS clients that automatically returns to pool."""
    
    def __init__(self, client, pool: ConnectionPool, conn_info: Dict[str, Any]):
        self._client = client
        self._pool = pool
        self._conn_info = conn_info
        self._returned = False
    
    def __getattr__(self, name):
        """Delegate all method calls to the underlying client."""
        return getattr(self._client, name)
    
    def __enter__(self):
        return self._client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.return_to_pool()
    
    def return_to_pool(self):
        """Return the client to the pool."""
        if not self._returned:
            self._pool.return_client(self._conn_info)
            self._returned = True
    
    def __del__(self):
        """Ensure client is returned to pool on garbage collection."""
        if not self._returned:
            try:
                self.return_to_pool()
            except:
                pass  # Ignore errors during cleanup


class LazyLoader:
    """Lazy loading system for non-critical components."""
    
    def __init__(self):
        self._loaded_modules = {}
        self._loading_lock = threading.Lock()
        self._load_times = {}
    
    def register_lazy_import(self, module_name: str, import_func: Callable, 
                           is_critical: bool = False):
        """Register a module for lazy loading."""
        self._loaded_modules[module_name] = {
            'import_func': import_func,
            'module': None,
            'is_critical': is_critical,
            'load_time': None,
            'error': None
        }
    
    def get_module(self, module_name: str):
        """Get a lazily loaded module."""
        if module_name not in self._loaded_modules:
            raise ValueError(f"Module {module_name} not registered for lazy loading")
        
        module_info = self._loaded_modules[module_name]
        
        # Return cached module if already loaded
        if module_info['module'] is not None:
            return module_info['module']
        
        # Load module with thread safety
        with self._loading_lock:
            # Double-check after acquiring lock
            if module_info['module'] is not None:
                return module_info['module']
            
            try:
                start_time = time.time()
                module = module_info['import_func']()
                load_time = time.time() - start_time
                
                module_info['module'] = module
                module_info['load_time'] = load_time
                
                logger.info(f"Lazy loaded {module_name} in {load_time:.3f}s")
                return module
                
            except Exception as e:
                module_info['error'] = str(e)
                logger.error(f"Failed to lazy load {module_name}: {e}")
                
                if module_info['is_critical']:
                    raise
                else:
                    return None
    
    def preload_critical_modules(self):
        """Preload all critical modules."""
        critical_modules = [
            name for name, info in self._loaded_modules.items() 
            if info['is_critical'] and info['module'] is None
        ]
        
        for module_name in critical_modules:
            try:
                self.get_module(module_name)
            except Exception as e:
                logger.error(f"Failed to preload critical module {module_name}: {e}")
    
    def get_load_stats(self) -> Dict[str, Any]:
        """Get lazy loading statistics."""
        stats = {
            'total_registered': len(self._loaded_modules),
            'loaded_modules': 0,
            'failed_modules': 0,
            'total_load_time': 0.0,
            'modules': {}
        }
        
        for name, info in self._loaded_modules.items():
            module_stats = {
                'loaded': info['module'] is not None,
                'is_critical': info['is_critical'],
                'load_time': info['load_time'],
                'error': info['error']
            }
            
            if info['module'] is not None:
                stats['loaded_modules'] += 1
                if info['load_time']:
                    stats['total_load_time'] += info['load_time']
            elif info['error']:
                stats['failed_modules'] += 1
            
            stats['modules'][name] = module_stats
        
        return stats


class LambdaWarmer:
    """Lambda warming system to reduce cold starts."""
    
    def __init__(self, function_configs: List[LambdaConfig]):
        self.function_configs = {config.function_name: config for config in function_configs}
        self.lambda_client = boto3.client('lambda')
        self.warming_active = False
        self.warming_stats = {}
        
        # EventBridge for scheduled warming
        self.events_client = boto3.client('events')
    
    def setup_warming_schedule(self, schedule_expression: str = "rate(5 minutes)"):
        """Set up EventBridge rule for scheduled Lambda warming."""
        try:
            rule_name = f"lambda-warmer-{os.environ.get('ENVIRONMENT', 'dev')}"
            
            # Create EventBridge rule
            self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=schedule_expression,
                Description="Scheduled Lambda warming to reduce cold starts",
                State='ENABLED'
            )
            
            # Add targets (this would typically be done via CloudFormation)
            logger.info(f"Created warming schedule: {rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup warming schedule: {e}")
    
    def warm_function(self, function_name: str, concurrent_executions: int = 1) -> Dict[str, Any]:
        """Warm a specific Lambda function."""
        if function_name not in self.function_configs:
            logger.warning(f"No configuration found for function {function_name}")
            return {'success': False, 'error': 'No configuration found'}
        
        config = self.function_configs[function_name]
        results = []
        
        try:
            # Invoke function multiple times concurrently
            with ThreadPoolExecutor(max_workers=min(concurrent_executions, 10)) as executor:
                futures = []
                
                for i in range(concurrent_executions):
                    future = executor.submit(self._invoke_warming_request, function_name, i)
                    futures.append(future)
                
                # Collect results
                for future in futures:
                    try:
                        result = future.result(timeout=30)
                        results.append(result)
                    except Exception as e:
                        results.append({'success': False, 'error': str(e)})
            
            # Update warming stats
            success_count = sum(1 for r in results if r.get('success', False))
            self.warming_stats[function_name] = {
                'last_warmed': datetime.utcnow().isoformat(),
                'concurrent_executions': concurrent_executions,
                'successful_invocations': success_count,
                'failed_invocations': len(results) - success_count
            }
            
            return {
                'success': success_count > 0,
                'function_name': function_name,
                'concurrent_executions': concurrent_executions,
                'successful_invocations': success_count,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error warming function {function_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _invoke_warming_request(self, function_name: str, invocation_id: int) -> Dict[str, Any]:
        """Invoke a single warming request."""
        try:
            warming_payload = {
                'warming': True,
                'invocation_id': invocation_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            start_time = time.time()
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(warming_payload)
            )
            
            duration = time.time() - start_time
            
            # Check if invocation was successful
            if response['StatusCode'] == 200:
                return {
                    'success': True,
                    'invocation_id': invocation_id,
                    'duration': duration,
                    'status_code': response['StatusCode']
                }
            else:
                return {
                    'success': False,
                    'invocation_id': invocation_id,
                    'duration': duration,
                    'status_code': response['StatusCode'],
                    'error': 'Non-200 status code'
                }
                
        except Exception as e:
            return {
                'success': False,
                'invocation_id': invocation_id,
                'error': str(e)
            }
    
    def warm_all_functions(self) -> Dict[str, Any]:
        """Warm all configured functions."""
        results = {}
        
        for function_name, config in self.function_configs.items():
            result = self.warm_function(function_name, config.warm_pool_size)
            results[function_name] = result
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'functions_warmed': len(results),
            'results': results
        }
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get warming statistics."""
        return {
            'warming_active': self.warming_active,
            'configured_functions': list(self.function_configs.keys()),
            'warming_stats': self.warming_stats,
            'timestamp': datetime.utcnow().isoformat()
        }


class LambdaOptimizer:
    """Main Lambda optimization coordinator."""
    
    def __init__(self, configs: List[LambdaConfig]):
        self.configs = {config.function_name: config for config in configs}
        
        # Initialize components
        self.connection_pools = {}
        self.lazy_loader = LazyLoader()
        self.warmer = LambdaWarmer(configs)
        
        # Performance tracking
        self.performance_metrics = {}
        self.optimization_start_time = time.time()
        
        # Initialize optimization components
        self._setup_connection_pools()
        self._setup_lazy_loading()
    
    def _setup_connection_pools(self):
        """Set up connection pools for AWS services."""
        # Common AWS services used by healthcare agents
        services_config = {
            'bedrock-runtime': {'max_connections': 5},
            'dynamodb': {'max_connections': 8},
            'lambda': {'max_connections': 3},
            'transcribe': {'max_connections': 2},
            'polly': {'max_connections': 2},
            's3': {'max_connections': 3},
            'ssm': {'max_connections': 2}
        }
        
        for service_name, config in services_config.items():
            try:
                pool = ConnectionPool(
                    service_name=service_name,
                    max_connections=config['max_connections']
                )
                self.connection_pools[service_name] = pool
                logger.info(f"Created connection pool for {service_name}")
            except Exception as e:
                logger.error(f"Failed to create connection pool for {service_name}: {e}")
    
    def _setup_lazy_loading(self):
        """Set up lazy loading for non-critical modules."""
        # Register common modules for lazy loading
        lazy_imports = [
            # Non-critical analysis modules
            ('sentiment_analysis', lambda: __import__('textblob'), False),
            ('advanced_nlp', lambda: __import__('spacy'), False),
            ('image_processing', lambda: __import__('PIL'), False),
            
            # Optional integrations
            ('monitoring_tools', lambda: __import__('prometheus_client'), False),
            ('advanced_logging', lambda: __import__('structlog'), False),
            
            # Critical healthcare modules (preload these)
            ('json', lambda: __import__('json'), True),
            ('datetime', lambda: __import__('datetime'), True),
            ('uuid', lambda: __import__('uuid'), True),
        ]
        
        for module_name, import_func, is_critical in lazy_imports:
            try:
                self.lazy_loader.register_lazy_import(module_name, import_func, is_critical)
            except Exception as e:
                logger.warning(f"Failed to register lazy import for {module_name}: {e}")
        
        # Preload critical modules
        self.lazy_loader.preload_critical_modules()
    
    def get_optimized_client(self, service_name: str):
        """Get an optimized AWS client from the connection pool."""
        if service_name in self.connection_pools:
            return self.connection_pools[service_name].get_client()
        else:
            # Fallback to regular client
            logger.warning(f"No connection pool for {service_name}, using regular client")
            return boto3.client(service_name)
    
    def get_lazy_module(self, module_name: str):
        """Get a lazily loaded module."""
        return self.lazy_loader.get_module(module_name)
    
    def optimize_handler(self, handler_func: Callable) -> Callable:
        """Decorator to optimize Lambda handler functions."""
        @wraps(handler_func)
        def optimized_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
            start_time = time.time()
            
            # Check if this is a warming request
            if event.get('warming', False):
                return self._handle_warming_request(event, context)
            
            # Track cold start
            is_cold_start = not hasattr(context, '_lambda_optimizer_initialized')
            if is_cold_start:
                context._lambda_optimizer_initialized = True
                logger.info("Cold start detected, applying optimizations")
            
            try:
                # Execute the original handler
                result = handler_func(event, context)
                
                # Track performance
                execution_time = time.time() - start_time
                self._track_performance(context.function_name, execution_time, is_cold_start)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                self._track_performance(context.function_name, execution_time, is_cold_start, error=str(e))
                raise
        
        return optimized_handler
    
    def _handle_warming_request(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """Handle Lambda warming requests."""
        return {
            'statusCode': 200,
            'body': json.dumps({
                'warming': True,
                'function_name': context.function_name,
                'invocation_id': event.get('invocation_id'),
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'Function warmed successfully'
            })
        }
    
    def _track_performance(self, function_name: str, execution_time: float, 
                          is_cold_start: bool, error: str = None):
        """Track Lambda performance metrics."""
        if function_name not in self.performance_metrics:
            self.performance_metrics[function_name] = {
                'total_invocations': 0,
                'cold_starts': 0,
                'total_execution_time': 0.0,
                'errors': 0,
                'avg_execution_time': 0.0,
                'cold_start_percentage': 0.0
            }
        
        metrics = self.performance_metrics[function_name]
        metrics['total_invocations'] += 1
        metrics['total_execution_time'] += execution_time
        
        if is_cold_start:
            metrics['cold_starts'] += 1
        
        if error:
            metrics['errors'] += 1
        
        # Update calculated metrics
        metrics['avg_execution_time'] = metrics['total_execution_time'] / metrics['total_invocations']
        metrics['cold_start_percentage'] = (metrics['cold_starts'] / metrics['total_invocations']) * 100
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        uptime = time.time() - self.optimization_start_time
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': uptime,
            'configured_functions': list(self.configs.keys()),
            'connection_pools': {
                name: pool.get_stats() 
                for name, pool in self.connection_pools.items()
            },
            'lazy_loading': self.lazy_loader.get_load_stats(),
            'warming': self.warmer.get_warming_stats(),
            'performance_metrics': self.performance_metrics,
            'optimization_summary': {
                'total_functions': len(self.configs),
                'active_connection_pools': len(self.connection_pools),
                'lazy_loaded_modules': len(self.lazy_loader._loaded_modules),
                'total_invocations': sum(
                    metrics['total_invocations'] 
                    for metrics in self.performance_metrics.values()
                ),
                'average_cold_start_percentage': (
                    sum(metrics['cold_start_percentage'] 
                        for metrics in self.performance_metrics.values()) / 
                    max(1, len(self.performance_metrics))
                )
            }
        }
    
    def cleanup(self):
        """Clean up optimization resources."""
        # Clean up connection pools
        for pool in self.connection_pools.values():
            try:
                pool._cleanup_old_connections()
            except Exception as e:
                logger.error(f"Error cleaning up connection pool: {e}")
        
        logger.info("Lambda optimizer cleanup completed")


# Predefined configurations for healthcare agents
HEALTHCARE_LAMBDA_CONFIGS = [
    LambdaConfig(
        function_name="healthcare-agent-router",
        memory_mb=512,
        timeout_seconds=30,
        optimization_level=OptimizationLevel.AGGRESSIVE,
        warm_pool_size=3,
        connection_pool_size=8,
        enable_lazy_loading=True,
        critical_dependencies=["json", "boto3", "datetime"],
        optional_dependencies=["advanced_nlp", "sentiment_analysis"]
    ),
    LambdaConfig(
        function_name="healthcare-illness-monitor",
        memory_mb=1024,
        timeout_seconds=60,
        optimization_level=OptimizationLevel.STANDARD,
        warm_pool_size=2,
        connection_pool_size=6,
        enable_lazy_loading=True,
        critical_dependencies=["json", "boto3", "datetime", "uuid"],
        optional_dependencies=["advanced_nlp", "medical_terminology"]
    ),
    LambdaConfig(
        function_name="healthcare-mental-health",
        memory_mb=1024,
        timeout_seconds=60,
        optimization_level=OptimizationLevel.STANDARD,
        warm_pool_size=2,
        connection_pool_size=6,
        enable_lazy_loading=True,
        critical_dependencies=["json", "boto3", "datetime", "uuid"],
        optional_dependencies=["sentiment_analysis", "emotion_detection"]
    ),
    LambdaConfig(
        function_name="healthcare-safety-guardian",
        memory_mb=512,
        timeout_seconds=30,
        optimization_level=OptimizationLevel.AGGRESSIVE,
        warm_pool_size=3,
        connection_pool_size=5,
        enable_lazy_loading=False,  # Critical function, load everything
        critical_dependencies=["json", "boto3", "datetime", "uuid"],
        optional_dependencies=[]
    ),
    LambdaConfig(
        function_name="healthcare-wellness-coach",
        memory_mb=768,
        timeout_seconds=45,
        optimization_level=OptimizationLevel.STANDARD,
        warm_pool_size=2,
        connection_pool_size=5,
        enable_lazy_loading=True,
        critical_dependencies=["json", "boto3", "datetime", "uuid"],
        optional_dependencies=["fitness_tracking", "nutrition_analysis"]
    ),
    LambdaConfig(
        function_name="healthcare-speech-processor",
        memory_mb=1536,
        timeout_seconds=120,
        optimization_level=OptimizationLevel.STANDARD,
        warm_pool_size=1,
        connection_pool_size=4,
        enable_lazy_loading=True,
        critical_dependencies=["json", "boto3", "datetime"],
        optional_dependencies=["audio_processing", "advanced_transcription"]
    )
]

# Global optimizer instance
lambda_optimizer = LambdaOptimizer(HEALTHCARE_LAMBDA_CONFIGS)

# Convenience decorators
def optimize_lambda_handler(handler_func: Callable) -> Callable:
    """Decorator to optimize any Lambda handler function."""
    return lambda_optimizer.optimize_handler(handler_func)

def get_optimized_bedrock_client():
    """Get optimized Bedrock client from connection pool."""
    return lambda_optimizer.get_optimized_client('bedrock-runtime')

def get_optimized_dynamodb_client():
    """Get optimized DynamoDB client from connection pool."""
    return lambda_optimizer.get_optimized_client('dynamodb')

def get_optimized_lambda_client():
    """Get optimized Lambda client from connection pool."""
    return lambda_optimizer.get_optimized_client('lambda')

def lazy_import(module_name: str):
    """Get a lazily loaded module."""
    return lambda_optimizer.get_lazy_module(module_name)