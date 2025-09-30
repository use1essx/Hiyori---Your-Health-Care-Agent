"""
AWS Cost Monitoring and Optimization
====================================

Monitors and optimizes AWS costs across all healthcare AI services.
"""

import json
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CostThreshold(Enum):
    """Cost alert thresholds."""
    LOW = 10.0      # $10 daily
    MEDIUM = 50.0   # $50 daily  
    HIGH = 100.0    # $100 daily
    CRITICAL = 200.0 # $200 daily


@dataclass
class CostAlert:
    """Cost alert information."""
    service: str
    current_cost: float
    threshold: float
    percentage: float
    timestamp: datetime
    recommendations: List[str]


class CostMonitor:
    """Monitors AWS costs and provides optimization recommendations."""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.ce = boto3.client('ce')  # Cost Explorer
        self.sns = boto3.client('sns')
        
        # Service cost tracking
        self.service_costs = {}
        self.daily_budgets = {
            'bedrock': 50.0,
            'lambda': 20.0,
            'dynamodb': 15.0,
            's3': 10.0,
            'cloudfront': 5.0,
            'transcribe': 10.0,
            'polly': 5.0
        }
    
    def get_current_costs(self, days: int = 1) -> Dict[str, float]:
        """Get current costs for all services."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        try:
            response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ]
            )
            
            costs = {}
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    costs[service.lower()] = costs.get(service.lower(), 0) + cost
            
            return costs
            
        except Exception as e:
            logger.error(f"Error getting costs: {e}")
            return {}
    
    def check_cost_thresholds(self) -> List[CostAlert]:
        """Check if any services exceed cost thresholds."""
        current_costs = self.get_current_costs()
        alerts = []
        
        for service, budget in self.daily_budgets.items():
            current_cost = current_costs.get(service, 0)
            percentage = (current_cost / budget) * 100 if budget > 0 else 0
            
            if percentage >= 80:  # Alert at 80% of budget
                threshold = CostThreshold.CRITICAL if percentage >= 150 else CostThreshold.HIGH
                
                recommendations = self._get_cost_recommendations(service, current_cost, budget)
                
                alert = CostAlert(
                    service=service,
                    current_cost=current_cost,
                    threshold=budget,
                    percentage=percentage,
                    timestamp=datetime.utcnow(),
                    recommendations=recommendations
                )
                alerts.append(alert)
        
        return alerts
    
    def _get_cost_recommendations(self, service: str, current_cost: float, budget: float) -> List[str]:
        """Get cost optimization recommendations for specific service."""
        recommendations = []
        
        if service == 'bedrock':
            recommendations.extend([
                "Consider using faster models for simple queries",
                "Implement request caching to reduce API calls",
                "Optimize prompt length to reduce token usage",
                "Use batch processing for multiple requests"
            ])
        
        elif service == 'lambda':
            recommendations.extend([
                "Optimize memory allocation for functions",
                "Reduce cold start times with provisioned concurrency",
                "Implement connection pooling for database connections",
                "Consider using Lambda layers for shared dependencies"
            ])
        
        elif service == 'dynamodb':
            recommendations.extend([
                "Review and optimize query patterns",
                "Consider using DynamoDB Accelerator (DAX) for caching",
                "Implement proper TTL for automatic data cleanup",
                "Use on-demand billing for unpredictable workloads"
            ])
        
        elif service == 's3':
            recommendations.extend([
                "Implement lifecycle policies for old data",
                "Use S3 Intelligent Tiering for automatic cost optimization",
                "Compress files before storage",
                "Review and delete unused objects"
            ])
        
        elif service == 'cloudfront':
            recommendations.extend([
                "Optimize cache settings to reduce origin requests",
                "Use appropriate price class for your audience",
                "Implement proper cache headers",
                "Consider using CloudFront Functions for edge processing"
            ])
        
        return recommendations
    
    def send_cost_alert(self, alert: CostAlert, topic_arn: str):
        """Send cost alert via SNS."""
        try:
            message = {
                "alert_type": "cost_threshold_exceeded",
                "service": alert.service,
                "current_cost": alert.current_cost,
                "budget": alert.threshold,
                "percentage": alert.percentage,
                "recommendations": alert.recommendations,
                "timestamp": alert.timestamp.isoformat()
            }
            
            subject = f"Cost Alert: {alert.service} at {alert.percentage:.1f}% of budget"
            
            self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message, indent=2),
                Subject=subject
            )
            
            logger.info(f"Cost alert sent for {alert.service}")
            
        except Exception as e:
            logger.error(f"Failed to send cost alert: {e}")
    
    def get_cost_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive cost optimization report."""
        current_costs = self.get_current_costs()
        weekly_costs = self.get_current_costs(days=7)
        monthly_costs = self.get_current_costs(days=30)
        
        total_daily = sum(current_costs.values())
        total_weekly = sum(weekly_costs.values())
        total_monthly = sum(monthly_costs.values())
        
        # Calculate trends
        daily_trend = (total_daily * 7) / max(total_weekly, 0.01) - 1
        weekly_trend = (total_weekly * 4) / max(total_monthly, 0.01) - 1
        
        # Service efficiency analysis
        service_efficiency = {}
        for service, cost in current_costs.items():
            budget = self.daily_budgets.get(service, 0)
            efficiency = (budget - cost) / budget * 100 if budget > 0 else 0
            service_efficiency[service] = {
                'cost': cost,
                'budget': budget,
                'efficiency_percentage': efficiency,
                'status': 'optimal' if efficiency > 20 else 'warning' if efficiency > 0 else 'over_budget'
            }
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'costs': {
                'daily': current_costs,
                'weekly': weekly_costs,
                'monthly': monthly_costs
            },
            'totals': {
                'daily': total_daily,
                'weekly': total_weekly,
                'monthly': total_monthly,
                'projected_monthly': total_daily * 30
            },
            'trends': {
                'daily_vs_weekly': daily_trend,
                'weekly_vs_monthly': weekly_trend
            },
            'service_efficiency': service_efficiency,
            'recommendations': self._get_global_recommendations(current_costs)
        }
    
    def _get_global_recommendations(self, costs: Dict[str, float]) -> List[str]:
        """Get global cost optimization recommendations."""
        recommendations = []
        total_cost = sum(costs.values())
        
        if total_cost > 100:  # High daily costs
            recommendations.extend([
                "Consider implementing request rate limiting",
                "Review and optimize high-cost services",
                "Implement comprehensive caching strategies",
                "Consider reserved capacity for predictable workloads"
            ])
        
        # Service-specific recommendations based on cost distribution
        bedrock_percentage = (costs.get('bedrock', 0) / total_cost) * 100 if total_cost > 0 else 0
        if bedrock_percentage > 60:
            recommendations.append("Bedrock costs are high - consider model optimization")
        
        lambda_percentage = (costs.get('lambda', 0) / total_cost) * 100 if total_cost > 0 else 0
        if lambda_percentage > 30:
            recommendations.append("Lambda costs are high - optimize function performance")
        
        return recommendations
    
    def publish_metrics(self):
        """Publish cost metrics to CloudWatch."""
        costs = self.get_current_costs()
        
        try:
            for service, cost in costs.items():
                self.cloudwatch.put_metric_data(
                    Namespace='HealthcareAI/Costs',
                    MetricData=[
                        {
                            'MetricName': 'DailyCost',
                            'Dimensions': [
                                {
                                    'Name': 'Service',
                                    'Value': service
                                }
                            ],
                            'Value': cost,
                            'Unit': 'None',
                            'Timestamp': datetime.utcnow()
                        }
                    ]
                )
            
            # Total cost metric
            total_cost = sum(costs.values())
            self.cloudwatch.put_metric_data(
                Namespace='HealthcareAI/Costs',
                MetricData=[
                    {
                        'MetricName': 'TotalDailyCost',
                        'Value': total_cost,
                        'Unit': 'None',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
            
            logger.info("Cost metrics published to CloudWatch")
            
        except Exception as e:
            logger.error(f"Failed to publish cost metrics: {e}")


class CostOptimizer:
    """Provides automated cost optimization suggestions and actions."""
    
    def __init__(self):
        self.monitor = CostMonitor()
    
    def optimize_bedrock_usage(self, usage_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize Bedrock model usage based on statistics."""
        recommendations = []
        
        total_requests = usage_stats.get('total_requests', 0)
        model_usage = usage_stats.get('model_usage', {})
        
        # Analyze model distribution
        if total_requests > 0:
            advanced_percentage = (model_usage.get('advanced', 0) / total_requests) * 100
            if advanced_percentage > 30:
                recommendations.append({
                    'type': 'model_optimization',
                    'description': 'High usage of advanced models detected',
                    'suggestion': 'Review if balanced models can handle some advanced requests',
                    'potential_savings': f"Up to {advanced_percentage * 0.5:.1f}% cost reduction"
                })
            
            fast_percentage = (model_usage.get('fast', 0) / total_requests) * 100
            if fast_percentage < 20:
                recommendations.append({
                    'type': 'model_optimization',
                    'description': 'Low usage of fast models',
                    'suggestion': 'Consider using fast models for simple wellness queries',
                    'potential_savings': "Up to 15% cost reduction"
                })
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'analysis': {
                'total_requests': total_requests,
                'model_distribution': model_usage,
                'cost_efficiency': usage_stats.get('average_cost_per_request', 0)
            },
            'recommendations': recommendations
        }
    
    def optimize_lambda_performance(self, function_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize Lambda function performance and costs."""
        recommendations = []
        
        # Analyze cold starts
        cold_start_percentage = function_stats.get('cold_start_percentage', 0)
        if cold_start_percentage > 20:
            recommendations.append({
                'type': 'performance_optimization',
                'description': f'High cold start rate: {cold_start_percentage}%',
                'suggestion': 'Consider provisioned concurrency for frequently used functions',
                'impact': 'Improved response time and user experience'
            })
        
        # Analyze memory usage
        avg_memory_used = function_stats.get('average_memory_used', 0)
        allocated_memory = function_stats.get('allocated_memory', 0)
        
        if allocated_memory > 0:
            memory_efficiency = (avg_memory_used / allocated_memory) * 100
            if memory_efficiency < 60:
                recommendations.append({
                    'type': 'resource_optimization',
                    'description': f'Low memory efficiency: {memory_efficiency:.1f}%',
                    'suggestion': f'Consider reducing memory allocation to {int(avg_memory_used * 1.2)}MB',
                    'potential_savings': "Up to 20% cost reduction"
                })
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'analysis': function_stats,
            'recommendations': recommendations
        }


# Global instances
cost_monitor = CostMonitor()
cost_optimizer = CostOptimizer()