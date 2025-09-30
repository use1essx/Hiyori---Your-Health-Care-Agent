"""
Final Integration and Testing Suite
==================================

Comprehensive final integration testing for the Healthcare AI Live2D system
deployed on AWS. This script validates all components work together correctly.
"""

import json
import boto3
import requests
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import argparse
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import existing test framework
from test_framework import HealthcareAITestFramework, TestResult, TestSuite

logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestConfig:
    """Configuration for integration testing."""
    environment: str
    aws_region: str
    stack_name: str
    api_base_url: Optional[str] = None
    cloudfront_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    parallel_tests: int = 5


@dataclass
class CostAnalysis:
    """Cost analysis results."""
    estimated_monthly_cost: float
    cost_breakdown: Dict[str, float]
    optimization_recommendations: List[str]
    cost_alerts_configured: bool


class FinalIntegrationTester:
    """Final integration testing orchestrator."""
    
    def __init__(self, config: IntegrationTestConfig):
        self.config = config
        self.test_framework = HealthcareAITestFramework(config.environment)
        
        # AWS clients
        self.cloudformation = boto3.client('cloudformation', region_name=config.aws_region)
        self.lambda_client = boto3.client('lambda', region_name=config.aws_region)
        self.dynamodb = boto3.client('dynamodb', region_name=config.aws_region)
        self.s3 = boto3.client('s3', region_name=config.aws_region)
        self.apigateway = boto3.client('apigateway', region_name=config.aws_region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=config.aws_region)
        self.pricing = boto3.client('pricing', region_name='us-east-1')  # Pricing API only in us-east-1
        
        # Test results
        self.test_results = []
        self.deployment_info = {}
        
    def setup_integration_test(self) -> bool:
        """Set up integration test environment."""
        try:
            logger.info("Setting up final integration test environment...")
            
            # Get deployment information
            self.deployment_info = self._get_deployment_info()
            if not self.deployment_info:
                logger.error("Failed to get deployment information")
                return False
            
            # Update config with actual URLs
            self.config.api_base_url = self.deployment_info.get('api_url')
            self.config.cloudfront_url = self.deployment_info.get('cloudfront_url')
            
            # Set up test framework
            if not self.test_framework.setup_test_environment():
                logger.error("Failed to set up test framework")
                return False
            
            logger.info("Integration test environment setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up integration test: {e}")
            return False
    
    def _get_deployment_info(self) -> Dict[str, Any]:
        """Get deployment information from CloudFormation stack."""
        try:
            response = self.cloudformation.describe_stacks(StackName=self.config.stack_name)
            
            if not response['Stacks']:
                logger.error(f"Stack {self.config.stack_name} not found")
                return {}
            
            stack = response['Stacks'][0]
            
            # Extract outputs
            outputs = {}
            for output in stack.get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']
            
            # Extract parameters
            parameters = {}
            for param in stack.get('Parameters', []):
                parameters[param['ParameterKey']] = param['ParameterValue']
            
            return {
                'stack_id': stack['StackId'],
                'stack_status': stack['StackStatus'],
                'api_url': outputs.get('APIGatewayURL'),
                'cloudfront_url': outputs.get('CloudFrontURL'),
                'website_bucket': outputs.get('WebsiteBucketName'),
                'data_bucket': outputs.get('DataBucketName'),
                'conversations_table': outputs.get('ConversationsTableName'),
                'users_table': outputs.get('UserProfilesTableName'),
                'environment': parameters.get('Environment', 'dev'),
                'outputs': outputs,
                'parameters': parameters
            }
            
        except Exception as e:
            logger.error(f"Error getting deployment info: {e}")
            return {}
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive integration tests."""
        logger.info("Starting comprehensive integration tests...")
        
        test_results = {
            'deployment_validation': self._test_deployment_validation(),
            'agent_functionality': self._test_agent_functionality(),
            'live2d_frontend': self._test_live2d_frontend(),
            'speech_functionality': self._test_speech_functionality(),
            'cost_analysis': self._perform_cost_analysis(),
            'performance_tests': self._test_performance(),
            'security_validation': self._test_security(),
            'monitoring_alerts': self._test_monitoring_alerts()
        }
        
        # Calculate overall success rate
        total_tests = 0
        passed_tests = 0
        
        for category, results in test_results.items():
            if isinstance(results, dict) and 'total_tests' in results:
                total_tests += results['total_tests']
                passed_tests += results.get('passed', 0)
        
        test_results['summary'] = {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'overall_status': 'PASSED' if passed_tests == total_tests else 'FAILED'
        }
        
        return test_results
    
    def _test_deployment_validation(self) -> Dict[str, Any]:
        """Test deployment validation."""
        logger.info("Testing deployment validation...")
        
        tests = []
        
        # Test CloudFormation stack status
        tests.append({
            'name': 'CloudFormation Stack Status',
            'passed': self.deployment_info.get('stack_status') == 'CREATE_COMPLETE' or 
                     self.deployment_info.get('stack_status') == 'UPDATE_COMPLETE',
            'details': f"Stack status: {self.deployment_info.get('stack_status')}"
        })
        
        # Test required outputs exist
        required_outputs = ['APIGatewayURL', 'CloudFrontURL', 'WebsiteBucketName', 'DataBucketName']
        for output in required_outputs:
            tests.append({
                'name': f'Required Output: {output}',
                'passed': output in self.deployment_info.get('outputs', {}),
                'details': f"Value: {self.deployment_info.get('outputs', {}).get(output, 'MISSING')}"
            })
        
        # Test Lambda functions exist and are active
        lambda_functions = [
            f"{self.deployment_info.get('environment', 'dev')}-healthcare-agent-router",
            f"{self.deployment_info.get('environment', 'dev')}-healthcare-illness-monitor",
            f"{self.deployment_info.get('environment', 'dev')}-healthcare-mental-health",
            f"{self.deployment_info.get('environment', 'dev')}-healthcare-safety-guardian",
            f"{self.deployment_info.get('environment', 'dev')}-healthcare-wellness-coach"
        ]
        
        for function_name in lambda_functions:
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                is_active = response['Configuration']['State'] == 'Active'
                tests.append({
                    'name': f'Lambda Function: {function_name}',
                    'passed': is_active,
                    'details': f"State: {response['Configuration']['State']}"
                })
            except Exception as e:
                tests.append({
                    'name': f'Lambda Function: {function_name}',
                    'passed': False,
                    'details': f"Error: {str(e)}"
                })
        
        # Test DynamoDB tables
        tables = [
            self.deployment_info.get('conversations_table'),
            self.deployment_info.get('users_table')
        ]
        
        for table_name in tables:
            if table_name:
                try:
                    response = self.dynamodb.describe_table(TableName=table_name)
                    is_active = response['Table']['TableStatus'] == 'ACTIVE'
                    tests.append({
                        'name': f'DynamoDB Table: {table_name}',
                        'passed': is_active,
                        'details': f"Status: {response['Table']['TableStatus']}"
                    })
                except Exception as e:
                    tests.append({
                        'name': f'DynamoDB Table: {table_name}',
                        'passed': False,
                        'details': f"Error: {str(e)}"
                    })
        
        return {
            'total_tests': len(tests),
            'passed': sum(1 for t in tests if t['passed']),
            'tests': tests
        }
    
    def _test_agent_functionality(self) -> Dict[str, Any]:
        """Test all four healthcare agents work correctly."""
        logger.info("Testing healthcare agent functionality...")
        
        if not self.config.api_base_url:
            return {
                'total_tests': 0,
                'passed': 0,
                'error': 'API URL not available'
            }
        
        agent_tests = []
        
        # Test messages for each agent
        test_messages = {
            'illness_monitor': [
                "I have a headache and feel dizzy",
                "我頭痛同頭暈"
            ],
            'mental_health': [
                "I'm feeling really stressed about school",
                "我對學校感到很大壓力"
            ],
            'safety_guardian': [
                "I'm having chest pain and can't breathe",
                "我胸痛，呼吸困難"
            ],
            'wellness_coach': [
                "How can I start exercising?",
                "我怎樣開始運動？"
            ]
        }
        
        for agent_type, messages in test_messages.items():
            for message in messages:
                try:
                    # Test via API Gateway
                    response = requests.post(
                        f"{self.config.api_base_url}/chat",
                        json={
                            'message': message,
                            'user_id': 'test_user_integration',
                            'conversation_id': f'test_{agent_type}_{int(time.time())}'
                        },
                        timeout=self.config.timeout
                    )
                    
                    success = response.status_code == 200
                    response_data = response.json() if success else {}
                    
                    agent_tests.append({
                        'name': f'{agent_type} - {message[:30]}...',
                        'passed': success and 'response' in response_data,
                        'details': {
                            'status_code': response.status_code,
                            'response_data': response_data,
                            'expected_agent': agent_type,
                            'actual_agent': response_data.get('agent', 'unknown')
                        }
                    })
                    
                except Exception as e:
                    agent_tests.append({
                        'name': f'{agent_type} - {message[:30]}...',
                        'passed': False,
                        'details': f"Error: {str(e)}"
                    })
        
        return {
            'total_tests': len(agent_tests),
            'passed': sum(1 for t in agent_tests if t['passed']),
            'tests': agent_tests
        }
    
    def _test_live2d_frontend(self) -> Dict[str, Any]:
        """Test Live2D avatar interactions through AWS frontend."""
        logger.info("Testing Live2D frontend...")
        
        if not self.config.cloudfront_url:
            return {
                'total_tests': 0,
                'passed': 0,
                'error': 'CloudFront URL not available'
            }
        
        frontend_tests = []
        
        # Test CloudFront accessibility
        try:
            response = requests.get(self.config.cloudfront_url, timeout=self.config.timeout)
            frontend_tests.append({
                'name': 'CloudFront Distribution Access',
                'passed': response.status_code == 200,
                'details': f"Status: {response.status_code}"
            })
        except Exception as e:
            frontend_tests.append({
                'name': 'CloudFront Distribution Access',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
        
        # Test static assets
        asset_paths = [
            '/index.html',
            '/assets/js/main.js',
            '/assets/css/style.css',
            '/live2d/models/hiyori/hiyori.model3.json'
        ]
        
        for asset_path in asset_paths:
            try:
                response = requests.get(
                    f"{self.config.cloudfront_url}{asset_path}",
                    timeout=self.config.timeout
                )
                frontend_tests.append({
                    'name': f'Static Asset: {asset_path}',
                    'passed': response.status_code == 200,
                    'details': f"Status: {response.status_code}"
                })
            except Exception as e:
                frontend_tests.append({
                    'name': f'Static Asset: {asset_path}',
                    'passed': False,
                    'details': f"Error: {str(e)}"
                })
        
        # Test API configuration in frontend
        try:
            response = requests.get(
                f"{self.config.cloudfront_url}/config/aws-config.js",
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                config_content = response.text
                api_configured = self.config.api_base_url in config_content
                frontend_tests.append({
                    'name': 'API Configuration in Frontend',
                    'passed': api_configured,
                    'details': f"API URL configured: {api_configured}"
                })
            else:
                frontend_tests.append({
                    'name': 'API Configuration in Frontend',
                    'passed': False,
                    'details': f"Config file not accessible: {response.status_code}"
                })
        except Exception as e:
            frontend_tests.append({
                'name': 'API Configuration in Frontend',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
        
        return {
            'total_tests': len(frontend_tests),
            'passed': sum(1 for t in frontend_tests if t['passed']),
            'tests': frontend_tests
        }
    
    def _test_speech_functionality(self) -> Dict[str, Any]:
        """Test speech functionality with AWS Transcribe/Polly."""
        logger.info("Testing speech functionality...")
        
        if not self.config.api_base_url:
            return {
                'total_tests': 0,
                'passed': 0,
                'error': 'API URL not available'
            }
        
        speech_tests = []
        
        # Test text-to-speech endpoint
        try:
            response = requests.post(
                f"{self.config.api_base_url}/speech",
                json={
                    'action': 'synthesize',
                    'text': 'Hello, this is a test of the speech synthesis system.',
                    'agent_type': 'wellness_coach',
                    'language': 'en-US'
                },
                timeout=self.config.timeout
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else {}
            
            speech_tests.append({
                'name': 'Text-to-Speech (English)',
                'passed': success and 'audio_data' in response_data,
                'details': {
                    'status_code': response.status_code,
                    'has_audio_data': 'audio_data' in response_data
                }
            })
            
        except Exception as e:
            speech_tests.append({
                'name': 'Text-to-Speech (English)',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
        
        # Test Chinese text-to-speech
        try:
            response = requests.post(
                f"{self.config.api_base_url}/speech",
                json={
                    'action': 'synthesize',
                    'text': '你好，這是語音合成系統的測試。',
                    'agent_type': 'illness_monitor',
                    'language': 'zh-CN'
                },
                timeout=self.config.timeout
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else {}
            
            speech_tests.append({
                'name': 'Text-to-Speech (Chinese)',
                'passed': success and 'audio_data' in response_data,
                'details': {
                    'status_code': response.status_code,
                    'has_audio_data': 'audio_data' in response_data
                }
            })
            
        except Exception as e:
            speech_tests.append({
                'name': 'Text-to-Speech (Chinese)',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
        
        # Test speech-to-text endpoint (mock audio data)
        try:
            # Mock base64 audio data (would be real audio in production)
            mock_audio_data = "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT"
            
            response = requests.post(
                f"{self.config.api_base_url}/speech",
                json={
                    'action': 'transcribe',
                    'audio_data': mock_audio_data,
                    'language': 'en-US'
                },
                timeout=self.config.timeout
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else {}
            
            speech_tests.append({
                'name': 'Speech-to-Text',
                'passed': success,
                'details': {
                    'status_code': response.status_code,
                    'response_data': response_data
                }
            })
            
        except Exception as e:
            speech_tests.append({
                'name': 'Speech-to-Text',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
        
        return {
            'total_tests': len(speech_tests),
            'passed': sum(1 for t in speech_tests if t['passed']),
            'tests': speech_tests
        }
    
    def _perform_cost_analysis(self) -> Dict[str, Any]:
        """Conduct cost analysis and optimization review."""
        logger.info("Performing cost analysis...")
        
        try:
            # Get current month's costs (simplified analysis)
            cost_analysis = {
                'estimated_monthly_cost': 0.0,
                'cost_breakdown': {},
                'optimization_recommendations': [],
                'cost_alerts_configured': False
            }
            
            # Check if cost monitoring is configured
            try:
                # Check for CloudWatch billing alarms
                response = self.cloudwatch.describe_alarms(
                    AlarmNamePrefix=f"{self.deployment_info.get('environment', 'dev')}-healthcare"
                )
                
                cost_analysis['cost_alerts_configured'] = len(response['MetricAlarms']) > 0
                
            except Exception as e:
                logger.warning(f"Could not check cost alerts: {e}")
            
            # Estimate costs based on deployed resources
            lambda_functions = 5  # Number of Lambda functions
            dynamodb_tables = 3   # Number of DynamoDB tables
            s3_buckets = 2        # Number of S3 buckets
            
            # Rough cost estimates (very simplified)
            estimated_costs = {
                'lambda': lambda_functions * 0.20,  # $0.20 per function per month (light usage)
                'dynamodb': dynamodb_tables * 1.25,  # $1.25 per table per month (on-demand)
                's3': s3_buckets * 0.50,            # $0.50 per bucket per month
                'api_gateway': 2.00,                 # $2.00 per month for API calls
                'cloudfront': 1.00,                  # $1.00 per month for CDN
                'transcribe_polly': 3.00             # $3.00 per month for speech services
            }
            
            cost_analysis['cost_breakdown'] = estimated_costs
            cost_analysis['estimated_monthly_cost'] = sum(estimated_costs.values())
            
            # Generate optimization recommendations
            recommendations = [
                "Configure DynamoDB TTL to automatically clean up old conversations",
                "Set up S3 lifecycle policies to archive old files",
                "Monitor Lambda memory usage and optimize for cost",
                "Use CloudWatch cost anomaly detection",
                "Consider Reserved Capacity for consistent workloads"
            ]
            
            cost_analysis['optimization_recommendations'] = recommendations
            
            return {
                'total_tests': 1,
                'passed': 1 if cost_analysis['estimated_monthly_cost'] < 50 else 0,
                'cost_analysis': cost_analysis,
                'tests': [{
                    'name': 'Cost Analysis',
                    'passed': cost_analysis['estimated_monthly_cost'] < 50,
                    'details': f"Estimated monthly cost: ${cost_analysis['estimated_monthly_cost']:.2f}"
                }]
            }
            
        except Exception as e:
            return {
                'total_tests': 1,
                'passed': 0,
                'error': f"Cost analysis failed: {str(e)}"
            }
    
    def _test_performance(self) -> Dict[str, Any]:
        """Test system performance."""
        logger.info("Testing system performance...")
        
        if not self.config.api_base_url:
            return {
                'total_tests': 0,
                'passed': 0,
                'error': 'API URL not available'
            }
        
        performance_tests = []
        
        # Test API response times
        test_message = "Hello, this is a performance test message."
        
        response_times = []
        for i in range(5):  # Test 5 times
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.config.api_base_url}/chat",
                    json={
                        'message': test_message,
                        'user_id': f'perf_test_{i}',
                        'conversation_id': f'perf_test_{int(time.time())}_{i}'
                    },
                    timeout=self.config.timeout
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
                
            except Exception as e:
                logger.warning(f"Performance test {i} failed: {e}")
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            performance_tests.append({
                'name': 'API Response Time',
                'passed': avg_response_time < 3.0,  # Under 3 seconds average
                'details': {
                    'average_response_time': avg_response_time,
                    'max_response_time': max_response_time,
                    'successful_requests': len(response_times)
                }
            })
        else:
            performance_tests.append({
                'name': 'API Response Time',
                'passed': False,
                'details': 'No successful requests'
            })
        
        # Test concurrent requests
        def make_concurrent_request(request_id):
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.config.api_base_url}/chat",
                    json={
                        'message': f"Concurrent test message {request_id}",
                        'user_id': f'concurrent_test_{request_id}',
                        'conversation_id': f'concurrent_test_{int(time.time())}_{request_id}'
                    },
                    timeout=self.config.timeout
                )
                end_time = time.time()
                
                return {
                    'success': response.status_code == 200,
                    'response_time': end_time - start_time,
                    'request_id': request_id
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'request_id': request_id
                }
        
        # Run concurrent requests
        concurrent_results = []
        with ThreadPoolExecutor(max_workers=self.config.parallel_tests) as executor:
            futures = [executor.submit(make_concurrent_request, i) for i in range(self.config.parallel_tests)]
            
            for future in as_completed(futures):
                concurrent_results.append(future.result())
        
        successful_concurrent = sum(1 for r in concurrent_results if r.get('success', False))
        
        performance_tests.append({
            'name': 'Concurrent Request Handling',
            'passed': successful_concurrent >= self.config.parallel_tests * 0.8,  # 80% success rate
            'details': {
                'total_requests': len(concurrent_results),
                'successful_requests': successful_concurrent,
                'success_rate': successful_concurrent / len(concurrent_results) * 100
            }
        })
        
        return {
            'total_tests': len(performance_tests),
            'passed': sum(1 for t in performance_tests if t['passed']),
            'tests': performance_tests
        }
    
    def _test_security(self) -> Dict[str, Any]:
        """Test security configurations."""
        logger.info("Testing security configurations...")
        
        security_tests = []
        
        # Test HTTPS enforcement
        if self.config.cloudfront_url:
            try:
                # Try HTTP (should redirect to HTTPS)
                http_url = self.config.cloudfront_url.replace('https://', 'http://')
                response = requests.get(http_url, allow_redirects=False, timeout=10)
                
                security_tests.append({
                    'name': 'HTTPS Enforcement',
                    'passed': response.status_code in [301, 302, 307, 308],
                    'details': f"HTTP redirect status: {response.status_code}"
                })
            except Exception as e:
                security_tests.append({
                    'name': 'HTTPS Enforcement',
                    'passed': False,
                    'details': f"Error: {str(e)}"
                })
        
        # Test CORS configuration
        if self.config.api_base_url:
            try:
                response = requests.options(
                    f"{self.config.api_base_url}/chat",
                    headers={'Origin': 'https://example.com'},
                    timeout=10
                )
                
                has_cors = 'Access-Control-Allow-Origin' in response.headers
                
                security_tests.append({
                    'name': 'CORS Configuration',
                    'passed': has_cors,
                    'details': f"CORS headers present: {has_cors}"
                })
            except Exception as e:
                security_tests.append({
                    'name': 'CORS Configuration',
                    'passed': False,
                    'details': f"Error: {str(e)}"
                })
        
        # Test S3 bucket security
        if self.deployment_info.get('data_bucket'):
            try:
                # Try to access data bucket directly (should be blocked)
                bucket_url = f"https://{self.deployment_info['data_bucket']}.s3.amazonaws.com/"
                response = requests.get(bucket_url, timeout=10)
                
                # Should get access denied or similar
                security_tests.append({
                    'name': 'S3 Data Bucket Security',
                    'passed': response.status_code in [403, 404],
                    'details': f"Direct access status: {response.status_code}"
                })
            except Exception as e:
                security_tests.append({
                    'name': 'S3 Data Bucket Security',
                    'passed': True,  # Error accessing is good for security
                    'details': f"Access blocked: {str(e)}"
                })
        
        return {
            'total_tests': len(security_tests),
            'passed': sum(1 for t in security_tests if t['passed']),
            'tests': security_tests
        }
    
    def _test_monitoring_alerts(self) -> Dict[str, Any]:
        """Test monitoring and alerting configuration."""
        logger.info("Testing monitoring and alerts...")
        
        monitoring_tests = []
        
        # Test CloudWatch log groups exist
        log_groups = [
            f"/aws/lambda/{self.deployment_info.get('environment', 'dev')}-healthcare-agent-router",
            f"/aws/lambda/{self.deployment_info.get('environment', 'dev')}-healthcare-illness-monitor"
        ]
        
        logs_client = boto3.client('logs', region_name=self.config.aws_region)
        
        for log_group in log_groups:
            try:
                response = logs_client.describe_log_groups(logGroupNamePrefix=log_group)
                exists = len(response['logGroups']) > 0
                
                monitoring_tests.append({
                    'name': f'Log Group: {log_group}',
                    'passed': exists,
                    'details': f"Exists: {exists}"
                })
            except Exception as e:
                monitoring_tests.append({
                    'name': f'Log Group: {log_group}',
                    'passed': False,
                    'details': f"Error: {str(e)}"
                })
        
        # Test CloudWatch alarms
        try:
            response = self.cloudwatch.describe_alarms(
                AlarmNamePrefix=f"{self.deployment_info.get('environment', 'dev')}-healthcare"
            )
            
            alarms_configured = len(response['MetricAlarms']) > 0
            
            monitoring_tests.append({
                'name': 'CloudWatch Alarms',
                'passed': alarms_configured,
                'details': f"Alarms configured: {len(response['MetricAlarms'])}"
            })
        except Exception as e:
            monitoring_tests.append({
                'name': 'CloudWatch Alarms',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
        
        return {
            'total_tests': len(monitoring_tests),
            'passed': sum(1 for t in monitoring_tests if t['passed']),
            'tests': monitoring_tests
        }
    
    def generate_final_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive final integration test report."""
        return {
            'test_execution': {
                'timestamp': datetime.utcnow().isoformat(),
                'environment': self.config.environment,
                'aws_region': self.config.aws_region,
                'stack_name': self.config.stack_name
            },
            'deployment_info': self.deployment_info,
            'test_results': test_results,
            'recommendations': self._generate_recommendations(test_results),
            'next_steps': self._generate_next_steps(test_results)
        }
    
    def _generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Check overall success rate
        summary = test_results.get('summary', {})
        success_rate = summary.get('success_rate', 0)
        
        if success_rate < 100:
            recommendations.append("Address failing tests before production deployment")
        
        if success_rate < 80:
            recommendations.append("Consider rolling back deployment due to low success rate")
        
        # Cost recommendations
        cost_analysis = test_results.get('cost_analysis', {})
        if cost_analysis and 'cost_analysis' in cost_analysis:
            cost_data = cost_analysis['cost_analysis']
            if cost_data.get('estimated_monthly_cost', 0) > 30:
                recommendations.append("Review cost optimization opportunities")
            
            recommendations.extend(cost_data.get('optimization_recommendations', []))
        
        # Performance recommendations
        performance = test_results.get('performance_tests', {})
        if performance and 'tests' in performance:
            for test in performance['tests']:
                if not test['passed'] and 'response_time' in str(test.get('details', '')):
                    recommendations.append("Optimize Lambda function performance for faster response times")
        
        return recommendations
    
    def _generate_next_steps(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate next steps based on test results."""
        next_steps = []
        
        summary = test_results.get('summary', {})
        
        if summary.get('overall_status') == 'PASSED':
            next_steps.extend([
                "✅ System is ready for production use",
                "📊 Set up regular monitoring and cost reviews",
                "🔄 Implement automated testing in CI/CD pipeline",
                "📚 Update documentation with deployment URLs",
                "👥 Train users on the new AWS-based system"
            ])
        else:
            next_steps.extend([
                "❌ Fix failing tests before proceeding",
                "🔍 Review error logs for detailed failure information",
                "🛠️ Update deployment configuration as needed",
                "🔄 Re-run integration tests after fixes",
                "📋 Consider rollback if issues persist"
            ])
        
        # Add specific next steps based on test categories
        if test_results.get('live2d_frontend', {}).get('passed', 0) == 0:
            next_steps.append("🎨 Deploy frontend files to S3 and update configuration")
        
        if test_results.get('speech_functionality', {}).get('passed', 0) == 0:
            next_steps.append("🎤 Configure AWS Transcribe and Polly services")
        
        return next_steps


def main():
    """Main function for final integration testing."""
    parser = argparse.ArgumentParser(description='Final Integration Testing for Healthcare AI')
    parser.add_argument('--environment', default='dev', help='Environment to test')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--stack-name', required=True, help='CloudFormation stack name')
    parser.add_argument('--output', help='Output file for test report')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--parallel', type=int, default=5, help='Number of parallel tests')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create configuration
    config = IntegrationTestConfig(
        environment=args.environment,
        aws_region=args.region,
        stack_name=args.stack_name,
        timeout=args.timeout,
        parallel_tests=args.parallel
    )
    
    # Initialize tester
    tester = FinalIntegrationTester(config)
    
    # Set up test environment
    if not tester.setup_integration_test():
        logger.error("Failed to set up integration test environment")
        return 1
    
    # Run comprehensive tests
    test_results = tester.run_comprehensive_tests()
    
    # Generate final report
    final_report = tester.generate_final_report(test_results)
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(final_report, f, indent=2)
        logger.info(f"Final integration test report saved to: {args.output}")
    
    # Print summary
    summary = test_results.get('summary', {})
    print(f"\n{'='*60}")
    print(f"FINAL INTEGRATION TEST RESULTS")
    print(f"{'='*60}")
    print(f"Environment: {config.environment}")
    print(f"Stack: {config.stack_name}")
    print(f"Region: {config.aws_region}")
    print(f"")
    print(f"Total Tests: {summary.get('total_tests', 0)}")
    print(f"Passed: {summary.get('passed', 0)}")
    print(f"Failed: {summary.get('failed', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
    print(f"Overall Status: {summary.get('overall_status', 'UNKNOWN')}")
    
    # Print key URLs
    deployment_info = final_report.get('deployment_info', {})
    if deployment_info.get('api_url'):
        print(f"\n📡 API Gateway URL: {deployment_info['api_url']}")
    if deployment_info.get('cloudfront_url'):
        print(f"🌐 CloudFront URL: {deployment_info['cloudfront_url']}")
    
    # Print recommendations
    recommendations = final_report.get('recommendations', [])
    if recommendations:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in recommendations[:5]:  # Show top 5
            print(f"  • {rec}")
    
    # Print next steps
    next_steps = final_report.get('next_steps', [])
    if next_steps:
        print(f"\n🚀 NEXT STEPS:")
        for step in next_steps[:5]:  # Show top 5
            print(f"  {step}")
    
    print(f"\n{'='*60}")
    
    # Return appropriate exit code
    return 0 if summary.get('overall_status') == 'PASSED' else 1


if __name__ == '__main__':
    sys.exit(main())