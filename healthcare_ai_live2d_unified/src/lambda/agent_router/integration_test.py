#!/usr/bin/env python3
"""
Agent Router Integration Test
============================

Integration test to verify Agent Router works with AWS infrastructure.
"""

import json
import boto3
import sys
import time
from typing import Dict, Any

def test_lambda_integration(environment: str = 'dev'):
    """Test Agent Router Lambda integration with AWS."""
    
    print(f"Testing Agent Router Lambda integration for environment: {environment}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda')
    
    function_name = f"{environment}-healthcare-agent-router"
    
    # Test cases
    test_cases = [
        {
            'name': 'Physical Health Query',
            'payload': {
                'message': 'I have a severe headache and feel nauseous',
                'user_id': 'integration_test_user_1',
                'conversation_id': 'integration_test_conv_1'
            },
            'expected_agent': 'illness_monitor'
        },
        {
            'name': 'Mental Health Query',
            'payload': {
                'message': 'I feel very anxious and stressed about work',
                'user_id': 'integration_test_user_2',
                'conversation_id': 'integration_test_conv_2'
            },
            'expected_agent': 'mental_health'
        },
        {
            'name': 'Emergency Query',
            'payload': {
                'message': 'Emergency! I can\'t breathe properly!',
                'user_id': 'integration_test_user_3',
                'conversation_id': 'integration_test_conv_3'
            },
            'expected_agent': 'safety_guardian'
        },
        {
            'name': 'Wellness Query',
            'payload': {
                'message': 'I want to start exercising and eating healthier',
                'user_id': 'integration_test_user_4',
                'conversation_id': 'integration_test_conv_4'
            },
            'expected_agent': 'wellness_coach'
        },
        {
            'name': 'Manual Agent Selection',
            'payload': {
                'message': 'General health question',
                'user_id': 'integration_test_user_5',
                'conversation_id': 'integration_test_conv_5',
                'preferred_agent': 'mental_health'
            },
            'expected_agent': 'mental_health'
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        print(f"Message: {test_case['payload']['message']}")
        
        try:
            # Invoke Lambda function
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_case['payload'])
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read().decode())
            
            if response.get('StatusCode') == 200:
                if 'body' in response_payload:
                    body = json.loads(response_payload['body'])
                else:
                    body = response_payload
                
                selected_agent = body.get('agent', 'unknown')
                ai_response = body.get('response', 'No response')
                confidence = body.get('routing_info', {}).get('confidence', 0.0)
                
                print(f"✅ Lambda invocation successful")
                print(f"Selected Agent: {selected_agent}")
                print(f"Confidence: {confidence}")
                print(f"Response: {ai_response[:100]}...")
                
                # Check if correct agent was selected
                if selected_agent == test_case['expected_agent']:
                    print(f"✅ Correct agent selected")
                    test_result = 'PASS'
                else:
                    print(f"❌ Wrong agent - Expected: {test_case['expected_agent']}, Got: {selected_agent}")
                    test_result = 'FAIL'
                
                results.append({
                    'test': test_case['name'],
                    'result': test_result,
                    'selected_agent': selected_agent,
                    'expected_agent': test_case['expected_agent'],
                    'confidence': confidence
                })
                
            else:
                print(f"❌ Lambda invocation failed: {response_payload}")
                results.append({
                    'test': test_case['name'],
                    'result': 'FAIL',
                    'error': str(response_payload)
                })
                
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            results.append({
                'test': test_case['name'],
                'result': 'ERROR',
                'error': str(e)
            })
        
        # Small delay between tests
        time.sleep(1)
    
    # Print summary
    print("\n" + "="*60)
    print("INTEGRATION TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results if r['result'] == 'PASS')
    failed = sum(1 for r in results if r['result'] in ['FAIL', 'ERROR'])
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(results)*100):.1f}%")
    
    print("\nDetailed Results:")
    for result in results:
        status_icon = "✅" if result['result'] == 'PASS' else "❌"
        print(f"{status_icon} {result['test']}: {result['result']}")
        if 'selected_agent' in result:
            print(f"   Agent: {result['selected_agent']} (expected: {result['expected_agent']})")
        if 'error' in result:
            print(f"   Error: {result['error']}")
    
    return passed == len(results)

def test_api_gateway_integration(environment: str = 'dev'):
    """Test Agent Router through API Gateway."""
    
    print(f"\n{'='*60}")
    print("TESTING API GATEWAY INTEGRATION")
    print("="*60)
    
    # Get API Gateway URL from CloudFormation outputs
    try:
        cf_client = boto3.client('cloudformation')
        stack_name = f"{environment}-healthcare-ai-stack"
        
        response = cf_client.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0]['Outputs']
        
        api_url = None
        for output in outputs:
            if output['OutputKey'] == 'APIGatewayURL':
                api_url = output['OutputValue']
                break
        
        if not api_url:
            print("❌ Could not find API Gateway URL in CloudFormation outputs")
            return False
        
        print(f"API Gateway URL: {api_url}")
        
        # Test API Gateway endpoint
        import requests
        
        test_payload = {
            'message': 'I have a headache',
            'user_id': 'api_test_user'
        }
        
        response = requests.post(
            f"{api_url}/chat",
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Gateway test successful")
            print(f"Selected Agent: {data.get('agent')}")
            print(f"Response: {data.get('response', '')[:100]}...")
            return True
        else:
            print(f"❌ API Gateway test failed: {response.status_code} - {response.text}")
            return False
            
    except ImportError:
        print("⚠️  Skipping API Gateway test - requests library not available")
        print("   Install with: pip install requests")
        return True
    except Exception as e:
        print(f"❌ API Gateway test failed: {str(e)}")
        return False

def main():
    """Run integration tests."""
    
    # Get environment from command line
    environment = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    
    print("Agent Router Integration Test Suite")
    print("="*60)
    print(f"Environment: {environment}")
    
    try:
        # Test Lambda integration
        lambda_success = test_lambda_integration(environment)
        
        # Test API Gateway integration
        api_success = test_api_gateway_integration(environment)
        
        # Overall result
        if lambda_success and api_success:
            print(f"\n🎉 All integration tests passed!")
            sys.exit(0)
        else:
            print(f"\n❌ Some integration tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Integration test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()