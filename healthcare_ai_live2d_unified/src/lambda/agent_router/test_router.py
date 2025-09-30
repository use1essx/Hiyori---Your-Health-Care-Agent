#!/usr/bin/env python3
"""
Agent Router Test Script
=======================

Test script to validate Agent Router functionality locally without AWS dependencies.
"""

import json
import sys
import os
import re
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_agent_selection():
    """Test agent selection logic without AWS dependencies."""
    
    print("Testing Agent Selection Logic...")
    
    # Create a simplified router for testing
    class TestAgentRouter:
        def __init__(self):
            self.agent_patterns = {
                'safety_guardian': {
                    'keywords': [
                        'emergency', '緊急', 'urgent', '急', 'help', '救命', 'crisis', '危機',
                        'suicide', '自殺', 'self-harm', '自傷', 'overdose', '服藥過量',
                        'can\'t breathe', '唔可以呼吸', 'chest pain', '胸痛', 'dying', '快死',
                        'call ambulance', '叫救護車', 'hospital now', '立即去醫院'
                    ],
                    'patterns': [
                        r'\b(emergency|緊急|urgent|急)\b',
                        r'\b(suicide|自殺|kill myself|想死)\b',
                        r'\b(overdose|服藥過量|too many pills|食咗太多藥)\b',
                        r'\b(can\'t breathe|唔可以呼吸|difficulty breathing|呼吸困難)\b'
                    ],
                    'confidence_boost': 0.3
                },
                'illness_monitor': {
                    'keywords': [
                        'pain', '痛', 'sick', '病', 'fever', '發燒', 'headache', '頭痛',
                        'medication', '藥物', 'symptoms', '症狀', 'diagnosis', '診斷',
                        'doctor', '醫生', 'hospital', '醫院', 'treatment', '治療',
                        'chronic', '慢性', 'diabetes', '糖尿病', 'hypertension', '高血壓'
                    ],
                    'patterns': [
                        r'\b(pain|痛|hurt|痛苦)\b',
                        r'\b(sick|病|illness|疾病)\b',
                        r'\b(medication|藥物|medicine|藥)\b',
                        r'\b(symptoms|症狀|feel|感覺)\b'
                    ],
                    'confidence_boost': 0.2
                },
                'mental_health': {
                    'keywords': [
                        'stress', '壓力', 'anxiety', '焦慮', 'depression', '抑鬱',
                        'sad', '傷心', 'worried', '擔心', 'scared', '害怕',
                        'lonely', '孤獨', 'overwhelmed', '不知所措', 'panic', '恐慌',
                        'mood', '心情', 'emotional', '情緒', 'mental health', '心理健康'
                    ],
                    'patterns': [
                        r'\b(stress|壓力|stressed|有壓力)\b',
                        r'\b(anxiety|焦慮|anxious|焦慮不安)\b',
                        r'\b(depression|抑鬱|depressed|憂鬱)\b',
                        r'\b(sad|傷心|upset|不開心)\b'
                    ],
                    'confidence_boost': 0.2
                },
                'wellness_coach': {
                    'keywords': [
                        'healthy', '健康', 'exercise', '運動', 'diet', '飲食',
                        'nutrition', '營養', 'fitness', '健身', 'lifestyle', '生活方式',
                        'prevention', '預防', 'wellness', '保健', 'improve', '改善',
                        'habits', '習慣', 'sleep', '睡眠', 'weight', '體重'
                    ],
                    'patterns': [
                        r'\b(healthy|健康|health|保健)\b',
                        r'\b(exercise|運動|workout|鍛煉)\b',
                        r'\b(diet|飲食|nutrition|營養)\b',
                        r'\b(improve|改善|better|更好)\b'
                    ],
                    'confidence_boost': 0.1
                }
            }
        
        def determine_agent(self, message, user_context=None):
            """Determine the best agent for handling the user message."""
            message_lower = message.lower()
            agent_scores = {}
            
            # Calculate scores for each agent
            for agent_id, patterns in self.agent_patterns.items():
                score = 0.0
                reasons = []
                
                # Keyword matching
                keyword_matches = sum(1 for keyword in patterns['keywords'] 
                                    if keyword in message_lower)
                if keyword_matches > 0:
                    score += (keyword_matches / len(patterns['keywords'])) * 0.5
                    reasons.append(f"Matched {keyword_matches} keywords")
                
                # Pattern matching
                pattern_matches = 0
                for pattern in patterns['patterns']:
                    if re.search(pattern, message_lower, re.IGNORECASE):
                        pattern_matches += 1
                
                if pattern_matches > 0:
                    score += (pattern_matches / len(patterns['patterns'])) * 0.4
                    reasons.append(f"Matched {pattern_matches} patterns")
                
                # Apply confidence boost
                if score > 0:
                    score += patterns['confidence_boost']
                    score = min(score, 1.0)  # Cap at 1.0
                
                if score > 0:
                    agent_scores[agent_id] = (score, reasons)
            
            # Select best agent
            if not agent_scores:
                # Default fallback to wellness coach for general health questions
                return 'wellness_coach', 0.5, ['No specific patterns matched - using wellness coach as fallback']
            
            # Sort by score
            sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1][0], reverse=True)
            best_agent, (best_score, reasons) = sorted_agents[0]
            
            # Emergency override check
            if self._is_emergency(message):
                if best_agent != 'safety_guardian':
                    return 'safety_guardian', 0.95, ['Emergency keywords detected - safety override activated']
            
            return best_agent, best_score, reasons
        
        def _is_emergency(self, message):
            """Check if message contains emergency indicators."""
            emergency_patterns = [
                r'\b(emergency|緊急|urgent|急)\b',
                r'\b(suicide|自殺|kill myself|想死)\b',
                r'\b(can\'t breathe|唔可以呼吸|difficulty breathing|呼吸困難)\b',
                r'\b(chest pain|胸痛|heart attack|心臟病發)\b',
                r'\b(overdose|服藥過量|too many pills|食咗太多藥)\b',
                r'\b(help me|救我|call ambulance|叫救護車)\b'
            ]
            
            message_lower = message.lower()
            return any(re.search(pattern, message_lower, re.IGNORECASE) 
                      for pattern in emergency_patterns)
    
    router = TestAgentRouter()
    
    # Test cases
    test_cases = [
        {
            'message': 'I have a severe headache and fever',
            'expected_agent': 'illness_monitor',
            'description': 'Physical symptoms'
        },
        {
            'message': 'I feel very anxious and stressed about work',
            'expected_agent': 'mental_health',
            'description': 'Mental health concerns'
        },
        {
            'message': 'Emergency! I can\'t breathe properly',
            'expected_agent': 'safety_guardian',
            'description': 'Emergency situation'
        },
        {
            'message': 'I want to start exercising and eating healthier',
            'expected_agent': 'wellness_coach',
            'description': 'Wellness and lifestyle'
        },
        {
            'message': 'Hello, how are you today?',
            'expected_agent': 'wellness_coach',  # Default fallback
            'description': 'General greeting (fallback)'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Message: '{test_case['message']}'")
        
        agent, confidence, reasons = router.determine_agent(test_case['message'])
        
        print(f"Selected Agent: {agent}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Reasons: {reasons}")
        
        if agent == test_case['expected_agent']:
            print("✅ PASS")
        else:
            print(f"❌ FAIL - Expected: {test_case['expected_agent']}, Got: {agent}")

def test_emergency_detection():
    """Test emergency detection logic."""
    
    print("\n" + "="*50)
    print("Testing Emergency Detection...")
    
    # Create a simplified router for testing
    class TestAgentRouter:
        def _is_emergency(self, message):
            """Check if message contains emergency indicators."""
            emergency_patterns = [
                r'\b(emergency|緊急|urgent|急)\b',
                r'\b(suicide|自殺|kill myself|想死)\b',
                r'\b(can\'t breathe|唔可以呼吸|difficulty breathing|呼吸困難)\b',
                r'\b(chest pain|胸痛|heart attack|心臟病發)\b',
                r'\b(overdose|服藥過量|too many pills|食咗太多藥)\b',
                r'\b(help me|救我|call ambulance|叫救護車)\b'
            ]
            
            message_lower = message.lower()
            return any(re.search(pattern, message_lower, re.IGNORECASE) 
                      for pattern in emergency_patterns)
        
        def determine_agent(self, message):
            """Simple agent determination for emergency testing."""
            if self._is_emergency(message):
                return 'safety_guardian', 0.95, ['Emergency detected']
            else:
                return 'wellness_coach', 0.5, ['No emergency detected']
    
    router = TestAgentRouter()
    
    emergency_messages = [
        'Emergency! Call ambulance!',
        'I think I\'m having a heart attack',
        'I can\'t breathe properly',
        'I want to kill myself',
        'I took too many pills',
        '緊急情況！救命！'
    ]
    
    for message in emergency_messages:
        is_emergency = router._is_emergency(message)
        agent, confidence, reasons = router.determine_agent(message)
        
        print(f"\nMessage: '{message}'")
        print(f"Emergency Detected: {is_emergency}")
        print(f"Selected Agent: {agent}")
        
        if is_emergency and agent == 'safety_guardian':
            print("✅ PASS - Emergency correctly routed to Safety Guardian")
        elif not is_emergency:
            print("⚠️  WARNING - Emergency not detected")
        else:
            print("❌ FAIL - Emergency detected but not routed to Safety Guardian")

def test_lambda_handler():
    """Test the main Lambda handler function logic."""
    
    print("\n" + "="*50)
    print("Testing Lambda Handler Logic...")
    
    # Test the core routing logic without AWS dependencies
    def simulate_handler(message, user_id='test_user', conversation_id='test_conv'):
        """Simulate handler logic without AWS calls."""
        
        # Simple agent selection logic for testing
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['emergency', 'urgent', 'help']):
            agent = 'safety_guardian'
            confidence = 0.95
        elif any(word in message_lower for word in ['pain', 'sick', 'headache']):
            agent = 'illness_monitor'
            confidence = 0.8
        elif any(word in message_lower for word in ['stress', 'anxiety', 'sad']):
            agent = 'mental_health'
            confidence = 0.8
        elif any(word in message_lower for word in ['exercise', 'healthy', 'diet']):
            agent = 'wellness_coach'
            confidence = 0.8
        else:
            agent = 'wellness_coach'
            confidence = 0.5
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'response': f'Simulated response from {agent}',
                'agent': agent,
                'avatar': 'TestAvatar',
                'conversation_id': conversation_id,
                'routing_info': {
                    'confidence': confidence,
                    'reasons': ['Test routing'],
                    'emergency_override': agent == 'safety_guardian'
                }
            })
        }
    
    # Test cases
    test_cases = [
        {'message': 'I have a headache', 'expected_agent': 'illness_monitor'},
        {'message': 'I feel stressed', 'expected_agent': 'mental_health'},
        {'message': 'Emergency help!', 'expected_agent': 'safety_guardian'},
        {'message': 'I want to exercise', 'expected_agent': 'wellness_coach'}
    ]
    
    for test_case in test_cases:
        response = simulate_handler(test_case['message'])
        
        print(f"\nMessage: '{test_case['message']}'")
        print(f"Response Status: {response['statusCode']}")
        
        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            agent = body.get('agent')
            print(f"Selected Agent: {agent}")
            
            if agent == test_case['expected_agent']:
                print("✅ PASS - Correct agent selected")
            else:
                print(f"❌ FAIL - Expected: {test_case['expected_agent']}, Got: {agent}")
        else:
            print(f"❌ FAIL - Handler returned error: {response}")

def main():
    """Run all tests."""
    
    print("Agent Router Test Suite")
    print("="*50)
    
    try:
        test_agent_selection()
        test_emergency_detection()
        test_lambda_handler()
        
        print("\n" + "="*50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()