"""
CloudWatch Monitoring and Logging Setup
=======================================

Sets up comprehensive monitoring, logging, and alerting for the healthcare AI system.
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class CloudWatchSetup:
    """Sets up CloudWatch monitoring, logging, and alerting."""
    
    def __init__(self, environment: str = 'dev'):
        self.cloudwatch = boto3.client('cloudwatch')
        self.logs = boto3.client('logs')
        self.sns = boto3.client('sns')
        self.environment = environment
        
        # Namespace for custom metrics
        self.namespace = f'HealthcareAI/{environment.title()}'
        
        # Log group configurations
        self.log_groups = {
            'lambda-agent-router': {
                'retention_days': 30,
                'description': 'Agent router Lambda function logs'
            },
            'lambda-illness-monitor': {
                'retention_days': 30,
                'description': 'Illness monitor agent logs'
            },
            'lambda-mental-health': {
                'retention_days': 90,  # Longer retention for mental health
                'description': 'Mental health agent logs'
            },
            'lambda-safety-guardian': {
                'retention_days': 90,  # Longer retention for emergencies
                'description': 'Safety guardian emergency response logs'
            },
            'lambda-wellness-coach': {
                'retention_days': 30,
                'description': 'Wellness coach agent logs'
            },
            'lambda-speech-to-text': {
                'retention_days': 14,
                'description': 'Speech to text processing logs'
            },
            'lambda-text-to-speech': {
                'retention_days': 14,
                'description': 'Text to speech processing logs'
            },
            'lambda-file-upload': {
                'retention_days': 60,
                'description': 'File upload and processing logs'
            },
            'lambda-cost-monitor': {
                'retention_days': 90,
                'description': 'Cost monitoring and optimization logs'
            },
            'api-gateway': {
                'retention_days': 30,
                'description': 'API Gateway access and execution logs'
            },
            'cloudfront': {
                'retention_days': 14,
                'description': 'CloudFront access logs'
            }
        }
        
        # Metric filters for structured logging
        self.metric_filters = [
            {
                'log_group': 'lambda-agent-router',
                'filter_name': 'ConversationCount',
                'filter_pattern': '[timestamp, request_id, "CONVERSATION_STARTED"]',
                'metric_name': 'ConversationsStarted',
                'metric_value': '1'
            },
            {
                'log_group': 'lambda-mental-health',
                'filter_name': 'CrisisDetection',
                'filter_pattern': '[timestamp, request_id, "CRISIS_DETECTED"]',
                'metric_name': 'CrisisDetections',
                'metric_value': '1'
            },
            {
                'log_group': 'lambda-safety-guardian',
                'filter_name': 'EmergencyResponse',
                'filter_pattern': '[timestamp, request_id, "EMERGENCY_ACTIVATED"]',
                'metric_name': 'EmergencyActivations',
                'metric_value': '1'
            },
            {
                'log_group': 'lambda-agent-router',
                'filter_name': 'ErrorCount',
                'filter_pattern': '[timestamp, request_id, "ERROR"]',
                'metric_name': 'Errors',
                'metric_value': '1'
            },
            {
                'log_group': 'lambda-speech-to-text',
                'filter_name': 'SpeechProcessing',
                'filter_pattern': '[timestamp, request_id, "SPEECH_PROCESSED"]',
                'metric_name': 'SpeechProcessed',
                'metric_value': '1'
            }
        ]
        
        # CloudWatch alarms configuration
        self.alarms = [
            {
                'name': 'HighErrorRate',
                'description': 'High error rate across Lambda functions',
                'metric_name': 'Errors',
                'statistic': 'Sum',
                'period': 300,  # 5 minutes
                'evaluation_periods': 2,
                'threshold': 10,
                'comparison_operator': 'GreaterThanThreshold',
                'severity': 'high'
            },
            {
                'name': 'CrisisDetectionAlert',
                'description': 'Mental health crisis detected',
                'metric_name': 'CrisisDetections',
                'statistic': 'Sum',
                'period': 60,  # 1 minute
                'evaluation_periods': 1,
                'threshold': 1,
                'comparison_operator': 'GreaterThanOrEqualToThreshold',
                'severity': 'critical'
            },
            {
                'name': 'EmergencyActivationAlert',
                'description': 'Emergency response activated',
                'metric_name': 'EmergencyActivations',
                'statistic': 'Sum',
                'period': 60,  # 1 minute
                'evaluation_periods': 1,
                'threshold': 1,
                'comparison_operator': 'GreaterThanOrEqualToThreshold',
                'severity': 'critical'
            },
            {
                'name': 'HighLambdaDuration',
                'description': 'Lambda function duration is high',
                'metric_name': 'Duration',
                'namespace': 'AWS/Lambda',
                'statistic': 'Average',
                'period': 300,
                'evaluation_periods': 3,
                'threshold': 30000,  # 30 seconds
                'comparison_operator': 'GreaterThanThreshold',
                'severity': 'medium'
            },
            {
                'name': 'DynamoDBThrottling',
                'description': 'DynamoDB throttling detected',
                'metric_name': 'ThrottledRequests',
                'namespace': 'AWS/DynamoDB',
                'statistic': 'Sum',
                'period': 300,
                'evaluation_periods': 2,
                'threshold': 5,
                'comparison_operator': 'GreaterThanThreshold',
                'severity': 'high'
            }
        ]
    
    def create_log_groups(self) -> Dict[str, Any]:
        """Create CloudWatch log groups with appropriate retention."""
        results = {'created': [], 'existing': [], 'errors': []}
        
        for log_group_name, config in self.log_groups.items():
            full_log_group_name = f"/aws/lambda/healthcare-ai-{self.environment}-{log_group_name}"
            
            try:
                # Check if log group exists
                try:
                    self.logs.describe_log_groups(logGroupNamePrefix=full_log_group_name)
                    existing_groups = self.logs.describe_log_groups(
                        logGroupNamePrefix=full_log_group_name
                    )['logGroups']
                    
                    if any(lg['logGroupName'] == full_log_group_name for lg in existing_groups):
                        results['existing'].append(full_log_group_name)
                        continue
                        
                except self.logs.exceptions.ResourceNotFoundException:
                    pass
                
                # Create log group
                self.logs.create_log_group(logGroupName=full_log_group_name)
                
                # Set retention policy
                self.logs.put_retention_policy(
                    logGroupName=full_log_group_name,
                    retentionInDays=config['retention_days']
                )
                
                results['created'].append(full_log_group_name)
                logger.info(f"Created log group: {full_log_group_name}")
                
            except Exception as e:
                error_msg = f"Error creating log group {full_log_group_name}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    def create_metric_filters(self) -> Dict[str, Any]:
        """Create CloudWatch metric filters for structured logging."""
        results = {'created': [], 'errors': []}
        
        for filter_config in self.metric_filters:
            log_group_name = f"/aws/lambda/healthcare-ai-{self.environment}-{filter_config['log_group']}"
            filter_name = f"{self.environment}-{filter_config['filter_name']}"
            
            try:
                self.logs.put_metric_filter(
                    logGroupName=log_group_name,
                    filterName=filter_name,
                    filterPattern=filter_config['filter_pattern'],
                    metricTransformations=[
                        {
                            'metricName': filter_config['metric_name'],
                            'metricNamespace': self.namespace,
                            'metricValue': filter_config['metric_value'],
                            'defaultValue': 0
                        }
                    ]
                )
                
                results['created'].append(filter_name)
                logger.info(f"Created metric filter: {filter_name}")
                
            except Exception as e:
                error_msg = f"Error creating metric filter {filter_name}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    def create_sns_topics(self) -> Dict[str, str]:
        """Create SNS topics for alerts."""
        topics = {
            'critical-alerts': 'Critical healthcare AI alerts (emergencies, crises)',
            'high-alerts': 'High priority alerts (errors, performance issues)',
            'medium-alerts': 'Medium priority alerts (warnings, optimization)',
            'cost-alerts': 'Cost monitoring and budget alerts'
        }
        
        topic_arns = {}
        
        for topic_name, description in topics.items():
            full_topic_name = f"healthcare-ai-{self.environment}-{topic_name}"
            
            try:
                response = self.sns.create_topic(Name=full_topic_name)
                topic_arn = response['TopicArn']
                
                # Set topic attributes
                self.sns.set_topic_attributes(
                    TopicArn=topic_arn,
                    AttributeName='DisplayName',
                    AttributeValue=f"Healthcare AI {topic_name.replace('-', ' ').title()}"
                )
                
                topic_arns[topic_name] = topic_arn
                logger.info(f"Created SNS topic: {full_topic_name}")
                
            except Exception as e:
                logger.error(f"Error creating SNS topic {full_topic_name}: {e}")
        
        return topic_arns
    
    def create_cloudwatch_alarms(self, topic_arns: Dict[str, str]) -> Dict[str, Any]:
        """Create CloudWatch alarms with SNS notifications."""
        results = {'created': [], 'errors': []}
        
        for alarm_config in self.alarms:
            alarm_name = f"healthcare-ai-{self.environment}-{alarm_config['name']}"
            
            try:
                # Determine SNS topic based on severity
                severity = alarm_config.get('severity', 'medium')
                topic_key = f"{severity}-alerts"
                
                if topic_key not in topic_arns:
                    topic_key = 'medium-alerts'  # Fallback
                
                alarm_actions = [topic_arns[topic_key]] if topic_key in topic_arns else []
                
                # Create alarm
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm_name,
                    AlarmDescription=alarm_config['description'],
                    ActionsEnabled=True,
                    AlarmActions=alarm_actions,
                    MetricName=alarm_config['metric_name'],
                    Namespace=alarm_config.get('namespace', self.namespace),
                    Statistic=alarm_config['statistic'],
                    Period=alarm_config['period'],
                    EvaluationPeriods=alarm_config['evaluation_periods'],
                    Threshold=alarm_config['threshold'],
                    ComparisonOperator=alarm_config['comparison_operator'],
                    TreatMissingData='notBreaching'
                )
                
                results['created'].append(alarm_name)
                logger.info(f"Created CloudWatch alarm: {alarm_name}")
                
            except Exception as e:
                error_msg = f"Error creating alarm {alarm_name}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    def create_dashboard(self) -> str:
        """Create CloudWatch dashboard for healthcare AI monitoring."""
        dashboard_name = f"HealthcareAI-{self.environment.title()}"
        
        # Dashboard configuration
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "ConversationsStarted"],
                            [self.namespace, "CrisisDetections"],
                            [self.namespace, "EmergencyActivations"],
                            [self.namespace, "Errors"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": "us-east-1",
                        "title": "Healthcare AI Activity"
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Lambda", "Duration", "FunctionName", f"healthcare-ai-{self.environment}-agent-router"],
                            ["AWS/Lambda", "Duration", "FunctionName", f"healthcare-ai-{self.environment}-illness-monitor"],
                            ["AWS/Lambda", "Duration", "FunctionName", f"healthcare-ai-{self.environment}-mental-health"],
                            ["AWS/Lambda", "Duration", "FunctionName", f"healthcare-ai-{self.environment}-safety-guardian"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "Lambda Function Performance"
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", f"HealthcareAI-{self.environment.title()}-Conversations"],
                            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", f"HealthcareAI-{self.environment.title()}-Conversations"],
                            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", f"HealthcareAI-{self.environment.title()}-Users"],
                            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", f"HealthcareAI-{self.environment.title()}-Users"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": "us-east-1",
                        "title": "DynamoDB Usage"
                    }
                },
                {
                    "type": "log",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "query": f"SOURCE '/aws/lambda/healthcare-ai-{self.environment}-agent-router'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 20",
                        "region": "us-east-1",
                        "title": "Recent Errors",
                        "view": "table"
                    }
                }
            ]
        }
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            logger.info(f"Created CloudWatch dashboard: {dashboard_name}")
            return dashboard_name
            
        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            return None
    
    def setup_complete_monitoring(self) -> Dict[str, Any]:
        """Set up complete monitoring infrastructure."""
        logger.info(f"Setting up monitoring for healthcare AI ({self.environment})")
        
        results = {
            'environment': self.environment,
            'setup_started_at': datetime.utcnow().isoformat()
        }
        
        # Create log groups
        logger.info("Creating CloudWatch log groups...")
        results['log_groups'] = self.create_log_groups()
        
        # Create metric filters
        logger.info("Creating metric filters...")
        results['metric_filters'] = self.create_metric_filters()
        
        # Create SNS topics
        logger.info("Creating SNS topics...")
        topic_arns = self.create_sns_topics()
        results['sns_topics'] = topic_arns
        
        # Create CloudWatch alarms
        logger.info("Creating CloudWatch alarms...")
        results['alarms'] = self.create_cloudwatch_alarms(topic_arns)
        
        # Create dashboard
        logger.info("Creating CloudWatch dashboard...")
        dashboard_name = self.create_dashboard()
        results['dashboard'] = dashboard_name
        
        results['setup_completed_at'] = datetime.utcnow().isoformat()
        
        # Summary
        total_created = (
            len(results['log_groups']['created']) +
            len(results['metric_filters']['created']) +
            len(topic_arns) +
            len(results['alarms']['created']) +
            (1 if dashboard_name else 0)
        )
        
        total_errors = (
            len(results['log_groups']['errors']) +
            len(results['metric_filters']['errors']) +
            len(results['alarms']['errors'])
        )
        
        results['summary'] = {
            'total_resources_created': total_created,
            'total_errors': total_errors,
            'success_rate': (total_created / (total_created + total_errors) * 100) if (total_created + total_errors) > 0 else 100
        }
        
        logger.info(f"Monitoring setup completed: {total_created} resources created, {total_errors} errors")
        
        return results


def main():
    """Main setup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Set up CloudWatch monitoring for Healthcare AI')
    parser.add_argument('--environment', default='dev', help='Environment (dev/staging/prod)')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and run setup
    setup = CloudWatchSetup(args.environment)
    results = setup.setup_complete_monitoring()
    
    # Print results
    print(json.dumps(results, indent=2))
    
    # Print summary
    summary = results['summary']
    print(f"\n✅ Monitoring setup completed!")
    print(f"Resources created: {summary['total_resources_created']}")
    print(f"Errors: {summary['total_errors']}")
    print(f"Success rate: {summary['success_rate']:.1f}%")
    
    if results.get('dashboard'):
        print(f"Dashboard: {results['dashboard']}")


if __name__ == '__main__':
    main()