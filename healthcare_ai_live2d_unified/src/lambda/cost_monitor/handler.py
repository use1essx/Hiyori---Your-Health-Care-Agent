"""
Cost Monitoring Lambda Function
==============================

Monitors AWS costs and provides optimization recommendations for the healthcare AI system.
Sends alerts when cost thresholds are exceeded and generates cost reports.
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ce = boto3.client('ce')  # Cost Explorer
cloudwatch = boto3.client('cloudwatch')
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

# Environment variables
COST_ALERT_TOPIC = os.environ.get('COST_ALERT_TOPIC')
SYSTEM_CONFIG_TABLE = os.environ.get('SYSTEM_CONFIG_TABLE')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Initialize DynamoDB table
config_table = dynamodb.Table(SYSTEM_CONFIG_TABLE) if SYSTEM_CONFIG_TABLE else None


@dataclass
class CostAlert:
    """Cost alert information."""
    service: str
    current_cost: float
    threshold: float
    percentage: float
    period: str
    recommendations: List[str]
    severity: str
    timestamp: str


class CostMonitor:
    """Monitors AWS costs and provides optimization recommendations."""
    
    def __init__(self):
        self.ce_client = ce
        self.cloudwatch_client = cloudwatch
        self.sns_client = sns
        self.config_table = config_table
        
        # Cost thresholds by service (daily limits in USD)
        self.service_thresholds = {
            'bedrock': {'warning': 20.0, 'critical': 50.0},
            'lambda': {'warning': 10.0, 'critical': 25.0},
            'dynamodb': {'warning': 8.0, 'critical': 20.0},
            's3': {'warning': 5.0, 'critical': 15.0},
            'cloudfront': {'warning': 3.0, 'critical': 10.0},
            'transcribe': {'warning': 5.0, 'critical': 15.0},
            'polly': {'warning': 3.0, 'critical': 10.0},
            'textract': {'warning': 10.0, 'critical': 25.0},
            'comprehend': {'warning': 5.0, 'critical': 15.0},
            'apigateway': {'warning': 2.0, 'critical': 8.0}
        }
        
        # Total daily threshold
        self.total_daily_threshold = {'warning': 50.0, 'critical': 100.0}
    
    def get_cost_and_usage(self, start_date: datetime, end_date: datetime, 
                          granularity: str = 'DAILY') -> Dict[str, Any]:
        """Get cost and usage data from AWS Cost Explorer."""
        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity=granularity,
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ]
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting cost and usage data: {e}")
            return {}
    
    def parse_cost_data(self, cost_response: Dict[str, Any]) -> Dict[str, float]:
        """Parse cost response into service costs."""
        service_costs = {}
        
        for result in cost_response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service = group['Keys'][0].lower()
                
                # Map AWS service names to our service names
                service_mapping = {
                    'amazon bedrock': 'bedrock',
                    'aws lambda': 'lambda',
                    'amazon dynamodb': 'dynamodb',
                    'amazon simple storage service': 's3',
                    'amazon cloudfront': 'cloudfront',
                    'amazon transcribe': 'transcribe',
                    'amazon polly': 'polly',
                    'amazon textract': 'textract',
                    'amazon comprehend': 'comprehend',
                    'amazon api gateway': 'apigateway'
                }
                
                mapped_service = service_mapping.get(service, service)
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                
                service_costs[mapped_service] = service_costs.get(mapped_service, 0) + cost
        
        return service_costs
    
    def check_cost_thresholds(self, service_costs: Dict[str, float]) -> List[CostAlert]:
        """Check if any services exceed cost thresholds."""
        alerts = []
        current_time = datetime.utcnow().isoformat()
        
        # Check individual service thresholds
        for service, cost in service_costs.items():
            if service not in self.service_thresholds:
                continue
            
            thresholds = self.service_thresholds[service]
            
            # Check critical threshold
            if cost >= thresholds['critical']:
                alert = CostAlert(
                    service=service,
                    current_cost=cost,
                    threshold=thresholds['critical'],
                    percentage=(cost / thresholds['critical']) * 100,
                    period='daily',
                    recommendations=self._get_cost_recommendations(service, cost),
                    severity='critical',
                    timestamp=current_time
                )
                alerts.append(alert)
            
            # Check warning threshold
            elif cost >= thresholds['warning']:
                alert = CostAlert(
                    service=service,
                    current_cost=cost,
                    threshold=thresholds['warning'],
                    percentage=(cost / thresholds['warning']) * 100,
                    period='daily',
                    recommendations=self._get_cost_recommendations(service, cost),
                    severity='warning',
                    timestamp=current_time
                )
                alerts.append(alert)
        
        # Check total cost threshold
        total_cost = sum(service_costs.values())
        
        if total_cost >= self.total_daily_threshold['critical']:
            alert = CostAlert(
                service='total',
                current_cost=total_cost,
                threshold=self.total_daily_threshold['critical'],
                percentage=(total_cost / self.total_daily_threshold['critical']) * 100,
                period='daily',
                recommendations=self._get_global_recommendations(service_costs),
                severity='critical',
                timestamp=current_time
            )
            alerts.append(alert)
        
        elif total_cost >= self.total_daily_threshold['warning']:
            alert = CostAlert(
                service='total',
                current_cost=total_cost,
                threshold=self.total_daily_threshold['warning'],
                percentage=(total_cost / self.total_daily_threshold['warning']) * 100,
                period='daily',
                recommendations=self._get_global_recommendations(service_costs),
                severity='warning',
                timestamp=current_time
            )
            alerts.append(alert)
        
        return alerts
    
    def _get_cost_recommendations(self, service: str, current_cost: float) -> List[str]:
        """Get cost optimization recommendations for specific service."""
        recommendations = []
        
        if service == 'bedrock':
            recommendations.extend([
                "Consider using faster models for simple queries to reduce token costs",
                "Implement request caching to reduce duplicate API calls",
                "Optimize prompt length to minimize token usage",
                "Use batch processing for multiple requests when possible",
                "Review model selection - use balanced models instead of advanced when appropriate"
            ])
        
        elif service == 'lambda':
            recommendations.extend([
                "Optimize memory allocation - reduce if functions are over-provisioned",
                "Implement connection pooling for database connections",
                "Use Lambda layers for shared dependencies to reduce package size",
                "Consider provisioned concurrency only for high-traffic functions",
                "Review function timeout settings to avoid unnecessary charges"
            ])
        
        elif service == 'dynamodb':
            recommendations.extend([
                "Review and optimize query patterns to reduce RCU/WCU usage",
                "Implement proper TTL for automatic data cleanup",
                "Use on-demand billing for unpredictable workloads",
                "Consider DynamoDB Accelerator (DAX) for read-heavy workloads",
                "Archive old data to cheaper storage options"
            ])
        
        elif service == 's3':
            recommendations.extend([
                "Implement lifecycle policies to transition old data to cheaper storage classes",
                "Use S3 Intelligent Tiering for automatic cost optimization",
                "Compress files before storage to reduce storage costs",
                "Review and delete unused objects and incomplete multipart uploads",
                "Use CloudFront for frequently accessed content to reduce S3 requests"
            ])
        
        elif service == 'cloudfront':
            recommendations.extend([
                "Optimize cache settings to reduce origin requests",
                "Use appropriate price class for your geographic audience",
                "Implement proper cache headers to improve hit rates",
                "Consider using CloudFront Functions for edge processing instead of Lambda@Edge"
            ])
        
        elif service in ['transcribe', 'polly', 'textract', 'comprehend']:
            recommendations.extend([
                "Implement caching for frequently processed content",
                "Batch process multiple requests when possible",
                "Use appropriate quality settings - don't over-process",
                "Consider preprocessing to reduce input size",
                "Implement usage quotas to prevent runaway costs"
            ])
        
        return recommendations
    
    def _get_global_recommendations(self, service_costs: Dict[str, float]) -> List[str]:
        """Get global cost optimization recommendations."""
        recommendations = []
        total_cost = sum(service_costs.values())
        
        # Find the most expensive services
        sorted_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)
        top_services = [service for service, cost in sorted_services[:3] if cost > 0]
        
        recommendations.extend([
            f"Focus optimization efforts on top cost drivers: {', '.join(top_services)}",
            "Implement comprehensive monitoring and alerting for all services",
            "Consider reserved capacity for predictable workloads",
            "Review usage patterns and implement auto-scaling where appropriate",
            "Set up budget alerts for proactive cost management"
        ])
        
        # Service-specific recommendations based on cost distribution
        if service_costs.get('bedrock', 0) / total_cost > 0.5:
            recommendations.append("Bedrock costs are >50% of total - prioritize AI model optimization")
        
        if service_costs.get('lambda', 0) / total_cost > 0.3:
            recommendations.append("Lambda costs are >30% of total - focus on function optimization")
        
        return recommendations
    
    def send_cost_alert(self, alert: CostAlert) -> bool:
        """Send cost alert via SNS."""
        if not COST_ALERT_TOPIC:
            logger.warning("Cost alert topic not configured")
            return False
        
        try:
            message = {
                "alert_type": "cost_threshold_exceeded",
                "service": alert.service,
                "current_cost": alert.current_cost,
                "threshold": alert.threshold,
                "percentage": alert.percentage,
                "severity": alert.severity,
                "period": alert.period,
                "recommendations": alert.recommendations,
                "timestamp": alert.timestamp,
                "environment": ENVIRONMENT
            }
            
            subject = f"Cost Alert [{alert.severity.upper()}]: {alert.service} - ${alert.current_cost:.2f}"
            
            self.sns_client.publish(
                TopicArn=COST_ALERT_TOPIC,
                Message=json.dumps(message, indent=2),
                Subject=subject
            )
            
            logger.info(f"Cost alert sent for {alert.service} (${alert.current_cost:.2f})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send cost alert: {e}")
            return False
    
    def publish_cost_metrics(self, service_costs: Dict[str, float]) -> bool:
        """Publish cost metrics to CloudWatch."""
        try:
            metric_data = []
            
            # Individual service metrics
            for service, cost in service_costs.items():
                metric_data.append({
                    'MetricName': 'DailyCost',
                    'Dimensions': [
                        {
                            'Name': 'Service',
                            'Value': service
                        },
                        {
                            'Name': 'Environment',
                            'Value': ENVIRONMENT
                        }
                    ],
                    'Value': cost,
                    'Unit': 'None',
                    'Timestamp': datetime.utcnow()
                })
            
            # Total cost metric
            total_cost = sum(service_costs.values())
            metric_data.append({
                'MetricName': 'TotalDailyCost',
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': ENVIRONMENT
                    }
                ],
                'Value': total_cost,
                'Unit': 'None',
                'Timestamp': datetime.utcnow()
            })
            
            # Publish metrics in batches (CloudWatch limit is 20 per call)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                
                self.cloudwatch_client.put_metric_data(
                    Namespace='HealthcareAI/Costs',
                    MetricData=batch
                )
            
            logger.info(f"Published {len(metric_data)} cost metrics to CloudWatch")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish cost metrics: {e}")
            return False
    
    def generate_cost_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive cost report."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get cost data
        cost_response = self.get_cost_and_usage(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time())
        )
        
        if not cost_response:
            return {'error': 'Failed to retrieve cost data'}
        
        # Parse daily costs
        daily_costs = {}
        total_cost = 0
        
        for result in cost_response.get('ResultsByTime', []):
            date = result['TimePeriod']['Start']
            day_total = 0
            
            for group in result.get('Groups', []):
                service = group['Keys'][0].lower()
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                day_total += cost
            
            daily_costs[date] = day_total
            total_cost += day_total
        
        # Calculate trends
        costs_list = list(daily_costs.values())
        if len(costs_list) >= 2:
            recent_avg = sum(costs_list[-3:]) / min(3, len(costs_list))
            earlier_avg = sum(costs_list[:-3]) / max(1, len(costs_list) - 3)
            trend = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
        else:
            trend = 0
        
        # Get current service costs for recommendations
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        today_end = today_start + timedelta(days=1)
        
        today_response = self.get_cost_and_usage(today_start, today_end)
        today_service_costs = self.parse_cost_data(today_response)
        
        # Generate recommendations
        recommendations = []
        if total_cost > 0:
            recommendations = self._get_global_recommendations(today_service_costs)
        
        return {
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'cost_summary': {
                'total_cost': round(total_cost, 2),
                'average_daily_cost': round(total_cost / days, 2),
                'trend_percentage': round(trend, 2)
            },
            'daily_costs': daily_costs,
            'current_service_costs': today_service_costs,
            'recommendations': recommendations,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def store_cost_history(self, service_costs: Dict[str, float]) -> bool:
        """Store cost history in DynamoDB for trend analysis."""
        if not self.config_table:
            return False
        
        try:
            date_key = datetime.utcnow().date().isoformat()
            
            self.config_table.put_item(
                Item={
                    'config_key': f'cost_history_{date_key}',
                    'category': 'cost_monitoring',
                    'date': date_key,
                    'service_costs': service_costs,
                    'total_cost': sum(service_costs.values()),
                    'updated_at': datetime.utcnow().isoformat(),
                    'environment': ENVIRONMENT
                }
            )
            
            logger.info(f"Stored cost history for {date_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing cost history: {e}")
            return False


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for cost monitoring.
    
    Expected event structure:
    {
        "action": "check_costs" | "generate_report" | "get_recommendations",
        "days": 7 (for report generation),
        "send_alerts": true/false (default: true)
    }
    """
    try:
        # Parse input
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        action = body.get('action', 'check_costs')
        monitor = CostMonitor()
        
        if action == 'check_costs':
            # Check current costs and send alerts if needed
            send_alerts = body.get('send_alerts', True)
            
            # Get today's costs
            today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
            today_end = today_start + timedelta(days=1)
            
            cost_response = monitor.get_cost_and_usage(today_start, today_end)
            service_costs = monitor.parse_cost_data(cost_response)
            
            # Check thresholds
            alerts = monitor.check_cost_thresholds(service_costs)
            
            # Send alerts if enabled
            alerts_sent = 0
            if send_alerts:
                for alert in alerts:
                    if monitor.send_cost_alert(alert):
                        alerts_sent += 1
            
            # Publish metrics
            monitor.publish_cost_metrics(service_costs)
            
            # Store cost history
            monitor.store_cost_history(service_costs)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'service_costs': service_costs,
                    'total_cost': sum(service_costs.values()),
                    'alerts': [asdict(alert) for alert in alerts],
                    'alerts_sent': alerts_sent,
                    'metrics_published': True,
                    'checked_at': datetime.utcnow().isoformat()
                })
            }
        
        elif action == 'generate_report':
            # Generate cost report
            days = body.get('days', 7)
            
            report = monitor.generate_cost_report(days)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(report)
            }
        
        elif action == 'get_recommendations':
            # Get cost optimization recommendations
            today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
            today_end = today_start + timedelta(days=1)
            
            cost_response = monitor.get_cost_and_usage(today_start, today_end)
            service_costs = monitor.parse_cost_data(cost_response)
            
            recommendations = {}
            for service, cost in service_costs.items():
                if cost > 0:
                    recommendations[service] = monitor._get_cost_recommendations(service, cost)
            
            global_recommendations = monitor._get_global_recommendations(service_costs)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'service_recommendations': recommendations,
                    'global_recommendations': global_recommendations,
                    'service_costs': service_costs,
                    'generated_at': datetime.utcnow().isoformat()
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        logger.error(f"Error in cost monitor handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }