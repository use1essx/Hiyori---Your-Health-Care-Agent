"""
Lambda Configuration Optimizer
=============================

Automatically determines optimal Lambda memory, timeout, and other configuration settings
based on performance data and cost analysis. Provides recommendations for each healthcare agent.
"""

import json
import boto3
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class OptimizationGoal(Enum):
    """Optimization goals for Lambda configuration."""
    COST = "cost"                    # Minimize cost
    PERFORMANCE = "performance"      # Minimize latency
    BALANCED = "balanced"           # Balance cost and performance
    RELIABILITY = "reliability"     # Maximize reliability


@dataclass
class LambdaPerformanceData:
    """Performance data for a Lambda function."""
    function_name: str
    current_memory: int
    current_timeout: int
    avg_duration: float
    p95_duration: float
    p99_duration: float
    max_duration: float
    avg_memory_used: float
    max_memory_used: float
    cold_start_percentage: float
    error_rate: float
    invocations_per_hour: float
    cost_per_invocation: float


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation for a Lambda function."""
    function_name: str
    current_config: Dict[str, Any]
    recommended_config: Dict[str, Any]
    expected_improvements: Dict[str, float]
    cost_impact: Dict[str, float]
    confidence_score: float
    reasoning: List[str]


class LambdaCostCalculator:
    """Calculate Lambda costs based on configuration and usage patterns."""
    
    # AWS Lambda pricing (as of 2024, us-east-1)
    PRICE_PER_GB_SECOND = 0.0000166667
    PRICE_PER_REQUEST = 0.0000002
    
    # Memory allocation tiers (MB)
    MEMORY_TIERS = [
        128, 256, 512, 768, 1024, 1280, 1536, 1792, 2048, 2304, 2560, 2816, 3072,
        3328, 3584, 3840, 4096, 4352, 4608, 4864, 5120, 5376, 5632, 5888, 6144,
        6400, 6656, 6912, 7168, 7424, 7680, 7936, 8192, 8448, 8704, 8960, 9216,
        9472, 9728, 9984, 10240
    ]
    
    @classmethod
    def calculate_monthly_cost(cls, memory_mb: int, avg_duration_ms: float, 
                             invocations_per_month: int) -> float:
        """Calculate monthly cost for given configuration."""
        # Convert to GB-seconds
        memory_gb = memory_mb / 1024
        duration_seconds = avg_duration_ms / 1000
        gb_seconds = memory_gb * duration_seconds * invocations_per_month
        
        # Calculate costs
        compute_cost = gb_seconds * cls.PRICE_PER_GB_SECOND
        request_cost = invocations_per_month * cls.PRICE_PER_REQUEST
        
        return compute_cost + request_cost
    
    @classmethod
    def find_optimal_memory(cls, performance_data: LambdaPerformanceData,
                          goal: OptimizationGoal = OptimizationGoal.BALANCED) -> Tuple[int, Dict[str, float]]:
        """Find optimal memory allocation based on performance data and goal."""
        current_memory = performance_data.current_memory
        max_memory_used = performance_data.max_memory_used
        avg_duration = performance_data.avg_duration
        invocations_per_month = performance_data.invocations_per_hour * 24 * 30
        
        # Ensure minimum memory requirement
        min_memory = max(128, math.ceil(max_memory_used * 1.2))  # 20% buffer
        
        # Test different memory configurations
        candidates = []
        
        for memory in cls.MEMORY_TIERS:
            if memory < min_memory:
                continue
            
            # Estimate performance improvement with more memory
            memory_ratio = memory / current_memory
            
            # Performance scaling model (diminishing returns)
            if memory_ratio > 1:
                # More memory = faster execution (up to a point)
                performance_improvement = min(1.5, 1 + (memory_ratio - 1) * 0.3)
                estimated_duration = avg_duration / performance_improvement
            else:
                # Less memory = slower execution
                performance_degradation = max(0.5, 1 - (1 - memory_ratio) * 0.5)
                estimated_duration = avg_duration / performance_degradation
            
            # Calculate cost
            monthly_cost = cls.calculate_monthly_cost(
                memory, estimated_duration, invocations_per_month
            )
            
            # Calculate score based on optimization goal
            if goal == OptimizationGoal.COST:
                score = 1 / monthly_cost  # Lower cost = higher score
            elif goal == OptimizationGoal.PERFORMANCE:
                score = 1 / estimated_duration  # Lower duration = higher score
            elif goal == OptimizationGoal.BALANCED:
                # Balance cost and performance
                cost_score = 1 / monthly_cost
                perf_score = 1 / estimated_duration
                score = (cost_score + perf_score) / 2
            else:  # RELIABILITY
                # Favor higher memory for reliability
                reliability_factor = min(2.0, memory / max_memory_used)
                score = reliability_factor / monthly_cost
            
            candidates.append({
                'memory': memory,
                'estimated_duration': estimated_duration,
                'monthly_cost': monthly_cost,
                'score': score
            })
        
        # Select best candidate
        best_candidate = max(candidates, key=lambda x: x['score'])
        
        improvements = {
            'duration_improvement_percent': (
                (avg_duration - best_candidate['estimated_duration']) / avg_duration * 100
            ),
            'cost_change_percent': (
                (best_candidate['monthly_cost'] - 
                 cls.calculate_monthly_cost(current_memory, avg_duration, invocations_per_month)) /
                cls.calculate_monthly_cost(current_memory, avg_duration, invocations_per_month) * 100
            )
        }
        
        return best_candidate['memory'], improvements


class LambdaConfigOptimizer:
    """Main Lambda configuration optimizer."""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.cloudwatch = boto3.client('cloudwatch')
        self.cost_calculator = LambdaCostCalculator()
        
        # Healthcare-specific optimization profiles
        self.agent_profiles = {
            'healthcare-agent-router': {
                'priority': 'performance',  # Fast routing is critical
                'memory_preference': 'moderate',
                'timeout_preference': 'short',
                'cold_start_sensitivity': 'high'
            },
            'healthcare-illness-monitor': {
                'priority': 'balanced',
                'memory_preference': 'high',  # AI processing needs memory
                'timeout_preference': 'moderate',
                'cold_start_sensitivity': 'moderate'
            },
            'healthcare-mental-health': {
                'priority': 'reliability',  # Mental health needs reliability
                'memory_preference': 'high',
                'timeout_preference': 'moderate',
                'cold_start_sensitivity': 'moderate'
            },
            'healthcare-safety-guardian': {
                'priority': 'performance',  # Emergency response needs speed
                'memory_preference': 'moderate',
                'timeout_preference': 'short',
                'cold_start_sensitivity': 'critical'
            },
            'healthcare-wellness-coach': {
                'priority': 'cost',  # Wellness coaching can be cost-optimized
                'memory_preference': 'moderate',
                'timeout_preference': 'moderate',
                'cold_start_sensitivity': 'low'
            },
            'healthcare-speech-processor': {
                'priority': 'performance',  # Speech processing needs resources
                'memory_preference': 'very_high',
                'timeout_preference': 'long',
                'cold_start_sensitivity': 'low'
            }
        }
    
    def collect_performance_data(self, function_name: str, 
                               days_back: int = 7) -> Optional[LambdaPerformanceData]:
        """Collect performance data from CloudWatch metrics."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)
            
            # Get function configuration
            function_config = self.lambda_client.get_function_configuration(
                FunctionName=function_name
            )
            
            current_memory = function_config['MemorySize']
            current_timeout = function_config['Timeout']
            
            # Collect CloudWatch metrics
            metrics_to_collect = [
                ('Duration', 'AWS/Lambda'),
                ('MemoryUtilization', 'AWS/Lambda'),
                ('Errors', 'AWS/Lambda'),
                ('Invocations', 'AWS/Lambda'),
                ('ConcurrentExecutions', 'AWS/Lambda')
            ]
            
            metric_data = {}
            
            for metric_name, namespace in metrics_to_collect:
                try:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace=namespace,
                        MetricName=metric_name,
                        Dimensions=[
                            {'Name': 'FunctionName', 'Value': function_name}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1 hour periods
                        Statistics=['Average', 'Maximum', 'Sum']
                    )
                    
                    if response['Datapoints']:
                        metric_data[metric_name] = response['Datapoints']
                
                except Exception as e:
                    logger.warning(f"Failed to collect {metric_name} for {function_name}: {e}")
            
            # Process collected data
            if not metric_data.get('Duration'):
                logger.warning(f"No duration data found for {function_name}")
                return None
            
            durations = [dp['Average'] for dp in metric_data['Duration']]
            max_durations = [dp['Maximum'] for dp in metric_data['Duration']]
            
            # Calculate memory usage (estimate from memory utilization)
            memory_utilizations = []
            if 'MemoryUtilization' in metric_data:
                memory_utilizations = [dp['Average'] for dp in metric_data['MemoryUtilization']]
            
            avg_memory_used = (
                statistics.mean(memory_utilizations) * current_memory / 100
                if memory_utilizations else current_memory * 0.7  # Estimate
            )
            max_memory_used = (
                max(memory_utilizations) * current_memory / 100
                if memory_utilizations else current_memory * 0.9  # Estimate
            )
            
            # Calculate invocation rate
            invocations = []
            if 'Invocations' in metric_data:
                invocations = [dp['Sum'] for dp in metric_data['Invocations']]
            
            invocations_per_hour = statistics.mean(invocations) if invocations else 0
            
            # Calculate error rate
            errors = []
            if 'Errors' in metric_data:
                errors = [dp['Sum'] for dp in metric_data['Errors']]
            
            total_errors = sum(errors) if errors else 0
            total_invocations = sum(invocations) if invocations else 1
            error_rate = (total_errors / total_invocations) * 100
            
            # Estimate cold start percentage (simplified)
            cold_start_percentage = min(30.0, 100 / max(1, invocations_per_hour))
            
            # Calculate cost per invocation
            cost_per_invocation = self.cost_calculator.calculate_monthly_cost(
                current_memory, statistics.mean(durations), 1
            )
            
            return LambdaPerformanceData(
                function_name=function_name,
                current_memory=current_memory,
                current_timeout=current_timeout,
                avg_duration=statistics.mean(durations),
                p95_duration=statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations),
                p99_duration=statistics.quantiles(durations, n=100)[98] if len(durations) >= 100 else max(durations),
                max_duration=max(max_durations),
                avg_memory_used=avg_memory_used,
                max_memory_used=max_memory_used,
                cold_start_percentage=cold_start_percentage,
                error_rate=error_rate,
                invocations_per_hour=invocations_per_hour,
                cost_per_invocation=cost_per_invocation
            )
            
        except Exception as e:
            logger.error(f"Failed to collect performance data for {function_name}: {e}")
            return None
    
    def generate_recommendations(self, function_name: str) -> Optional[OptimizationRecommendation]:
        """Generate optimization recommendations for a Lambda function."""
        # Collect performance data
        perf_data = self.collect_performance_data(function_name)
        if not perf_data:
            return None
        
        # Get agent profile
        agent_profile = self.agent_profiles.get(function_name, {
            'priority': 'balanced',
            'memory_preference': 'moderate',
            'timeout_preference': 'moderate',
            'cold_start_sensitivity': 'moderate'
        })
        
        # Determine optimization goal
        priority_to_goal = {
            'cost': OptimizationGoal.COST,
            'performance': OptimizationGoal.PERFORMANCE,
            'balanced': OptimizationGoal.BALANCED,
            'reliability': OptimizationGoal.RELIABILITY
        }
        
        optimization_goal = priority_to_goal.get(agent_profile['priority'], OptimizationGoal.BALANCED)
        
        # Find optimal memory
        optimal_memory, memory_improvements = self.cost_calculator.find_optimal_memory(
            perf_data, optimization_goal
        )
        
        # Calculate optimal timeout
        optimal_timeout = self._calculate_optimal_timeout(perf_data, agent_profile)
        
        # Generate recommendations
        current_config = {
            'memory': perf_data.current_memory,
            'timeout': perf_data.current_timeout
        }
        
        recommended_config = {
            'memory': optimal_memory,
            'timeout': optimal_timeout
        }
        
        # Calculate expected improvements
        expected_improvements = {
            'duration_improvement_percent': memory_improvements['duration_improvement_percent'],
            'cost_change_percent': memory_improvements['cost_change_percent'],
            'cold_start_reduction_percent': self._estimate_cold_start_reduction(
                perf_data, optimal_memory
            )
        }
        
        # Calculate cost impact
        current_monthly_cost = self.cost_calculator.calculate_monthly_cost(
            perf_data.current_memory,
            perf_data.avg_duration,
            int(perf_data.invocations_per_hour * 24 * 30)
        )
        
        new_monthly_cost = self.cost_calculator.calculate_monthly_cost(
            optimal_memory,
            perf_data.avg_duration * (1 - memory_improvements['duration_improvement_percent'] / 100),
            int(perf_data.invocations_per_hour * 24 * 30)
        )
        
        cost_impact = {
            'current_monthly_cost': current_monthly_cost,
            'new_monthly_cost': new_monthly_cost,
            'monthly_savings': current_monthly_cost - new_monthly_cost
        }
        
        # Generate reasoning
        reasoning = self._generate_reasoning(perf_data, agent_profile, recommended_config)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(perf_data, agent_profile)
        
        return OptimizationRecommendation(
            function_name=function_name,
            current_config=current_config,
            recommended_config=recommended_config,
            expected_improvements=expected_improvements,
            cost_impact=cost_impact,
            confidence_score=confidence_score,
            reasoning=reasoning
        )
    
    def _calculate_optimal_timeout(self, perf_data: LambdaPerformanceData, 
                                 agent_profile: Dict[str, str]) -> int:
        """Calculate optimal timeout based on performance data and agent profile."""
        # Base timeout on P99 duration with buffer
        base_timeout = math.ceil(perf_data.p99_duration / 1000) + 5  # Convert to seconds, add 5s buffer
        
        # Adjust based on agent profile
        timeout_preferences = {
            'short': 0.8,
            'moderate': 1.0,
            'long': 1.5
        }
        
        multiplier = timeout_preferences.get(agent_profile.get('timeout_preference', 'moderate'), 1.0)
        optimal_timeout = int(base_timeout * multiplier)
        
        # Ensure reasonable bounds
        return max(30, min(900, optimal_timeout))  # 30s to 15min
    
    def _estimate_cold_start_reduction(self, perf_data: LambdaPerformanceData, 
                                     new_memory: int) -> float:
        """Estimate cold start reduction with new memory allocation."""
        if new_memory > perf_data.current_memory:
            # More memory typically reduces cold start time
            memory_ratio = new_memory / perf_data.current_memory
            reduction = min(30.0, (memory_ratio - 1) * 20)  # Up to 30% reduction
            return reduction
        else:
            return 0.0
    
    def _generate_reasoning(self, perf_data: LambdaPerformanceData, 
                          agent_profile: Dict[str, str], 
                          recommended_config: Dict[str, Any]) -> List[str]:
        """Generate human-readable reasoning for recommendations."""
        reasoning = []
        
        # Memory reasoning
        if recommended_config['memory'] > perf_data.current_memory:
            reasoning.append(
                f"Increasing memory from {perf_data.current_memory}MB to {recommended_config['memory']}MB "
                f"will improve performance and may reduce cold starts"
            )
        elif recommended_config['memory'] < perf_data.current_memory:
            reasoning.append(
                f"Reducing memory from {perf_data.current_memory}MB to {recommended_config['memory']}MB "
                f"will reduce costs while maintaining adequate performance"
            )
        
        # Timeout reasoning
        if recommended_config['timeout'] != perf_data.current_timeout:
            reasoning.append(
                f"Adjusting timeout to {recommended_config['timeout']}s based on P99 duration "
                f"({perf_data.p99_duration:.0f}ms) and agent profile"
            )
        
        # Performance-based reasoning
        if perf_data.cold_start_percentage > 20:
            reasoning.append(
                f"High cold start rate ({perf_data.cold_start_percentage:.1f}%) suggests "
                f"need for warming strategy or memory optimization"
            )
        
        if perf_data.error_rate > 5:
            reasoning.append(
                f"Error rate ({perf_data.error_rate:.1f}%) is above threshold, "
                f"consider increasing memory for reliability"
            )
        
        # Agent-specific reasoning
        agent_type = agent_profile.get('priority', 'balanced')
        if agent_type == 'performance':
            reasoning.append("Performance-critical agent: optimizing for speed over cost")
        elif agent_type == 'cost':
            reasoning.append("Cost-sensitive agent: optimizing for minimal cost")
        elif agent_type == 'reliability':
            reasoning.append("Reliability-focused agent: optimizing for error reduction")
        
        return reasoning
    
    def _calculate_confidence_score(self, perf_data: LambdaPerformanceData, 
                                  agent_profile: Dict[str, str]) -> float:
        """Calculate confidence score for recommendations."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence with more data
        if perf_data.invocations_per_hour > 10:
            confidence += 0.2
        
        # Higher confidence with stable performance
        if perf_data.error_rate < 1:
            confidence += 0.1
        
        # Higher confidence with clear optimization opportunity
        memory_utilization = perf_data.avg_memory_used / perf_data.current_memory
        if memory_utilization < 0.5 or memory_utilization > 0.9:
            confidence += 0.2  # Clear over/under allocation
        
        return min(1.0, confidence)
    
    def optimize_all_healthcare_functions(self) -> Dict[str, OptimizationRecommendation]:
        """Generate optimization recommendations for all healthcare functions."""
        recommendations = {}
        
        for function_name in self.agent_profiles.keys():
            try:
                recommendation = self.generate_recommendations(function_name)
                if recommendation:
                    recommendations[function_name] = recommendation
            except Exception as e:
                logger.error(f"Failed to generate recommendations for {function_name}: {e}")
        
        return recommendations
    
    def apply_recommendations(self, recommendations: Dict[str, OptimizationRecommendation],
                           dry_run: bool = True) -> Dict[str, bool]:
        """Apply optimization recommendations to Lambda functions."""
        results = {}
        
        for function_name, recommendation in recommendations.items():
            try:
                if dry_run:
                    logger.info(f"DRY RUN: Would update {function_name} with {recommendation.recommended_config}")
                    results[function_name] = True
                else:
                    # Apply the configuration
                    self.lambda_client.update_function_configuration(
                        FunctionName=function_name,
                        MemorySize=recommendation.recommended_config['memory'],
                        Timeout=recommendation.recommended_config['timeout']
                    )
                    
                    logger.info(f"Updated {function_name} configuration")
                    results[function_name] = True
                    
            except Exception as e:
                logger.error(f"Failed to update {function_name}: {e}")
                results[function_name] = False
        
        return results
    
    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        recommendations = self.optimize_all_healthcare_functions()
        
        # Calculate totals
        total_current_cost = sum(
            rec.cost_impact['current_monthly_cost'] 
            for rec in recommendations.values()
        )
        
        total_new_cost = sum(
            rec.cost_impact['new_monthly_cost'] 
            for rec in recommendations.values()
        )
        
        total_savings = total_current_cost - total_new_cost
        
        # Categorize recommendations
        high_impact = [
            name for name, rec in recommendations.items()
            if abs(rec.cost_impact['monthly_savings']) > 10 or
               abs(rec.expected_improvements['duration_improvement_percent']) > 20
        ]
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_functions_analyzed': len(recommendations),
                'total_current_monthly_cost': total_current_cost,
                'total_optimized_monthly_cost': total_new_cost,
                'total_monthly_savings': total_savings,
                'high_impact_functions': high_impact
            },
            'recommendations': {
                name: asdict(rec) for name, rec in recommendations.items()
            },
            'optimization_priorities': [
                {
                    'function_name': name,
                    'priority_score': (
                        abs(rec.cost_impact['monthly_savings']) * 0.5 +
                        abs(rec.expected_improvements['duration_improvement_percent']) * 0.3 +
                        rec.confidence_score * 0.2
                    )
                }
                for name, rec in recommendations.items()
            ]
        }


# Global optimizer instance
lambda_config_optimizer = LambdaConfigOptimizer()

def optimize_lambda_configurations(dry_run: bool = True) -> Dict[str, Any]:
    """Convenience function to optimize all Lambda configurations."""
    return lambda_config_optimizer.generate_optimization_report()

def get_function_recommendations(function_name: str) -> Optional[OptimizationRecommendation]:
    """Get optimization recommendations for a specific function."""
    return lambda_config_optimizer.generate_recommendations(function_name)