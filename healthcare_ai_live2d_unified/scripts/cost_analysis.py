"""
AWS Cost Analysis and Optimization Script
=========================================

Analyzes current AWS costs for the Healthcare AI system and provides
optimization recommendations.
"""

import json
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import argparse
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CostMetric:
    """Cost metric data."""
    service: str
    amount: float
    unit: str
    usage_type: str
    region: str


@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation."""
    category: str
    title: str
    description: str
    potential_savings: float
    implementation_effort: str  # 'low', 'medium', 'high'
    priority: str  # 'high', 'medium', 'low'


class HealthcareAICostAnalyzer:
    """Cost analyzer for Healthcare AI system."""
    
    def __init__(self, environment: str, aws_region: str):
        self.environment = environment
        self.aws_region = aws_region
        
        # AWS clients
        self.ce_client = boto3.client('ce', region_name='us-east-1')  # Cost Explorer only in us-east-1
        self.cloudwatch = boto3.client('cloudwatch', region_name=aws_region)
        self.lambda_client = boto3.client('lambda', region_name=aws_region)
        self.dynamodb = boto3.client('dynamodb', region_name=aws_region)
        self.s3 = boto3.client('s3', region_name=aws_region)
        self.pricing = boto3.client('pricing', region_name='us-east-1')
        
    def analyze_current_costs(self, days_back: int = 30) -> Dict[str, Any]:
        """Analyze current costs for the Healthcare AI system."""
        logger.info(f"Analyzing costs for the last {days_back} days...")
        
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            # Get cost and usage data
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [
                            'AWS Lambda',
                            'Amazon DynamoDB',
                            'Amazon S3',
                            'Amazon API Gateway',
                            'Amazon CloudFront',
                            'Amazon Transcribe',
                            'Amazon Polly',
                            'Amazon Bedrock'
                        ]
                    }
                }
            )
            
            # Process cost data
            cost_breakdown = self._process_cost_data(response)
            
            # Calculate projections
            monthly_projection = self._calculate_monthly_projection(cost_breakdown, days_back)
            
            # Get usage metrics
            usage_metrics = self._get_usage_metrics()
            
            return {
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days_back
                },
                'cost_breakdown': cost_breakdown,
                'monthly_projection': monthly_projection,
                'usage_metrics': usage_metrics,
                'total_cost': sum(cost_breakdown.values()),
                'average_daily_cost': sum(cost_breakdown.values()) / days_back
            }
            
        except Exception as e:
            logger.error(f"Error analyzing costs: {e}")
            return self._get_estimated_costs()
    
    def _process_cost_data(self, cost_response: Dict[str, Any]) -> Dict[str, float]:
        """Process AWS Cost Explorer response."""
        cost_breakdown = {}
        
        for result in cost_response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service = group['Keys'][0]
                usage_type = group['Keys'][1]
                
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                
                if service not in cost_breakdown:
                    cost_breakdown[service] = 0.0
                
                cost_breakdown[service] += cost
        
        return cost_breakdown
    
    def _calculate_monthly_projection(self, cost_breakdown: Dict[str, float], days_back: int) -> Dict[str, float]:
        """Calculate monthly cost projection."""
        daily_average = {
            service: cost / days_back
            for service, cost in cost_breakdown.items()
        }
        
        monthly_projection = {
            service: daily_cost * 30
            for service, daily_cost in daily_average.items()
        }
        
        return monthly_projection
    
    def _get_usage_metrics(self) -> Dict[str, Any]:
        """Get usage metrics for optimization analysis."""
        metrics = {}
        
        try:
            # Lambda metrics
            lambda_metrics = self._get_lambda_metrics()
            metrics['lambda'] = lambda_metrics
            
            # DynamoDB metrics
            dynamodb_metrics = self._get_dynamodb_metrics()
            metrics['dynamodb'] = dynamodb_metrics
            
            # S3 metrics
            s3_metrics = self._get_s3_metrics()
            metrics['s3'] = s3_metrics
            
        except Exception as e:
            logger.warning(f"Error getting usage metrics: {e}")
        
        return metrics
    
    def _get_lambda_metrics(self) -> Dict[str, Any]:
        """Get Lambda function metrics."""
        lambda_functions = [
            f"{self.environment}-healthcare-agent-router",
            f"{self.environment}-healthcare-illness-monitor",
            f"{self.environment}-healthcare-mental-health",
            f"{self.environment}-healthcare-safety-guardian",
            f"{self.environment}-healthcare-wellness-coach"
        ]
        
        metrics = {}
        
        for function_name in lambda_functions:
            try:
                # Get function configuration
                config = self.lambda_client.get_function(FunctionName=function_name)
                
                # Get CloudWatch metrics
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=7)
                
                # Duration metrics
                duration_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Duration',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1 hour
                    Statistics=['Average', 'Maximum']
                )
                
                # Invocation metrics
                invocation_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum']
                )
                
                metrics[function_name] = {
                    'memory_size': config['Configuration']['MemorySize'],
                    'timeout': config['Configuration']['Timeout'],
                    'runtime': config['Configuration']['Runtime'],
                    'avg_duration': self._get_metric_average(duration_response, 'Average'),
                    'max_duration': self._get_metric_maximum(duration_response, 'Maximum'),
                    'total_invocations': self._get_metric_sum(invocation_response, 'Sum')
                }
                
            except Exception as e:
                logger.warning(f"Error getting metrics for {function_name}: {e}")
                metrics[function_name] = {'error': str(e)}
        
        return metrics
    
    def _get_dynamodb_metrics(self) -> Dict[str, Any]:
        """Get DynamoDB metrics."""
        tables = [
            f"{self.environment}-healthcare-conversations",
            f"{self.environment}-healthcare-users",
            f"{self.environment}-hongkong-healthcare-data"
        ]
        
        metrics = {}
        
        for table_name in tables:
            try:
                # Get table description
                table_info = self.dynamodb.describe_table(TableName=table_name)
                
                # Get CloudWatch metrics
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=7)
                
                # Read capacity metrics
                read_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ConsumedReadCapacityUnits',
                    Dimensions=[{'Name': 'TableName', 'Value': table_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum']
                )
                
                # Write capacity metrics
                write_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ConsumedWriteCapacityUnits',
                    Dimensions=[{'Name': 'TableName', 'Value': table_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum']
                )
                
                metrics[table_name] = {
                    'billing_mode': table_info['Table']['BillingModeSummary']['BillingMode'],
                    'table_status': table_info['Table']['TableStatus'],
                    'item_count': table_info['Table'].get('ItemCount', 0),
                    'table_size_bytes': table_info['Table'].get('TableSizeBytes', 0),
                    'total_read_units': self._get_metric_sum(read_response, 'Sum'),
                    'total_write_units': self._get_metric_sum(write_response, 'Sum')
                }
                
            except Exception as e:
                logger.warning(f"Error getting metrics for {table_name}: {e}")
                metrics[table_name] = {'error': str(e)}
        
        return metrics
    
    def _get_s3_metrics(self) -> Dict[str, Any]:
        """Get S3 metrics."""
        buckets = [
            f"{self.environment}-healthcare-live2d-{boto3.Session().get_credentials().access_key[:8]}",
            f"{self.environment}-healthcare-data-{boto3.Session().get_credentials().access_key[:8]}"
        ]
        
        metrics = {}
        
        for bucket_name in buckets:
            try:
                # Get bucket size
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=1)
                
                size_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/S3',
                    MetricName='BucketSizeBytes',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': bucket_name},
                        {'Name': 'StorageType', 'Value': 'StandardStorage'}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,  # 1 day
                    Statistics=['Average']
                )
                
                # Get number of objects
                objects_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/S3',
                    MetricName='NumberOfObjects',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': bucket_name},
                        {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Average']
                )
                
                metrics[bucket_name] = {
                    'size_bytes': self._get_metric_average(size_response, 'Average'),
                    'object_count': self._get_metric_average(objects_response, 'Average')
                }
                
            except Exception as e:
                logger.warning(f"Error getting metrics for {bucket_name}: {e}")
                metrics[bucket_name] = {'error': str(e)}
        
        return metrics
    
    def _get_metric_average(self, response: Dict[str, Any], stat_key: str) -> float:
        """Get average from CloudWatch metric response."""
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 0.0
        
        values = [dp[stat_key] for dp in datapoints if stat_key in dp]
        return sum(values) / len(values) if values else 0.0
    
    def _get_metric_maximum(self, response: Dict[str, Any], stat_key: str) -> float:
        """Get maximum from CloudWatch metric response."""
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 0.0
        
        values = [dp[stat_key] for dp in datapoints if stat_key in dp]
        return max(values) if values else 0.0
    
    def _get_metric_sum(self, response: Dict[str, Any], stat_key: str) -> float:
        """Get sum from CloudWatch metric response."""
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 0.0
        
        values = [dp[stat_key] for dp in datapoints if stat_key in dp]
        return sum(values) if values else 0.0
    
    def _get_estimated_costs(self) -> Dict[str, Any]:
        """Get estimated costs when actual data is not available."""
        logger.info("Using estimated costs (actual cost data not available)")
        
        estimated_costs = {
            'AWS Lambda': 2.50,
            'Amazon DynamoDB': 3.75,
            'Amazon S3': 1.50,
            'Amazon API Gateway': 2.00,
            'Amazon CloudFront': 1.00,
            'Amazon Transcribe': 1.50,
            'Amazon Polly': 1.50,
            'Amazon Bedrock': 8.00
        }
        
        return {
            'analysis_period': {
                'start_date': (datetime.utcnow().date() - timedelta(days=30)).isoformat(),
                'end_date': datetime.utcnow().date().isoformat(),
                'days': 30
            },
            'cost_breakdown': estimated_costs,
            'monthly_projection': estimated_costs,
            'usage_metrics': {},
            'total_cost': sum(estimated_costs.values()),
            'average_daily_cost': sum(estimated_costs.values()) / 30,
            'estimated': True
        }
    
    def generate_optimization_recommendations(self, cost_analysis: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        cost_breakdown = cost_analysis.get('cost_breakdown', {})
        usage_metrics = cost_analysis.get('usage_metrics', {})
        monthly_projection = cost_analysis.get('monthly_projection', {})
        
        # Lambda optimization recommendations
        lambda_cost = cost_breakdown.get('AWS Lambda', 0)
        if lambda_cost > 5.0:  # If Lambda costs are high
            recommendations.append(OptimizationRecommendation(
                category='Lambda',
                title='Optimize Lambda Memory Configuration',
                description='Review Lambda function memory settings and optimize based on actual usage patterns. Over-provisioned memory increases costs.',
                potential_savings=lambda_cost * 0.3,  # Potential 30% savings
                implementation_effort='low',
                priority='high'
            ))
        
        # Check Lambda metrics for optimization opportunities
        lambda_metrics = usage_metrics.get('lambda', {})
        for function_name, metrics in lambda_metrics.items():
            if isinstance(metrics, dict) and 'avg_duration' in metrics:
                avg_duration = metrics.get('avg_duration', 0)
                memory_size = metrics.get('memory_size', 128)
                
                # If function runs quickly but has high memory allocation
                if avg_duration < 1000 and memory_size > 512:  # Less than 1 second, more than 512MB
                    recommendations.append(OptimizationRecommendation(
                        category='Lambda',
                        title=f'Reduce Memory for {function_name}',
                        description=f'Function completes in {avg_duration:.0f}ms but has {memory_size}MB allocated. Consider reducing memory allocation.',
                        potential_savings=0.50,  # Estimated savings per function
                        implementation_effort='low',
                        priority='medium'
                    ))
        
        # DynamoDB optimization recommendations
        dynamodb_cost = cost_breakdown.get('Amazon DynamoDB', 0)
        if dynamodb_cost > 3.0:
            recommendations.append(OptimizationRecommendation(
                category='DynamoDB',
                title='Implement TTL for Automatic Data Cleanup',
                description='Configure Time-To-Live (TTL) on conversation data to automatically delete old records and reduce storage costs.',
                potential_savings=dynamodb_cost * 0.4,  # Potential 40% savings
                implementation_effort='low',
                priority='high'
            ))
        
        # S3 optimization recommendations
        s3_cost = cost_breakdown.get('Amazon S3', 0)
        if s3_cost > 2.0:
            recommendations.append(OptimizationRecommendation(
                category='S3',
                title='Implement S3 Lifecycle Policies',
                description='Set up lifecycle policies to transition old files to cheaper storage classes (IA, Glacier) and delete temporary files.',
                potential_savings=s3_cost * 0.5,  # Potential 50% savings
                implementation_effort='low',
                priority='medium'
            ))
        
        # Bedrock optimization recommendations
        bedrock_cost = cost_breakdown.get('Amazon Bedrock', 0)
        if bedrock_cost > 10.0:
            recommendations.append(OptimizationRecommendation(
                category='Bedrock',
                title='Optimize AI Model Selection',
                description='Implement intelligent model selection to use cheaper models for simple queries and reserve expensive models for complex requests.',
                potential_savings=bedrock_cost * 0.3,  # Potential 30% savings
                implementation_effort='medium',
                priority='high'
            ))
        
        # API Gateway optimization
        api_cost = cost_breakdown.get('Amazon API Gateway', 0)
        if api_cost > 3.0:
            recommendations.append(OptimizationRecommendation(
                category='API Gateway',
                title='Implement Response Caching',
                description='Enable API Gateway response caching for frequently requested data to reduce backend calls and costs.',
                potential_savings=api_cost * 0.2,  # Potential 20% savings
                implementation_effort='medium',
                priority='medium'
            ))
        
        # General recommendations
        total_monthly_cost = sum(monthly_projection.values())
        
        if total_monthly_cost > 50:
            recommendations.append(OptimizationRecommendation(
                category='Monitoring',
                title='Set Up Cost Anomaly Detection',
                description='Configure AWS Cost Anomaly Detection to automatically alert on unusual spending patterns.',
                potential_savings=total_monthly_cost * 0.1,  # Prevent 10% cost overruns
                implementation_effort='low',
                priority='high'
            ))
        
        recommendations.append(OptimizationRecommendation(
            category='Architecture',
            title='Consider Reserved Capacity for Consistent Workloads',
            description='If usage patterns become predictable, consider Reserved Capacity for DynamoDB and Savings Plans for Lambda to reduce costs.',
            potential_savings=total_monthly_cost * 0.15,  # Potential 15% savings
            implementation_effort='high',
            priority='low'
        ))
        
        # Sort recommendations by priority and potential savings
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        recommendations.sort(key=lambda x: (priority_order[x.priority], x.potential_savings), reverse=True)
        
        return recommendations
    
    def generate_cost_report(self, cost_analysis: Dict[str, Any], recommendations: List[OptimizationRecommendation]) -> Dict[str, Any]:
        """Generate comprehensive cost analysis report."""
        total_potential_savings = sum(rec.potential_savings for rec in recommendations)
        monthly_projection = cost_analysis.get('monthly_projection', {})
        total_monthly_cost = sum(monthly_projection.values())
        
        return {
            'report_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'environment': self.environment,
                'aws_region': self.aws_region,
                'analysis_period': cost_analysis.get('analysis_period', {})
            },
            'cost_summary': {
                'current_monthly_projection': total_monthly_cost,
                'total_potential_savings': total_potential_savings,
                'optimized_monthly_cost': total_monthly_cost - total_potential_savings,
                'potential_savings_percentage': (total_potential_savings / total_monthly_cost * 100) if total_monthly_cost > 0 else 0
            },
            'cost_breakdown': cost_analysis.get('cost_breakdown', {}),
            'monthly_projection': monthly_projection,
            'usage_metrics': cost_analysis.get('usage_metrics', {}),
            'optimization_recommendations': [
                {
                    'category': rec.category,
                    'title': rec.title,
                    'description': rec.description,
                    'potential_savings': rec.potential_savings,
                    'implementation_effort': rec.implementation_effort,
                    'priority': rec.priority
                }
                for rec in recommendations
            ],
            'implementation_roadmap': self._generate_implementation_roadmap(recommendations)
        }
    
    def _generate_implementation_roadmap(self, recommendations: List[OptimizationRecommendation]) -> Dict[str, List[str]]:
        """Generate implementation roadmap based on effort and priority."""
        roadmap = {
            'immediate': [],  # Low effort, high priority
            'short_term': [],  # Low-medium effort, medium-high priority
            'long_term': []   # High effort or low priority
        }
        
        for rec in recommendations:
            if rec.implementation_effort == 'low' and rec.priority in ['high', 'medium']:
                roadmap['immediate'].append(rec.title)
            elif rec.implementation_effort in ['low', 'medium'] and rec.priority != 'low':
                roadmap['short_term'].append(rec.title)
            else:
                roadmap['long_term'].append(rec.title)
        
        return roadmap


def main():
    """Main function for cost analysis."""
    parser = argparse.ArgumentParser(description='Analyze Healthcare AI AWS Costs')
    parser.add_argument('--environment', default='dev', help='Environment to analyze')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze')
    parser.add_argument('--output', help='Output file for cost report')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create cost analyzer
    analyzer = HealthcareAICostAnalyzer(args.environment, args.region)
    
    try:
        # Analyze current costs
        logger.info("Analyzing current costs...")
        cost_analysis = analyzer.analyze_current_costs(args.days)
        
        # Generate optimization recommendations
        logger.info("Generating optimization recommendations...")
        recommendations = analyzer.generate_optimization_recommendations(cost_analysis)
        
        # Generate comprehensive report
        logger.info("Generating cost report...")
        cost_report = analyzer.generate_cost_report(cost_analysis, recommendations)
        
        # Save report if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(cost_report, f, indent=2)
            logger.info(f"Cost report saved to: {args.output}")
        
        # Print summary
        summary = cost_report['cost_summary']
        print(f"\n{'='*60}")
        print(f"HEALTHCARE AI COST ANALYSIS REPORT")
        print(f"{'='*60}")
        print(f"Environment: {args.environment}")
        print(f"Analysis Period: {args.days} days")
        print(f"")
        print(f"💰 Current Monthly Projection: ${summary['current_monthly_projection']:.2f}")
        print(f"💡 Total Potential Savings: ${summary['total_potential_savings']:.2f}")
        print(f"✨ Optimized Monthly Cost: ${summary['optimized_monthly_cost']:.2f}")
        print(f"📊 Potential Savings: {summary['potential_savings_percentage']:.1f}%")
        
        # Print cost breakdown
        print(f"\n📋 Cost Breakdown:")
        cost_breakdown = cost_report['cost_breakdown']
        for service, cost in sorted(cost_breakdown.items(), key=lambda x: x[1], reverse=True):
            print(f"  {service}: ${cost:.2f}")
        
        # Print top recommendations
        print(f"\n🎯 Top Optimization Recommendations:")
        for i, rec in enumerate(cost_report['optimization_recommendations'][:5], 1):
            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            effort_emoji = {'low': '⚡', 'medium': '⚖️', 'high': '🏗️'}
            
            print(f"  {i}. {rec['title']}")
            print(f"     {priority_emoji[rec['priority']]} Priority: {rec['priority'].title()}")
            print(f"     {effort_emoji[rec['implementation_effort']]} Effort: {rec['implementation_effort'].title()}")
            print(f"     💵 Potential Savings: ${rec['potential_savings']:.2f}")
            print()
        
        # Print implementation roadmap
        roadmap = cost_report['implementation_roadmap']
        print(f"🗺️ Implementation Roadmap:")
        
        if roadmap['immediate']:
            print(f"  📅 Immediate (implement now):")
            for item in roadmap['immediate']:
                print(f"    • {item}")
        
        if roadmap['short_term']:
            print(f"  📅 Short-term (next 1-3 months):")
            for item in roadmap['short_term']:
                print(f"    • {item}")
        
        if roadmap['long_term']:
            print(f"  📅 Long-term (3+ months):")
            for item in roadmap['long_term']:
                print(f"    • {item}")
        
        print(f"\n{'='*60}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Cost analysis failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())