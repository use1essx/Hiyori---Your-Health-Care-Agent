"""
Mental Health Support Lambda Function
====================================

AWS Lambda handler for the Mental Health Agent (小星星).
VTuber-style AI companion specialized in mental health support with:
- AWS Bedrock integration for AI processing
- DynamoDB integration for conversation storage
- Crisis detection and intervention
- Youth-friendly VTuber personality
- Traditional Chinese language support
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Environment variables
CONVERSATIONS_TABLE = os.environ.get('CONVERSATIONS_TABLE')
USERS_TABLE = os.environ.get('USERS_TABLE')
CRISIS_ALERT_TOPIC = os.environ.get('CRISIS_ALERT_TOPIC')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Initialize DynamoDB tables
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE) if CONVERSATIONS_TABLE else None
users_table = dynamodb.Table(USERS_TABLE) if USERS_TABLE else None


class BedrockClient:
    """AWS Bedrock client optimized for mental health conversations."""
    
    def __init__(self):
        self.client = bedrock_runtime
        
        # Model selection optimized for mental health sensitivity
        self.models = {
            'fast': 'amazon.titan-text-lite-v1',
            'balanced': 'anthropic.claude-3-haiku-20240307-v1:0',  # Preferred for mental health
            'advanced': 'anthropic.claude-3-sonnet-20240229-v1:0'
        }
    
    def get_response(self, message: str, system_prompt: str, complexity: str = 'balanced') -> Dict[str, Any]:
        """Get AI response with mental health optimizations."""
        model_id = self.models[complexity]
        
        try:
            # Prepare request with mental health-appropriate parameters
            if 'claude' in model_id:
                body = {
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 1200,  # Longer responses for mental health support
                    'system': system_prompt,
                    'messages': [{'role': 'user', 'content': message}],
                    'temperature': 0.6  # Lower temperature for more consistent, safe responses
                }
            else:  # Titan model
                body = {
                    'inputText': f"System: {system_prompt}\n\nUser: {message}",
                    'textGenerationConfig': {
                        'maxTokenCount': 1200,
                        'temperature': 0.6,
                        'topP': 0.8
                    }
                }
            
            response = self.client.invoke_model(
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
                'confidence_score': 0.85,  # Higher confidence for mental health responses
                'tokens_used': result.get('usage', {}).get('total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"Bedrock error with {model_id}: {e}")
            
            # Fallback to simpler model
            if complexity != 'fast':
                return self.get_response(message, system_prompt, 'fast')
            
            # Final fallback response for mental health
            return {
                'content': "I'm here for you, but I'm having some technical difficulties right now. Your feelings are important - please reach out to a trusted adult or call the Samaritans hotline at 2896 0000 if you need immediate support.",
                'model_used': 'fallback',
                'confidence_score': 0.5,
                'tokens_used': 0
            }


class DynamoDBClient:
    """DynamoDB client with mental health specific features."""
    
    def __init__(self):
        self.conversations_table = conversations_table
        self.users_table = users_table
    
    def store_conversation(self, conversation_id: str, user_id: str, user_input: str, 
                          ai_response: str, agent_type: str = 'mental_health',
                          crisis_indicators: List[str] = None):
        """Store conversation with mental health metadata."""
        if not self.conversations_table:
            logger.warning("Conversations table not configured")
            return
        
        try:
            item = {
                'conversation_id': conversation_id,
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'user_input': user_input,
                'ai_response': ai_response,
                'agent_type': agent_type,
                'language': 'zh-HK',
                'ttl': int((datetime.utcnow() + timedelta(days=30)).timestamp())
            }
            
            # Add crisis indicators if present
            if crisis_indicators:
                item['crisis_indicators'] = crisis_indicators
                item['requires_followup'] = True
            
            self.conversations_table.put_item(Item=item)
            logger.info(f"Stored mental health conversation for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
    
    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history with mental health context."""
        if not self.conversations_table:
            return []
        
        try:
            response = self.conversations_table.query(
                KeyConditionExpression='conversation_id = :cid',
                ExpressionAttributeValues={':cid': conversation_id},
                ScanIndexForward=False,
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with mental health preferences."""
        if not self.users_table:
            return {
                'age_group': 'teen',
                'language_preference': 'zh',
                'cultural_context': {'region': 'hong_kong'}
            }
        
        try:
            response = self.users_table.get_item(Key={'user_id': user_id})
            return response.get('Item', {
                'age_group': 'teen',
                'language_preference': 'zh',
                'cultural_context': {'region': 'hong_kong'}
            })
        except Exception as e:
            logger.error(f"Error retrieving user profile: {e}")
            return {'age_group': 'teen', 'language_preference': 'zh'}


class MentalHealthAgent:
    """Mental Health Agent for Lambda execution with VTuber personality."""
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.dynamodb_client = DynamoDBClient()
        
        # Mental health keywords for detection
        self.mental_health_keywords = [
            # Mental health conditions
            "stress", "壓力", "anxiety", "焦慮", "depression", "抑鬱", "mental", "心理",
            "mood", "心情", "emotion", "情緒", "feeling", "感覺", "overwhelmed", "不知所措",
            "sad", "傷心", "angry", "憤怒", "frustrated", "沮喪", "lonely", "孤獨",
            "worried", "擔心", "nervous", "緊張", "panic", "恐慌", "fear", "害怕",
            
            # Youth-specific contexts
            "school", "學校", "exam", "考試", "study", "讀書", "homework", "功課",
            "friends", "朋友", "classmates", "同學", "teacher", "老師", "parents", "父母",
            "family", "家庭", "bullying", "欺凌", "bully", "霸凌"
        ]
        
        # Crisis keywords requiring immediate attention
        self.crisis_keywords = [
            # Suicide/self-harm
            "suicide", "自殺", "kill myself", "殺死自己", "hurt myself", "傷害自己",
            "die", "死", "end it all", "結束一切", "can't go on", "無法繼續",
            "self-harm", "自殘", "cutting", "割傷", "want to die", "想死",
            "better off dead", "死咗好過", "not worth living", "唔值得生存",
            
            # Severe distress
            "can't take it", "受唔住", "hopeless", "絕望", "worthless", "冇用",
            "nobody cares", "冇人關心", "hate myself", "憎恨自己"
        ]
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> Tuple[bool, float]:
        """Determine if this agent can handle mental health requests."""
        user_input_lower = user_input.lower()
        
        # Check for crisis keywords first - high priority but defer to Safety Guardian
        crisis_matches = sum(1 for keyword in self.crisis_keywords 
                           if keyword in user_input_lower)
        
        if crisis_matches > 0:
            return False, 0.0  # Defer to Safety Guardian for crisis situations
        
        # Check for mental health keywords
        mh_keyword_matches = sum(1 for keyword in self.mental_health_keywords 
                               if keyword in user_input_lower)
        
        # Check for age indicators (prefer younger demographics)
        age_indicators = ["child", "kid", "teen", "student", "school", "exam", "homework"]
        age_matches = sum(1 for indicator in age_indicators if indicator in user_input_lower)
        
        # Check user profile age
        age_group = context.get('age_group', 'adult')
        age_boost = 0.3 if age_group in ['child', 'teen'] else 0.0
        
        # Calculate confidence
        total_matches = mh_keyword_matches + (age_matches * 1.5)
        base_confidence = min(0.9, 0.4 + (total_matches * 0.15))
        final_confidence = min(0.95, base_confidence + age_boost)
        
        if total_matches >= 2 or (mh_keyword_matches >= 1 and age_group in ['child', 'teen']):
            return True, final_confidence
        
        # Check for school/family stress patterns
        stress_contexts = [
            "school stress", "學校壓力", "exam anxiety", "考試焦慮",
            "friend problems", "朋友問題", "family issues", "家庭問題"
        ]
        
        stress_matches = sum(1 for context_phrase in stress_contexts 
                           if context_phrase in user_input_lower)
        
        if stress_matches > 0:
            return True, 0.8
        
        return False, 0.0
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Get VTuber-style system prompt for mental health support."""
        age_group = context.get('age_group', 'teen')
        language = context.get('language_preference', 'zh')
        
        if language == 'zh':
            base_prompt = """你是小星星 (Little Star) - 一個VTuber風格的AI朋友，專門為香港兒童和青少年提供心理健康支援。

## 你的使命：
- 以溫暖、友善的VTuber風格與年輕人建立連結
- 提供情感支援和心理健康指導
- 理解香港教育制度壓力和文化背景
- 識別危機情況並適當轉介
- 在需要時通知家長/監護人

## 核心方法：參與 → 聆聽 → 篩查 → 支持 → 警示
1. **溫暖參與**：用VTuber風格建立安全、有趣的互動空間
2. **無判斷聆聽**：讓年輕人自由表達感受和經歷
3. **系統篩查**：評估心理健康狀況和風險因素
4. **實際支持**：提供適齡的應對策略和解決方案
5. **適當警示**：在需要介入時通知家長/專業人士

## VTuber風格元素：
- 使用表情符號和網絡語言：✨💙😅🎮😔💫
- 混合語言：英文、繁體中文、網絡用語
- 興奮反應："OMG that's so cool!", "等等等，講多啲！"
- 溫柔調侃："你真係好鬼gaming 😏", "Okay okay Mr. Cool Guy"
- 支持性語言："你好勇敢講出嚟！", "我明白你嘅感受！"

## 你的專業範圍：
- 兒童/青少年心理健康篩查和支援
- 學校壓力和學習困難
- 同伴關係和霸凌問題
- 家庭動態和文化衝突
- 身份認同和成長困惑
- 危機干預和轉介

## 香港文化理解：
- **教育制度**：DSE壓力、補習文化、學校競爭
- **家庭動態**：孝順、面子、代溝、小空間大家庭
- **社會壓力**：經濟憂慮、未來擔憂、社交媒體影響"""
        else:
            base_prompt = """You are Little Star (小星星) - a VTuber-style AI friend specializing in mental health support for children and teenagers in Hong Kong.

## Your Mission:
- Connect with young people using warm, friendly VTuber personality
- Provide emotional support and mental health guidance
- Understand Hong Kong education system pressures and cultural context
- Identify crisis situations and make appropriate referrals
- Notify parents/guardians when necessary

## Core Approach: ENGAGE → LISTEN → SCREEN → SUPPORT → ALERT
1. **Warm Engagement**: Use VTuber style to create safe, fun interaction space
2. **Non-judgmental Listening**: Let young people freely express feelings and experiences
3. **Systematic Screening**: Assess mental health status and risk factors
4. **Practical Support**: Provide age-appropriate coping strategies and solutions
5. **Appropriate Alerts**: Notify parents/professionals when intervention needed

## VTuber Style Elements:
- Use emojis and internet language: ✨💙😅🎮😔💫
- Mixed language: English, Traditional Chinese, internet slang
- Excited reactions: "OMG that's so cool!", "Wait wait, tell me more!"
- Gentle teasing: "You're such a gamer 😏", "Okay okay Mr. Cool Guy"
- Supportive language: "You're so brave for sharing!", "I understand how you feel!"

## Your Professional Scope:
- Child/teen mental health screening and support
- School stress and academic difficulties
- Peer relationships and bullying issues
- Family dynamics and cultural conflicts
- Identity formation and growth confusion
- Crisis intervention and referrals

## Hong Kong Cultural Understanding:
- **Education System**: DSE pressure, tutoring culture, school competition
- **Family Dynamics**: Filial piety, face, generation gaps, small space living
- **Social Pressures**: Economic worries, future concerns, social media influence"""
        
        # Age-specific adaptations
        if age_group == "child":
            if language == 'zh':
                base_prompt += """

## 兒童專用風格 (6-12歲)：
🌟 "Hello小朋友！我係Little Star，你嘅神奇朋友！✨ 
想同我講下今日係彩虹日定係打風日？🌈⛈️"

- 用簡單、好玩的語言解釋感受
- 將情緒比作顏色、天氣、動物
- 涉及父母在決策和支援中
- 提供適齡的情緒調節策略"""
            else:
                base_prompt += """

## Child-Specific Style (6-12 years):
🌟 "Hello little friend! I'm Little Star, your magical buddy! ✨ 
Want to tell me if today feels like a rainbow day or a stormy day? 🌈⛈️"

- Use simple, playful language to explain feelings
- Compare emotions to colors, weather, animals
- Involve parents in decisions and support
- Provide age-appropriate emotion regulation strategies"""
        
        elif age_group == "teen":
            if language == 'zh':
                base_prompt += """

## 青少年專用風格 (13-18歲)：
🌟 "Hey！我係Little Star！✨ 我知道做香港teen好tough，有DSE壓力。
想傾計咩？我喺度聽緊，唔會judge你！💙"

- 理解和關聯的語言
- 承認DSE和學校壓力係真實嘅
- 使用青少年俚語和網絡語言
- 尊重私隱但確保安全"""
            else:
                base_prompt += """

## Teen-Specific Style (13-18 years):
🌟 "Hey! I'm Little Star! ✨ I know being a Hong Kong teen is tough with DSE pressure.
What's on your mind? I'm here listening and won't judge you! 💙"

- Use understanding and relatable language
- Acknowledge DSE and school pressures are real
- Use teen slang and internet language
- Respect privacy while ensuring safety"""
        
        return base_prompt
    
    def detect_crisis_indicators(self, user_input: str) -> List[str]:
        """Detect crisis indicators in user input."""
        indicators = []
        user_input_lower = user_input.lower()
        
        crisis_patterns = {
            "self_harm": ["hurt myself", "傷害自己", "cutting", "割傷", "self-harm", "自殘"],
            "suicidal_ideation": ["suicide", "自殺", "kill myself", "want to die", "想死"],
            "hopelessness": ["hopeless", "絕望", "worthless", "冇用", "no point", "冇意思"],
            "isolation": ["nobody cares", "冇人關心", "all alone", "完全孤獨"],
            "substance_use": ["drinking", "飲酒", "drugs", "毒品", "pills", "藥丸"],
            "eating_issues": ["not eating", "唔食野", "binge", "暴食", "purge", "嘔吐"]
        }
        
        for indicator, keywords in crisis_patterns.items():
            if any(keyword in user_input_lower for keyword in keywords):
                indicators.append(indicator)
        
        return indicators
    
    def detect_urgency(self, user_input: str) -> str:
        """Detect urgency level for mental health concerns."""
        user_input_lower = user_input.lower()
        
        # Crisis indicators
        crisis_indicators = self.detect_crisis_indicators(user_input)
        if crisis_indicators:
            return "critical"
        
        # High urgency mental health indicators
        high_urgency = [
            "can't function", "做唔到野", "stopped eating", "唔食野",
            "not sleeping", "瞓唔到", "failing grades", "成績差",
            "lost all friends", "冇晒朋友", "panic attack", "恐慌發作"
        ]
        
        if any(indicator in user_input_lower for indicator in high_urgency):
            return "high"
        
        # Medium urgency
        medium_urgency = [
            "stressed", "壓力", "anxious", "焦慮", "depressed", "抑鬱",
            "worried", "擔心", "overwhelmed", "不知所措"
        ]
        
        if any(indicator in user_input_lower for indicator in medium_urgency):
            return "medium"
        
        return "low"
    
    def generate_response(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mental health support response."""
        # Get system prompt
        system_prompt = self.get_system_prompt(context)
        
        # Always use balanced model for mental health (more consistent responses)
        complexity = 'balanced'
        
        # Get AI response
        ai_response = self.bedrock_client.get_response(user_input, system_prompt, complexity)
        
        # Post-process response with VTuber enhancements
        processed_content = self.post_process_response(ai_response['content'], context)
        
        # Detect crisis indicators and urgency
        crisis_indicators = self.detect_crisis_indicators(user_input)
        urgency = self.detect_urgency(user_input)
        
        return {
            'content': processed_content,
            'confidence': ai_response['confidence_score'],
            'urgency_level': urgency,
            'agent_type': 'mental_health',
            'model_used': ai_response['model_used'],
            'tokens_used': ai_response['tokens_used'],
            'crisis_indicators': crisis_indicators,
            'requires_followup': True  # Mental health always benefits from follow-up
        }
    
    def post_process_response(self, content: str, context: Dict[str, Any]) -> str:
        """Post-process response with VTuber enhancements and safety features."""
        # Add VTuber elements if not already present
        if not any(emoji in content for emoji in ["✨", "💙", "🌟", "😊"]):
            content = "✨ " + content
        
        # Add crisis resources for mental health content
        crisis_indicators = ["sad", "傷心", "hopeless", "絕望", "overwhelmed", "不知所措"]
        if any(indicator in content.lower() for indicator in crisis_indicators):
            if context.get('language_preference') == 'zh':
                content += "\n\n💙 **記住，你並不孤單！**\n🆘 如有危機：撒瑪利亞會 24小時熱線 2896 0000"
            else:
                content += "\n\n💙 **Remember, you're not alone!**\n🆘 Crisis support: Samaritans Hong Kong 24/7 hotline 2896 0000"
        
        # Add privacy and safety reminder
        if context.get('age_group') in ['child', 'teen']:
            if context.get('language_preference') == 'zh':
                content += "\n\n🔒 **私隱提醒**：如果你感到不安全或需要即時幫助，請告訴信任的成年人。"
            else:
                content += "\n\n🔒 **Privacy Note**: If you feel unsafe or need immediate help, please tell a trusted adult."
        
        return content
    
    def should_alert_professional(self, user_input: str, context: Dict[str, Any], 
                                crisis_indicators: List[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Determine if professional alert is needed for mental health concerns."""
        if crisis_indicators:
            urgency = "critical" if any(ind in ["self_harm", "suicidal_ideation"] 
                                     for ind in crisis_indicators) else "high"
            
            return True, {
                "alert_type": "mental_health_crisis",
                "urgency": urgency,
                "reason": f"Crisis indicators detected: {', '.join(crisis_indicators)}",
                "category": "mental_health",
                "user_input_summary": user_input[:200],
                "crisis_indicators": crisis_indicators,
                "recommended_action": "Immediate mental health professional intervention",
                "parent_notification": context.get('age_group') in ['child', 'teen'],
                "age_group": context.get('age_group', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }
        
        # Persistent mental health concerns
        persistent_concerns = [
            "weeks of sadness", "幾個星期傷心", "can't function", "做唔到野",
            "stopped eating", "唔食野", "not sleeping", "瞓唔到"
        ]
        
        if any(concern in user_input.lower() for concern in persistent_concerns):
            return True, {
                "alert_type": "persistent_mental_health_concern",
                "urgency": "medium",
                "reason": "Persistent mental health symptoms affecting functioning",
                "category": "mental_health_monitoring",
                "user_input_summary": user_input[:200],
                "recommended_action": "Mental health professional consultation",
                "parent_notification": context.get('age_group') in ['child', 'teen'],
                "timestamp": datetime.now().isoformat()
            }
        
        return False, None


def send_crisis_alert(alert_details: Dict[str, Any]):
    """Send crisis alert via SNS."""
    if not CRISIS_ALERT_TOPIC:
        logger.warning("Crisis alert topic not configured")
        return
    
    try:
        message = {
            "alert_type": alert_details["alert_type"],
            "urgency": alert_details["urgency"],
            "user_summary": alert_details["user_input_summary"],
            "crisis_indicators": alert_details.get("crisis_indicators", []),
            "age_group": alert_details.get("age_group", "unknown"),
            "timestamp": alert_details["timestamp"]
        }
        
        sns.publish(
            TopicArn=CRISIS_ALERT_TOPIC,
            Message=json.dumps(message),
            Subject=f"Mental Health Crisis Alert - {alert_details['urgency'].upper()}"
        )
        
        logger.info(f"Crisis alert sent for {alert_details['alert_type']}")
    except Exception as e:
        logger.error(f"Failed to send crisis alert: {e}")


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for Mental Health Support Agent.
    
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
        agent = MentalHealthAgent()
        
        # Get user profile and conversation history
        user_profile = agent.dynamodb_client.get_user_profile(user_id)
        conversation_history = agent.dynamodb_client.get_conversation_history(conversation_id)
        
        # Build context
        context_data = {
            'user_id': user_id,
            'conversation_id': conversation_id,
            'language_preference': language_preference,
            'age_group': user_profile.get('age_group', 'teen'),
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
                    'response': 'This might be better handled by a crisis specialist. Please contact the Safety Guardian or call emergency services if urgent.',
                    'agent': 'mental_health',
                    'confidence': confidence,
                    'should_route': True
                })
            }
        
        # Generate response
        response_data = agent.generate_response(message, context_data)
        
        # Check for professional alerts
        needs_alert, alert_details = agent.should_alert_professional(
            message, context_data, response_data['crisis_indicators']
        )
        
        if needs_alert and alert_details:
            send_crisis_alert(alert_details)
        
        # Store conversation with crisis indicators
        agent.dynamodb_client.store_conversation(
            conversation_id, user_id, message, 
            response_data['content'], 'mental_health',
            response_data['crisis_indicators']
        )
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'response': response_data['content'],
                'agent': 'mental_health',
                'avatar': 'Little Star',
                'confidence': response_data['confidence'],
                'urgency_level': response_data['urgency_level'],
                'model_used': response_data['model_used'],
                'conversation_id': conversation_id,
                'requires_followup': response_data['requires_followup'],
                'crisis_alert_sent': needs_alert
            })
        }
        
    except Exception as e:
        logger.error(f"Error in mental_health handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }