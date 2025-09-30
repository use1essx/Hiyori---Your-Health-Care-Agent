"""
Agent Router Lambda Function
============================

Main routing Lambda that determines which healthcare agent to invoke based on user message content.
Implements intelligent agent selection logic with error handling and fallback mechanisms.

Requirements: 4.1, 4.2, 4.3, 4.4
"""

import json
import os
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid

# Import optimization system
import sys
sys.path.append('/opt/python/lib/python3.9/site-packages')
sys.path.append('/var/task/src')

from aws.lambda_optimizer import (
    optimize_lambda_handler, 
    get_optimized_lambda_client,
    get_optimized_dynamodb_client,
    lambda_optimizer
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize optimized AWS clients
lambda_client = None
dynamodb = None

def get_clients():
    """Get optimized AWS clients with lazy initialization."""
    global lambda_client, dynamodb
    if lambda_client is None:
        lambda_client = get_optimized_lambda_client()
    if dynamodb is None:
        dynamodb_client = get_optimized_dynamodb_client()
        dynamodb = dynamodb_client  # For compatibility
    return lambda_client, dynamodb

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
CONVERSATIONS_TABLE = os.environ.get('CONVERSATIONS_TABLE')
USERS_TABLE = os.environ.get('USERS_TABLE')

# Agent function mapping
AGENT_FUNCTIONS = {
    'illness_monitor': f"{ENVIRONMENT}-healthcare-illness-monitor",
    'mental_health': f"{ENVIRONMENT}-healthcare-mental-health", 
    'safety_guardian': f"{ENVIRONMENT}-healthcare-safety-guardian",
    'wellness_coach': f"{ENVIRONMENT}-healthcare-wellness-coach"
}

# Agent selection confidence thresholds
CONFIDENCE_THRESHOLD = 0.6
EMERGENCY_CONFIDENCE_THRESHOLD = 0.4
MULTI_AGENT_THRESHOLD = 0.8


class AgentRouter:
    """Intelligent agent routing system for healthcare AI."""
    
    def __init__(self):
        """Initialize the agent router."""
        # Use lazy initialization for DynamoDB tables
        self._conversations_table = None
        self._users_table = None
    
    @property
    def conversations_table(self):
        """Lazy-loaded conversations table."""
        if self._conversations_table is None and CONVERSATIONS_TABLE:
            _, dynamodb = get_clients()
            self._conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
        return self._conversations_table
    
    @property
    def users_table(self):
        """Lazy-loaded users table."""
        if self._users_table is None and USERS_TABLE:
            _, dynamodb = get_clients()
            self._users_table = dynamodb.Table(USERS_TABLE)
        return self._users_table
        
        # Agent selection patterns
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
    
    def determine_agent(self, message: str, user_context: Optional[Dict] = None) -> Tuple[str, float, List[str]]:
        """
        Determine the best agent for handling the user message.
        
        Args:
            message: User's message
            user_context: Optional user context information
            
        Returns:
            Tuple of (agent_id, confidence, reasons)
        """
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
            
            # Context-based adjustments
            if user_context:
                context_boost = self._apply_context_boost(agent_id, user_context)
                score += context_boost
                if context_boost > 0:
                    reasons.append("Context-based boost applied")
            
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
                logger.warning(f"Emergency override: switching from {best_agent} to safety_guardian")
                return 'safety_guardian', 0.95, ['Emergency keywords detected - safety override activated']
        
        return best_agent, best_score, reasons
    
    def _apply_context_boost(self, agent_id: str, user_context: Dict) -> float:
        """
        Apply context-based confidence boost.
        
        Args:
            agent_id: Agent identifier
            user_context: User context information
            
        Returns:
            Confidence boost value
        """
        boost = 0.0
        
        # Age-based preferences
        age_group = user_context.get('age_group', '')
        if age_group == 'elderly' and agent_id == 'illness_monitor':
            boost += 0.1
        elif age_group in ['child', 'teen'] and agent_id == 'mental_health':
            boost += 0.1
        
        # Previous agent preference
        preferred_agent = user_context.get('preferred_agent', '')
        if preferred_agent == agent_id:
            boost += 0.05
        
        # Recent conversation history
        recent_agent = user_context.get('recent_agent', '')
        if recent_agent == agent_id:
            boost += 0.05
        
        return boost
    
    def _is_emergency(self, message: str) -> bool:
        """
        Check if message contains emergency indicators.
        
        Args:
            message: User's message
            
        Returns:
            True if emergency detected
        """
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
    
    async def invoke_agent(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke specific agent Lambda function.
        
        Args:
            agent_id: Agent identifier
            payload: Payload to send to agent
            
        Returns:
            Agent response
        """
        function_name = AGENT_FUNCTIONS.get(agent_id)
        if not function_name:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        try:
            logger.info(f"Invoking agent: {agent_id} ({function_name})")
            
            # Get optimized Lambda client
            lambda_client, _ = get_clients()
            
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',  # Synchronous invocation
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read().decode())
            
            if response.get('StatusCode') == 200:
                return response_payload
            else:
                logger.error(f"Agent invocation failed: {response_payload}")
                raise Exception(f"Agent {agent_id} returned error: {response_payload}")
                
        except Exception as e:
            logger.error(f"Error invoking agent {agent_id}: {str(e)}")
            raise
    
    def store_conversation(self, conversation_id: str, user_input: str, 
                          agent_response: str, agent_id: str, user_id: str = None):
        """
        Store conversation in DynamoDB.
        
        Args:
            conversation_id: Conversation identifier
            user_input: User's message
            agent_response: Agent's response
            agent_id: Selected agent identifier
            user_id: User identifier
        """
        if not self.conversations_table:
            logger.warning("Conversations table not configured")
            return
        
        try:
            item = {
                'conversation_id': conversation_id,
                'timestamp': datetime.utcnow().isoformat(),
                'user_input': user_input,
                'ai_response': agent_response,
                'agent_type': agent_id,
                'user_id': user_id or 'anonymous',
                'ttl': int((datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60))  # 30 days TTL
            }
            
            self.conversations_table.put_item(Item=item)
            logger.info(f"Stored conversation: {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error storing conversation: {str(e)}")
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get user context from DynamoDB.
        
        Args:
            user_id: User identifier
            
        Returns:
            User context information
        """
        if not self.users_table or not user_id:
            return {}
        
        try:
            response = self.users_table.get_item(Key={'user_id': user_id})
            return response.get('Item', {})
        except Exception as e:
            logger.error(f"Error getting user context: {str(e)}")
            return {}


# Initialize router
router = AgentRouter()


@optimize_lambda_handler
def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for agent routing.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        HTTP response
    """
    try:
        # Parse request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        message = body.get('message', '')
        user_id = body.get('user_id', 'anonymous')
        conversation_id = body.get('conversation_id', str(uuid.uuid4()))
        preferred_agent = body.get('preferred_agent')
        
        if not message:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Message is required'})
            }
        
        logger.info(f"Processing message from user {user_id}: {message[:100]}...")
        
        # Get user context
        user_context = router.get_user_context(user_id)
        
        # Manual agent selection takes priority
        if preferred_agent and preferred_agent in AGENT_FUNCTIONS:
            selected_agent = preferred_agent
            confidence = 1.0
            reasons = [f"Manually selected {preferred_agent}"]
            logger.info(f"Manual agent selection: {preferred_agent}")
        else:
            # Determine best agent
            selected_agent, confidence, reasons = router.determine_agent(message, user_context)
        
        # Check confidence threshold
        if confidence < CONFIDENCE_THRESHOLD and selected_agent != 'safety_guardian':
            logger.warning(f"Low confidence selection: {confidence:.2f}")
            # Could implement human handoff logic here
        
        # Prepare payload for agent
        agent_payload = {
            'message': message,
            'conversation_id': conversation_id,
            'user_id': user_id,
            'user_context': user_context,
            'routing_info': {
                'selected_agent': selected_agent,
                'confidence': confidence,
                'reasons': reasons
            }
        }
        
        # Invoke selected agent
        try:
            agent_response = router.invoke_agent(selected_agent, agent_payload)
            
            # Extract response from agent
            if 'body' in agent_response:
                agent_body = json.loads(agent_response['body']) if isinstance(agent_response['body'], str) else agent_response['body']
                ai_response = agent_body.get('response', 'No response from agent')
                avatar = agent_body.get('avatar', 'Unknown')
            else:
                ai_response = agent_response.get('response', 'No response from agent')
                avatar = agent_response.get('avatar', 'Unknown')
            
            # Store conversation
            router.store_conversation(
                conversation_id=conversation_id,
                user_input=message,
                agent_response=ai_response,
                agent_id=selected_agent,
                user_id=user_id
            )
            
            # Return response
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'response': ai_response,
                    'agent': selected_agent,
                    'avatar': avatar,
                    'conversation_id': conversation_id,
                    'routing_info': {
                        'confidence': confidence,
                        'reasons': reasons,
                        'emergency_override': selected_agent == 'safety_guardian' and router._is_emergency(message)
                    }
                })
            }
            
        except Exception as agent_error:
            logger.error(f"Agent invocation failed: {str(agent_error)}")
            
            # Fallback mechanism
            fallback_response = {
                'response': "I'm sorry, I'm having technical difficulties right now. Please try again in a moment, or if this is an emergency, please contact emergency services immediately.",
                'agent': 'system',
                'avatar': 'System',
                'conversation_id': conversation_id,
                'routing_info': {
                    'confidence': 0.0,
                    'reasons': ['Agent invocation failed - using fallback'],
                    'error': str(agent_error)
                }
            }
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(fallback_response)
            }
    
    except Exception as e:
        logger.error(f"Router error: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }