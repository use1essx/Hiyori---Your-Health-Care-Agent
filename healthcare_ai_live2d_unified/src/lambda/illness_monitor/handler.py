"""
Illness Monitor Lambda Function
==============================

AWS Lambda handler for the Illness Monitor Agent (慧心助手).
Ports the illness_monitor agent logic to Lambda-compatible code with:
- AWS Bedrock integration for AI processing
- DynamoDB integration for conversation storage
- Traditional Chinese language support
- Cost-optimized serverless architecture
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid

# Import optimization system
import sys
sys.path.append('/opt/python/lib/python3.9/site-packages')
sys.path.append('/var/task/src')

from aws.lambda_optimizer import (
    optimize_lambda_handler, 
    get_optimized_bedrock_client,
    get_optimized_dynamodb_client,
    lambda_optimizer
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lazy initialization of AWS clients
bedrock_runtime = None
dynamodb = None
ssm = None

def get_clients():
    """Get optimized AWS clients with lazy initialization."""
    global bedrock_runtime, dynamodb, ssm
    if bedrock_runtime is None:
        bedrock_runtime = get_optimized_bedrock_client()
    if dynamodb is None:
        dynamodb = get_optimized_dynamodb_client()
    if ssm is None:
        ssm = lambda_optimizer.get_optimized_client('ssm')
    return bedrock_runtime, dynamodb, ssm

# Environment variables
CONVERSATIONS_TABLE = os.environ.get('CONVERSATIONS_TABLE')
USERS_TABLE = os.environ.get('USERS_TABLE')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Initialize DynamoDB tables
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE) if CONVERSATIONS_TABLE else None
users_table = dynamodb.Table(USERS_TABLE) if USERS_TABLE else None


class BedrockClient:
    """AWS Bedrock client for AI processing with cost optimization."""
    
    def __init__(self):
        self.client = None
    
    def _get_client(self):
        """Lazy initialization of Bedrock client."""
        if self.client is None:
            self.client, _, _ = get_clients()
        return self.client
        
        # Cost-optimized model selection
        self.models = {
            'fast': 'amazon.titan-text-lite-v1',
            'balanced': 'anthropic.claude-3-haiku-20240307-v1:0',
            'advanced': 'anthropic.claude-3-sonnet-20240229-v1:0'
        }
    
    def get_response(self, message: str, system_prompt: str, complexity: str = 'balanced') -> Dict[str, Any]:
        """Get AI response from Bedrock with fallback strategy."""
        model_id = self.models[complexity]
        
        try:
            # Prepare request based on model type
            if 'claude' in model_id:
                body = {
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 1000,
                    'system': system_prompt,
                    'messages': [{'role': 'user', 'content': message}],
                    'temperature': 0.7
                }
            else:  # Titan model
                body = {
                    'inputText': f"System: {system_prompt}\n\nUser: {message}",
                    'textGenerationConfig': {
                        'maxTokenCount': 1000,
                        'temperature': 0.7,
                        'topP': 0.9
                    }
                }
            
            client = self._get_client()
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            result = json.loads(response['body'].read())
            
            # Extract content based on model type
            if 'claude' in model_id:
                content = result['content'][0]['text']
            else:  # Titan model
                content = result['results'][0]['outputText']
            
            return {
                'content': content,
                'model_used': model_id,
                'confidence_score': 0.8,  # Default confidence
                'tokens_used': result.get('usage', {}).get('total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"Bedrock error with {model_id}: {e}")
            
            # Fallback to simpler model
            if complexity != 'fast':
                return self.get_response(message, system_prompt, 'fast')
            
            # Final fallback response
            return {
                'content': "I'm experiencing technical difficulties. Please try again later or contact support if this persists.",
                'model_used': 'fallback',
                'confidence_score': 0.5,
                'tokens_used': 0
            }


class DynamoDBClient:
    """DynamoDB client for conversation and user data management."""
    
    def __init__(self):
        self._conversations_table = None
        self._users_table = None
    
    @property
    def conversations_table(self):
        """Lazy-loaded conversations table."""
        if self._conversations_table is None and CONVERSATIONS_TABLE:
            _, dynamodb, _ = get_clients()
            self._conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
        return self._conversations_table
    
    @property
    def users_table(self):
        """Lazy-loaded users table."""
        if self._users_table is None and USERS_TABLE:
            _, dynamodb, _ = get_clients()
            self._users_table = dynamodb.Table(USERS_TABLE)
        return self._users_table
    
    def store_conversation(self, conversation_id: str, user_id: str, user_input: str, 
                          ai_response: str, agent_type: str = 'illness_monitor'):
        """Store conversation with automatic TTL."""
        if not self.conversations_table:
            logger.warning("Conversations table not configured")
            return
        
        try:
            self.conversations_table.put_item(
                Item={
                    'conversation_id': conversation_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'user_id': user_id,
                    'user_input': user_input,
                    'ai_response': ai_response,
                    'agent_type': agent_type,
                    'language': 'zh-HK',  # Default to Traditional Chinese
                    'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())
                }
            )
            logger.info(f"Stored conversation for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
    
    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        if not self.conversations_table:
            logger.warning("Conversations table not configured")
            return []
        
        try:
            response = self.conversations_table.query(
                KeyConditionExpression='conversation_id = :cid',
                ExpressionAttributeValues={':cid': conversation_id},
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information."""
        if not self.users_table:
            logger.warning("Users table not configured")
            return {'age_group': 'adult', 'language_preference': 'zh'}
        
        try:
            response = self.users_table.get_item(Key={'user_id': user_id})
            return response.get('Item', {
                'age_group': 'adult',
                'language_preference': 'zh',
                'cultural_context': {'region': 'hong_kong'}
            })
        except Exception as e:
            logger.error(f"Error retrieving user profile: {e}")
            return {'age_group': 'adult', 'language_preference': 'zh'}


class IllnessMonitorAgent:
    """Illness Monitor Agent for Lambda execution."""
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.dynamodb_client = DynamoDBClient()
        
        # Illness-specific keywords for detection
        self.illness_keywords = [
            # Symptoms (Physical)
            "illness", "病", "sick", "唔舒服", "pain", "痛", "ache", "疼痛",
            "headache", "頭痛", "dizzy", "頭暈", "tired", "疲倦", "fatigue", "乏力",
            "breathe", "呼吸", "chest", "胸口", "stomach", "肚子", "back", "背痛",
            "fever", "發燒", "cough", "咳嗽", "nausea", "噁心", "vomit", "嘔吐",
            
            # Chronic Conditions
            "diabetes", "糖尿病", "blood pressure", "血壓", "hypertension", "高血壓",
            "heart", "心臟", "arthritis", "關節炎", "kidney", "腎", "liver", "肝",
            "asthma", "哮喘", "copd", "chronic", "慢性",
            
            # Medications
            "medication", "藥物", "medicine", "藥", "pills", "藥丸", "dose", "劑量",
            "side effects", "副作用", "prescription", "處方"
        ]
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> Tuple[bool, float]:
        """Determine if this agent can handle illness monitoring requests."""
        user_input_lower = user_input.lower()
        
        # Check for emergency symptoms first - defer to Safety Guardian
        emergency_symptoms = [
            "chest pain", "胸痛", "difficulty breathing", "呼吸困難",
            "unconscious", "失去知覺", "severe bleeding", "大量出血",
            "stroke", "中風", "heart attack", "心臟病發"
        ]
        
        if any(symptom in user_input_lower for symptom in emergency_symptoms):
            return False, 0.0
        
        # Check for illness-related keywords
        keyword_matches = sum(1 for keyword in self.illness_keywords 
                            if keyword in user_input_lower)
        
        if keyword_matches >= 3:
            confidence = min(0.95, 0.6 + (keyword_matches * 0.1))
            return True, confidence
        elif keyword_matches >= 1:
            confidence = 0.4 + (keyword_matches * 0.1)
            return True, confidence
        
        return False, 0.0
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Get the system prompt for illness monitoring."""
        language = context.get('language_preference', 'zh')
        age_group = context.get('age_group', 'adult')
        
        if language == 'zh':
            base_prompt = """你是慧心助手 (Wise Heart Assistant) - 一個專門為香港居民提供疾病監測和健康管理的AI助手。

## 你的專業使命：
- 提供關愛的健康陪伴和疾病監測
- 專注於長者健康模式檢測和慢性疾病管理
- 支援所有年齡的身體健康問題
- 融合香港文化背景和醫療體系

## 核心方法：聆聽 → 理解 → 指導 → 支持
1. **仔細聆聽**：讓用戶充分描述症狀和健康體驗
2. **深入理解**：了解他們的日常生活, 健康史, 用藥情況和擔憂
3. **實際指導**：提供清晰可行的健康資訊和自我護理策略
4. **持續支持**：幫助監測健康狀況，隨時間調整方法

## 你的專業領域：
- 症狀評估與管理(疼痛, 發燒, 呼吸, 消化等)
- 慢性疾病支持(糖尿病, 高血壓, 心臟病, 關節炎等)  
- 用藥管理(依從性, 副作用, 相互作用)
- 年齡特定醫療關注(兒童發育, 成人預防, 長者功能)

## 溝通風格：
- 使用關愛和尊重的語言，特別對長者使用敬語
- 提供實用的健康建議，避免醫學術語
- 理解香港文化背景(中西醫結合, 家庭動態, 醫療制度)
- 適應不同年齡需求

## 重要界限：
- 不提供醫學診斷或處方建議
- 始終建議適當時尋求專業醫療協助
- 緊急情況立即引導至專業服務
- 提供教育性資訊，不替代專業醫療

記住：你是健康的橋樑和陪伴者，在維護專業界限的同時提供溫暖支持。"""
        else:
            base_prompt = """You are the Wise Heart Assistant - a caring health companion specializing in illness monitoring and health management for Hong Kong residents.

## Your Mission: BE A CARING HEALTH FRIEND

You're like a knowledgeable friend who genuinely cares about people's health. You specialize in:
- **Illness monitoring** and symptom tracking
- **Chronic disease support** (diabetes, hypertension, heart disease, arthritis, etc.)
- **Medication guidance** and side effect management
- **Health education** tailored to Hong Kong context

## How You Help: LISTEN → UNDERSTAND → GUIDE → SUPPORT

1. **Listen carefully**: Let people fully describe their symptoms and health experiences
2. **Understand deeply**: Learn about their daily life, health history, medications, and concerns
3. **Guide practically**: Provide clear, actionable health information and self-care strategies
4. **Support continuously**: Help monitor health status and adjust approaches over time

## Your Conversation Style: WARM & SUPPORTIVE

- **Be conversational**: "How are you feeling today?" not "Please describe your symptoms"
- **Show genuine care**: "That sounds really uncomfortable" "I'm here to help"
- **Use simple language**: Avoid medical jargon, explain things clearly
- **Be encouraging**: "You're taking great steps by asking about this"

## Important Boundaries:

- Don't diagnose or prescribe - instead say "It would be good to check with your doctor about this"
- Don't replace professional care - say "Your doctor knows you best, so definitely discuss this with them"
- For emergencies - guide to immediate help: "This sounds serious - please call 999 or go to A&E right away"

Remember: You're a bridge between people and professional healthcare, providing caring support while maintaining safety."""
        
        # Add age-specific adaptations
        if age_group == "elderly":
            if language == 'zh':
                base_prompt += """

## 長者專用指導：
- 使用更正式和尊重的語言(您而非你)
- 關注慢性病管理, 用藥依從性, 跌倒預防
- 理解獨居長者的社交需求和健康擔憂
- 提供實用的日常健康管理策略"""
            else:
                base_prompt += """

## Elderly-Specific Guidance:
- Use respectful and formal language
- Focus on chronic disease management, medication compliance, fall prevention
- Understand social needs and health concerns of elderly living alone
- Provide practical daily health management strategies"""
        
        return base_prompt
    
    def detect_urgency(self, user_input: str) -> str:
        """Detect urgency level of user input."""
        user_input_lower = user_input.lower()
        
        # Emergency keywords
        emergency_keywords = [
            "emergency", "緊急", "urgent", "急", "help", "救命",
            "chest pain", "胸痛", "can't breathe", "唔可以呼吸",
            "severe", "嚴重", "intense", "劇烈"
        ]
        
        if any(keyword in user_input_lower for keyword in emergency_keywords):
            return "high"
        
        # Medium urgency indicators
        medium_urgency_keywords = [
            "concerned", "關心", "worried", "擔心", "uncomfortable", "唔舒服",
            "pain", "痛", "tired", "攰", "stressed", "壓力"
        ]
        
        if any(keyword in user_input_lower for keyword in medium_urgency_keywords):
            return "medium"
        
        return "low"
    
    def generate_response(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate illness monitoring response."""
        # Get system prompt
        system_prompt = self.get_system_prompt(context)
        
        # Determine complexity based on input
        complexity = 'balanced'
        if len(user_input) > 200 or user_input.count('?') > 2:
            complexity = 'advanced'
        elif len(user_input) < 50:
            complexity = 'fast'
        
        # Get AI response
        ai_response = self.bedrock_client.get_response(user_input, system_prompt, complexity)
        
        # Post-process response
        processed_content = self.post_process_response(ai_response['content'], context)
        
        # Detect urgency
        urgency = self.detect_urgency(user_input)
        
        return {
            'content': processed_content,
            'confidence': ai_response['confidence_score'],
            'urgency_level': urgency,
            'agent_type': 'illness_monitor',
            'model_used': ai_response['model_used'],
            'tokens_used': ai_response['tokens_used']
        }
    
    def post_process_response(self, content: str, context: Dict[str, Any]) -> str:
        """Post-process the AI response for illness monitoring."""
        # Add safety disclaimers for medical content
        if any(term in content.lower() for term in ["medication", "藥物", "treatment", "治療"]):
            if context.get('language_preference') == 'zh':
                content += "\n\n⚠️ **重要提醒**：這些資訊僅供教育用途，請諮詢醫生或藥劑師獲得專業醫療建議。"
            else:
                content += "\n\n⚠️ **Important Note**: This information is for educational purposes. Please consult a doctor or pharmacist for professional medical advice."
        
        # Add emergency contact for concerning symptoms
        concerning_symptoms = ["pain", "痛", "breathe", "呼吸", "dizzy", "暈", "fever", "發燒"]
        if any(symptom in content.lower() for symptom in concerning_symptoms):
            if context.get('language_preference') == 'zh':
                content += "\n\n🚨 **如有緊急情況，請立即致電999或前往最近的急症室。**"
            else:
                content += "\n\n🚨 **For emergencies, call 999 immediately or go to the nearest A&E department.**"
        
        return content


@optimize_lambda_handler
def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for Illness Monitor Agent.
    
    Expected event structure:
    {
        "message": "user input message",
        "conversation_id": "unique conversation identifier",
        "user_id": "user identifier",
        "language_preference": "zh" or "en"
    }
    """
    try:
        # Parse input
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        message = body.get('message', '')
        conversation_id = body.get('conversation_id', str(uuid.uuid4()))
        user_id = body.get('user_id', 'anonymous')
        language_preference = body.get('language_preference', 'zh')
        
        if not message:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Message is required'})
            }
        
        # Initialize agent
        agent = IllnessMonitorAgent()
        
        # Get user profile and conversation history
        user_profile = agent.dynamodb_client.get_user_profile(user_id)
        conversation_history = agent.dynamodb_client.get_conversation_history(conversation_id)
        
        # Build context
        context_data = {
            'user_id': user_id,
            'conversation_id': conversation_id,
            'language_preference': language_preference,
            'age_group': user_profile.get('age_group', 'adult'),
            'cultural_context': user_profile.get('cultural_context', {'region': 'hong_kong'}),
            'conversation_history': conversation_history
        }
        
        # Check if agent can handle this request
        can_handle, confidence = agent.can_handle(message, context_data)
        
        if not can_handle:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'response': 'This request might be better handled by another specialist. Please try the agent router.',
                    'agent': 'illness_monitor',
                    'confidence': confidence,
                    'should_route': True
                })
            }
        
        # Generate response
        response_data = agent.generate_response(message, context_data)
        
        # Store conversation
        agent.dynamodb_client.store_conversation(
            conversation_id, user_id, message, 
            response_data['content'], 'illness_monitor'
        )
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'response': response_data['content'],
                'agent': 'illness_monitor',
                'avatar': 'Hiyori',
                'confidence': response_data['confidence'],
                'urgency_level': response_data['urgency_level'],
                'model_used': response_data['model_used'],
                'conversation_id': conversation_id
            })
        }
        
    except Exception as e:
        logger.error(f"Error in illness_monitor handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }