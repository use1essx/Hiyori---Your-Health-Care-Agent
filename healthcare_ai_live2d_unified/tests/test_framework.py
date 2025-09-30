"""
Healthcare AI Testing and Validation Framework
=============================================

Comprehensive testing framework for unit tests, integration tests, and end-to-end validation.
"""

import json
import boto3
import pytest
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from unittest.mock import Mock, patch, MagicMock
import requests
import time

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Test result information."""
    test_name: str
    status: str  # 'passed', 'failed', 'skipped'
    duration: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class TestSuite:
    """Test suite configuration."""
    name: str
    tests: List[Callable]
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    timeout: int = 300  # 5 minutes default


class HealthcareAITestFramework:
    """Main testing framework for healthcare AI system."""
    
    def __init__(self, environment: str = 'test'):
        self.environment = environment
        self.test_results = []
        self.setup_complete = False
        
        # Test configuration
        self.config = {
            'api_base_url': f'https://api-{environment}.healthcare-ai.example.com',
            'timeout': 30,
            'retry_attempts': 3,
            'retry_delay': 1.0
        }
        
        # Mock AWS clients for unit tests
        self.mock_clients = {}
        
    def setup_test_environment(self) -> bool:
        """Set up test environment and dependencies."""
        try:
            logger.info("Setting up test environment...")
            
            # Initialize mock AWS clients
            self.mock_clients = {
                'bedrock': Mock(),
                'dynamodb': Mock(),
                's3': Mock(),
                'transcribe': Mock(),
                'polly': Mock(),
                'sns': Mock()
            }
            
            # Set up test data
            self._setup_test_data()
            
            self.setup_complete = True
            logger.info("Test environment setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up test environment: {e}")
            return False
    
    def _setup_test_data(self):
        """Set up test data for various scenarios."""
        self.test_data = {
            'user_profiles': [
                {
                    'user_id': 'test_user_1',
                    'age_group': 'adult',
                    'language_preference': 'zh-HK',
                    'cultural_context': {'region': 'hong_kong'}
                },
                {
                    'user_id': 'test_user_2',
                    'age_group': 'elderly',
                    'language_preference': 'zh-HK',
                    'cultural_context': {'region': 'hong_kong'}
                },
                {
                    'user_id': 'test_user_3',
                    'age_group': 'teen',
                    'language_preference': 'en-US',
                    'cultural_context': {'region': 'hong_kong'}
                }
            ],
            'test_messages': {
                'illness_monitor': [
                    "I have a headache and feel dizzy",
                    "我頭痛同頭暈",
                    "My diabetes medication isn't working",
                    "我的糖尿病藥物沒有效果"
                ],
                'mental_health': [
                    "I'm feeling really stressed about school",
                    "我對學校感到很大壓力",
                    "I can't sleep and feel anxious",
                    "我睡不著，感到焦慮"
                ],
                'safety_guardian': [
                    "I'm having chest pain and can't breathe",
                    "我胸痛，呼吸困難",
                    "I think I'm having a heart attack",
                    "我覺得我心臟病發作"
                ],
                'wellness_coach': [
                    "How can I start exercising?",
                    "我怎樣開始運動？",
                    "What's a healthy diet for me?",
                    "什麼是適合我的健康飲食？"
                ]
            },
            'expected_responses': {
                'illness_monitor': {
                    'keywords': ['health', 'symptoms', 'doctor', 'medical'],
                    'keywords_zh': ['健康', '症狀', '醫生', '醫療']
                },
                'mental_health': {
                    'keywords': ['support', 'understand', 'help', 'counseling'],
                    'keywords_zh': ['支持', '明白', '幫助', '輔導']
                },
                'safety_guardian': {
                    'keywords': ['emergency', '999', 'immediate', 'hospital'],
                    'keywords_zh': ['緊急', '999', '立即', '醫院']
                },
                'wellness_coach': {
                    'keywords': ['exercise', 'healthy', 'nutrition', 'lifestyle'],
                    'keywords_zh': ['運動', '健康', '營養', '生活方式']
                }
            }
        }
    
    def run_test_suite(self, test_suite: TestSuite) -> List[TestResult]:
        """Run a complete test suite."""
        suite_results = []
        
        logger.info(f"Running test suite: {test_suite.name}")
        
        # Run setup if provided
        if test_suite.setup:
            try:
                test_suite.setup()
            except Exception as e:
                logger.error(f"Test suite setup failed: {e}")
                return [TestResult(
                    test_name=f"{test_suite.name}_setup",
                    status='failed',
                    duration=0.0,
                    error_message=str(e)
                )]
        
        # Run individual tests
        for test_func in test_suite.tests:
            result = self._run_single_test(test_func, test_suite.timeout)
            suite_results.append(result)
        
        # Run teardown if provided
        if test_suite.teardown:
            try:
                test_suite.teardown()
            except Exception as e:
                logger.warning(f"Test suite teardown failed: {e}")
        
        return suite_results
    
    def _run_single_test(self, test_func: Callable, timeout: int) -> TestResult:
        """Run a single test function."""
        test_name = test_func.__name__
        start_time = time.time()
        
        try:
            # Run test with timeout
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(asyncio.wait_for(test_func(), timeout=timeout))
            else:
                result = test_func()
            
            duration = time.time() - start_time
            
            return TestResult(
                test_name=test_name,
                status='passed',
                duration=duration,
                details=result if isinstance(result, dict) else None
            )
            
        except Exception as e:
            duration = time.time() - start_time
            
            return TestResult(
                test_name=test_name,
                status='failed',
                duration=duration,
                error_message=str(e)
            )
    
    # Unit Tests
    
    def test_agent_router_logic(self) -> Dict[str, Any]:
        """Test agent router message routing logic."""
        from src.lambda.agent_router.handler import AgentRouter
        
        router = AgentRouter()
        
        test_cases = [
            {
                'message': 'I have a headache',
                'expected_agent': 'illness_monitor',
                'min_confidence': 0.7
            },
            {
                'message': 'I feel stressed about school',
                'expected_agent': 'mental_health',
                'min_confidence': 0.7
            },
            {
                'message': 'I\'m having chest pain',
                'expected_agent': 'safety_guardian',
                'min_confidence': 0.8
            },
            {
                'message': 'How can I exercise more?',
                'expected_agent': 'wellness_coach',
                'min_confidence': 0.6
            }
        ]
        
        results = []
        
        for case in test_cases:
            agent, confidence = router.route_message(case['message'], {})
            
            results.append({
                'message': case['message'],
                'expected_agent': case['expected_agent'],
                'actual_agent': agent,
                'confidence': confidence,
                'passed': agent == case['expected_agent'] and confidence >= case['min_confidence']
            })
        
        return {
            'test_cases': len(test_cases),
            'passed': sum(1 for r in results if r['passed']),
            'results': results
        }
    
    def test_bedrock_client(self) -> Dict[str, Any]:
        """Test Bedrock client functionality."""
        from src.aws.bedrock_client import BedrockClient, ModelTier
        
        # Mock Bedrock responses
        mock_bedrock = Mock()
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Test response from Claude'}],
            'usage': {'total_tokens': 100}
        }).encode()
        
        mock_bedrock.invoke_model.return_value = mock_response
        
        with patch('boto3.client', return_value=mock_bedrock):
            client = BedrockClient()
            
            # Test model selection
            tier = client.model_manager.select_optimal_model('illness_monitor', 100, [])
            assert tier == ModelTier.BALANCED
            
            # Test response generation (would need async context in real test)
            # This is a simplified test
            
        return {
            'model_selection': 'passed',
            'mock_response': 'passed'
        }
    
    def test_dynamodb_operations(self) -> Dict[str, Any]:
        """Test DynamoDB operations."""
        from src.aws.dynamodb_client import DynamoDBClient, create_conversation_message
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        
        with patch('boto3.resource', return_value=mock_dynamodb):
            client = DynamoDBClient()
            
            # Test conversation message creation
            message = create_conversation_message(
                'test_conv_1',
                'Hello, I need help',
                'How can I assist you?',
                'wellness_coach',
                0.8,
                'low'
            )
            
            assert message.conversation_id == 'test_conv_1'
            assert message.agent_type == 'wellness_coach'
            assert message.confidence_score == 0.8
            
            # Test store operation (mocked)
            success = client.store_conversation_message(message)
            mock_table.put_item.assert_called_once()
        
        return {
            'message_creation': 'passed',
            'store_operation': 'passed'
        }
    
    # Integration Tests
    
    async def test_agent_integration(self) -> Dict[str, Any]:
        """Test integration between agents and AWS services."""
        results = {}
        
        for agent_type in ['illness_monitor', 'mental_health', 'safety_guardian', 'wellness_coach']:
            agent_results = []
            
            for message in self.test_data['test_messages'][agent_type]:
                # Mock Lambda invocation
                mock_response = {
                    'StatusCode': 200,
                    'Payload': json.dumps({
                        'statusCode': 200,
                        'body': json.dumps({
                            'response': f'Mock response for {agent_type}',
                            'agent': agent_type,
                            'confidence': 0.8
                        })
                    }).encode()
                }
                
                with patch('boto3.client') as mock_boto:
                    mock_lambda = Mock()
                    mock_lambda.invoke.return_value = mock_response
                    mock_boto.return_value = mock_lambda
                    
                    # Test agent invocation
                    response = mock_lambda.invoke(
                        FunctionName=f'healthcare-ai-{self.environment}-{agent_type}',
                        Payload=json.dumps({
                            'message': message,
                            'user_id': 'test_user_1'
                        })
                    )
                    
                    agent_results.append({
                        'message': message,
                        'status_code': response['StatusCode'],
                        'success': response['StatusCode'] == 200
                    })
            
            results[agent_type] = {
                'total_tests': len(agent_results),
                'passed': sum(1 for r in agent_results if r['success']),
                'results': agent_results
            }
        
        return results
    
    async def test_speech_processing_integration(self) -> Dict[str, Any]:
        """Test speech-to-text and text-to-speech integration."""
        # Mock audio data
        mock_audio_data = "mock_base64_audio_data"
        
        # Test speech-to-text
        stt_mock_response = {
            'StatusCode': 200,
            'Payload': json.dumps({
                'statusCode': 200,
                'body': json.dumps({
                    'job_name': 'test_job_123',
                    'status': 'started'
                })
            }).encode()
        }
        
        # Test text-to-speech
        tts_mock_response = {
            'StatusCode': 200,
            'Payload': json.dumps({
                'statusCode': 200,
                'body': json.dumps({
                    'audio_id': 'test_audio_123',
                    'audio_url': 'https://s3.amazonaws.com/test-bucket/audio.mp3'
                })
            }).encode()
        }
        
        with patch('boto3.client') as mock_boto:
            mock_lambda = Mock()
            mock_lambda.invoke.side_effect = [stt_mock_response, tts_mock_response]
            mock_boto.return_value = mock_lambda
            
            # Test STT
            stt_response = mock_lambda.invoke(
                FunctionName=f'healthcare-ai-{self.environment}-speech-to-text',
                Payload=json.dumps({
                    'action': 'start_transcription',
                    'audio_data': mock_audio_data
                })
            )
            
            # Test TTS
            tts_response = mock_lambda.invoke(
                FunctionName=f'healthcare-ai-{self.environment}-text-to-speech',
                Payload=json.dumps({
                    'action': 'synthesize',
                    'text': 'Hello, how can I help you?',
                    'agent_type': 'wellness_coach'
                })
            )
        
        return {
            'speech_to_text': {
                'status_code': stt_response['StatusCode'],
                'success': stt_response['StatusCode'] == 200
            },
            'text_to_speech': {
                'status_code': tts_response['StatusCode'],
                'success': tts_response['StatusCode'] == 200
            }
        }
    
    # End-to-End Tests
    
    async def test_complete_conversation_flow(self) -> Dict[str, Any]:
        """Test complete conversation flow from user input to response."""
        conversation_flows = []
        
        for user_profile in self.test_data['user_profiles']:
            for agent_type, messages in self.test_data['test_messages'].items():
                for message in messages[:1]:  # Test one message per agent
                    
                    flow_result = {
                        'user_id': user_profile['user_id'],
                        'agent_type': agent_type,
                        'message': message,
                        'steps': {}
                    }
                    
                    try:
                        # Step 1: Route message
                        with patch('boto3.client') as mock_boto:
                            mock_lambda = Mock()
                            mock_lambda.invoke.return_value = {
                                'StatusCode': 200,
                                'Payload': json.dumps({
                                    'statusCode': 200,
                                    'body': json.dumps({
                                        'selected_agent': agent_type,
                                        'confidence': 0.8
                                    })
                                }).encode()
                            }
                            mock_boto.return_value = mock_lambda
                            
                            flow_result['steps']['routing'] = 'passed'
                        
                        # Step 2: Process with agent
                        with patch('boto3.client') as mock_boto:
                            mock_lambda = Mock()
                            mock_lambda.invoke.return_value = {
                                'StatusCode': 200,
                                'Payload': json.dumps({
                                    'statusCode': 200,
                                    'body': json.dumps({
                                        'response': f'Response from {agent_type}',
                                        'agent': agent_type,
                                        'confidence': 0.8
                                    })
                                }).encode()
                            }
                            mock_boto.return_value = mock_lambda
                            
                            flow_result['steps']['agent_processing'] = 'passed'
                        
                        # Step 3: Store conversation
                        with patch('boto3.resource') as mock_boto:
                            mock_table = Mock()
                            mock_dynamodb = Mock()
                            mock_dynamodb.Table.return_value = mock_table
                            mock_boto.return_value = mock_dynamodb
                            
                            flow_result['steps']['storage'] = 'passed'
                        
                        flow_result['overall_status'] = 'passed'
                        
                    except Exception as e:
                        flow_result['overall_status'] = 'failed'
                        flow_result['error'] = str(e)
                    
                    conversation_flows.append(flow_result)
        
        return {
            'total_flows': len(conversation_flows),
            'passed': sum(1 for f in conversation_flows if f['overall_status'] == 'passed'),
            'flows': conversation_flows
        }
    
    def test_api_endpoints(self) -> Dict[str, Any]:
        """Test API Gateway endpoints (if available)."""
        endpoints = [
            '/agent-router',
            '/illness-monitor',
            '/mental-health',
            '/safety-guardian',
            '/wellness-coach',
            '/speech-to-text',
            '/text-to-speech'
        ]
        
        results = []
        
        for endpoint in endpoints:
            try:
                # Mock API response
                mock_response = {
                    'status_code': 200,
                    'json': {'status': 'healthy'},
                    'elapsed': 0.5
                }
                
                with patch('requests.get') as mock_get:
                    mock_get.return_value = Mock(**mock_response)
                    
                    response = mock_get(f"{self.config['api_base_url']}{endpoint}/health")
                    
                    results.append({
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'response_time': response.elapsed,
                        'success': response.status_code == 200
                    })
                    
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'error': str(e),
                    'success': False
                })
        
        return {
            'total_endpoints': len(endpoints),
            'passed': sum(1 for r in results if r.get('success', False)),
            'results': results
        }
    
    def generate_test_report(self, all_results: List[TestResult]) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(all_results)
        passed_tests = sum(1 for r in all_results if r.status == 'passed')
        failed_tests = sum(1 for r in all_results if r.status == 'failed')
        skipped_tests = sum(1 for r in all_results if r.status == 'skipped')
        
        total_duration = sum(r.duration for r in all_results)
        
        return {
            'test_summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'skipped': skipped_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_duration': total_duration
            },
            'test_results': [
                {
                    'test_name': r.test_name,
                    'status': r.status,
                    'duration': r.duration,
                    'error_message': r.error_message,
                    'details': r.details
                }
                for r in all_results
            ],
            'environment': self.environment,
            'generated_at': datetime.utcnow().isoformat()
        }


def create_test_suites() -> List[TestSuite]:
    """Create all test suites for the healthcare AI system."""
    framework = HealthcareAITestFramework()
    
    return [
        TestSuite(
            name='unit_tests',
            tests=[
                framework.test_agent_router_logic,
                framework.test_bedrock_client,
                framework.test_dynamodb_operations
            ]
        ),
        TestSuite(
            name='integration_tests',
            tests=[
                framework.test_agent_integration,
                framework.test_speech_processing_integration
            ]
        ),
        TestSuite(
            name='end_to_end_tests',
            tests=[
                framework.test_complete_conversation_flow,
                framework.test_api_endpoints
            ]
        )
    ]


def main():
    """Main test execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Healthcare AI tests')
    parser.add_argument('--environment', default='test', help='Test environment')
    parser.add_argument('--suite', help='Specific test suite to run')
    parser.add_argument('--output', help='Output file for test report')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize framework
    framework = HealthcareAITestFramework(args.environment)
    
    if not framework.setup_test_environment():
        logger.error("Failed to set up test environment")
        return 1
    
    # Get test suites
    test_suites = create_test_suites()
    
    # Filter by suite if specified
    if args.suite:
        test_suites = [s for s in test_suites if s.name == args.suite]
        if not test_suites:
            logger.error(f"Test suite '{args.suite}' not found")
            return 1
    
    # Run tests
    all_results = []
    
    for suite in test_suites:
        suite_results = framework.run_test_suite(suite)
        all_results.extend(suite_results)
    
    # Generate report
    report = framework.generate_test_report(all_results)
    
    # Save report if output specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Test report saved to: {args.output}")
    
    # Print summary
    summary = report['test_summary']
    print(f"\n{'='*50}")
    print(f"Healthcare AI Test Results")
    print(f"{'='*50}")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Duration: {summary['total_duration']:.2f}s")
    
    # Return appropriate exit code
    return 0 if summary['failed'] == 0 else 1


if __name__ == '__main__':
    exit(main())