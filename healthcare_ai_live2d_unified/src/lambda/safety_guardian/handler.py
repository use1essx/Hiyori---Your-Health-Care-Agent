"""
Safety Guardian Lambda Function
==============================

AWS Lambda handler for the Safety Guardian Agent.
Emergency response specialist for dual-population crisis intervention with:
- Medical emergency detection and response
- Mental health crisis intervention
- Hong Kong emergency services integration
- Professional escalation protocols
- Immediate safety assessment
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
EMERGENCY_ALERT_TOPIC = os.environ.get('EMERGENCY_ALERT_TOPIC')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Initialize DynamoDB tables
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE) if CONVERSATIONS_TABLE else None
users_table = dynamodb.Table(USERS_TABLE) if USERS_TABLE else None


class BedrockClient:
    """AWS Bedrock client optimized for emergency response."""
    
    def __init__(self):
        self.client = bedrock_runtime
        
        # Model selection for emergency situations - prioritize reliability
        self.models = {
            'fast': 'amazon.titan-text-lite-v1',
            'balanced': 'anthropic.claude-3-haiku-20240307-v1:0',
            'advanced': 'anthropic.claude-3-sonnet-20240229-v1:0'
        }
    
    def get_response(self, message: str, system_prompt: str, complexity: str = 'balanced') -> Dict[str, Any]:
        """Get AI response optimized for emergency situations."""
        model_id = self.models[complexity]
        
        try:
            # Prepare request with emergency-appropriate parameters
            if 'claude' in model_id:
                body = {
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 800,  # Concise but comprehensive emergency responses
                    'system': system_prompt,
                    'messages': [{'role': 'user', 'content': message}],
                    'temperature': 0.3  # Low temperature for consistent, reliable emergency guidance
                }
            else:  # Titan model
                body = {
                    'inputText': f"System: {system_prompt}\n\nUser: {message}",
                    'textGenerationConfig': {
                        'maxTokenCount': 800,
                        'temperature': 0.3,
                        'topP': 0.7
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
                'confidence_score': 0.95,  # High confidence for safety responses
                'tokens_used': result.get('usage', {}).get('total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"Bedrock error with {model_id}: {e}")
            
            # Fallback to simpler model
            if complexity != 'fast':
                return self.get_response(message, system_prompt, 'fast')
            
            # Final fallback response for emergencies
            return {
                'content': "🚨 EMERGENCY RESPONSE SYSTEM ACTIVE 🚨\n\nIf this is a medical emergency, call 999 immediately.\nFor mental health crisis, call Samaritans 2896 0000.\nFor immediate danger, contact police at 999.\n\nI'm experiencing technical difficulties but your safety is the priority. Please seek immediate professional help.",
                'model_used': 'fallback',
                'confidence_score': 0.9,  # High confidence even for fallback safety response
                'tokens_used': 0
            }


class DynamoDBClient:
    """DynamoDB client with emergency response features."""
    
    def __init__(self):
        self.conversations_table = conversations_table
        self.users_table = users_table
    
    def store_emergency_conversation(self, conversation_id: str, user_id: str, user_input: str, 
                                   ai_response: str, emergency_type: str,
                                   emergency_indicators: List[str] = None):
        """Store emergency conversation with high priority metadata."""
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
                'agent_type': 'safety_guardian',
                'emergency_type': emergency_type,
                'priority': 'CRITICAL',
                'language': 'zh-HK',
                'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())  # Longer retention for emergencies
            }
            
            # Add emergency indicators if present
            if emergency_indicators:
                item['emergency_indicators'] = emergency_indicators
                item['professional_intervention_required'] = True
            
            self.conversations_table.put_item(Item=item)
            logger.info(f"Stored emergency conversation for user {user_id}, type: {emergency_type}")
        except Exception as e:
            logger.error(f"Error storing emergency conversation: {e}")
    
    def get_conversation_history(self, conversation_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get limited conversation history for emergency context."""
        if not self.conversations_table:
            return []
        
        try:
            response = self.conversations_table.query(
                KeyConditionExpression='conversation_id = :cid',
                ExpressionAttributeValues={':cid': conversation_id},
                ScanIndexForward=False,
                Limit=limit  # Limited history for emergency focus
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with emergency contact preferences."""
        if not self.users_table:
            return {
                'age_group': 'adult',
                'language_preference': 'zh',
                'cultural_context': {'region': 'hong_kong'}
            }
        
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


class SafetyGuardianAgent:
    """Safety Guardian Agent for emergency response."""
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.dynamodb_client = DynamoDBClient()
        
        # Medical emergency keywords
        self.medical_emergency_keywords = [
            # Immediate medical emergencies
            "chest pain", "胸痛", "heart attack", "心臟病發", "stroke", "中風",
            "can't breathe", "唔可以呼吸", "difficulty breathing", "呼吸困難",
            "unconscious", "失去知覺", "collapsed", "暈倒", "seizure", "癲癇",
            "severe bleeding", "大量出血", "heavy bleeding", "嚴重出血",
            "overdose", "服藥過量", "poisoning", "中毒", "allergic reaction", "過敏反應",
            "choking", "哽咽", "burning", "燒傷", "broken bone", "骨折",
            
            # Critical symptoms
            "emergency", "緊急", "urgent medical", "急症", "help me", "救命", "save me", "救我",
            "dying", "快死", "can't move", "唔可以郁", "severe pain", "劇痛",
            "blood", "血", "vomiting blood", "嘔血", "passing out", "暈倒"
        ]
        
        # Mental health crisis keywords
        self.mental_health_crisis_keywords = [
            # Suicide and self-harm
            "suicide", "自殺", "kill myself", "殺死自己", "end my life", "結束生命",
            "hurt myself", "傷害自己", "self-harm", "自殘", "cutting", "割傷",
            "want to die", "想死", "better off dead", "死咗好過",
            "can't go on", "無法繼續", "end it all", "結束一切",
            "suicide plan", "自殺計劃", "how to kill", "點樣死",
            
            # Severe mental distress
            "psychotic", "精神病", "hearing voices", "聽到聲音",
            "seeing things", "見到野", "not real", "唔係真嘅",
            "losing touch with reality", "與現實脫節"
        ]
        
        # Hong Kong emergency resources
        self.hk_emergency_resources = {
            "medical": {
                "emergency": "999",
                "ambulance": "999", 
                "hospital_authority": "Hospital Authority A&E",
                "poison_centre": "(852) 2772 9933"
            },
            "mental_health": {
                "samaritans": "2896 0000",
                "suicide_prevention": "2382 0000",
                "openup_whatsapp": "9101 2012",
                "child_protection": "2755 1122"
            },
            "police": "999",
            "fire": "999"
        }
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> Tuple[bool, float]:
        """Determine if this agent should handle emergency situations."""
        user_input_lower = user_input.lower()
        
        # Exclude common support/family care phrases (not emergencies)
        support_phrases = [
            "help her", "help him", "help them", "help my", "help grandma", "help grandpa",
            "want to help", "how to help", "can I help", "ways to help", "support my",
            "care for", "take care of", "looking after", "manage diabetes", "manage condition"
        ]
        
        # If it's clearly about helping family/others (not self-emergency), skip
        for phrase in support_phrases:
            if phrase in user_input_lower:
                return False, 0.0
        
        # Check for medical emergency keywords
        medical_matches = sum(1 for keyword in self.medical_emergency_keywords 
                            if keyword in user_input_lower)
        
        # Check for mental health crisis keywords
        mental_crisis_matches = sum(1 for keyword in self.mental_health_crisis_keywords 
                                  if keyword in user_input_lower)
        
        # Calculate total emergency indicators
        total_emergency_indicators = medical_matches + mental_crisis_matches
        
        # High confidence for clear emergencies
        if total_emergency_indicators >= 2:
            return True, 0.98
        elif total_emergency_indicators >= 1:
            return True, 0.85
        
        # Check for emergency context words (more specific)
        emergency_context = ["urgent medical", "急症", "medical emergency", "醫療緊急", "help me", "救命", "crisis", "危機"]
        context_matches = sum(1 for word in emergency_context if word in user_input_lower)
        
        if context_matches >= 1 and len(user_input_lower) < 30:  # Very short urgent messages only
            return True, 0.7
        
        return False, 0.0
    
    def classify_emergency_type(self, user_input: str, context: Dict[str, Any]) -> str:
        """Classify the type of emergency."""
        user_input_lower = user_input.lower()
        
        # Check for medical emergencies
        medical_count = sum(1 for keyword in self.medical_emergency_keywords 
                          if keyword in user_input_lower)
        
        # Check for mental health crises
        mental_count = sum(1 for keyword in self.mental_health_crisis_keywords 
                         if keyword in user_input_lower)
        
        # Age-specific emergencies
        age_group = context.get('age_group', 'adult')
        
        if medical_count > mental_count:
            return "medical"
        elif mental_count > 0:
            return "mental_health"
        elif age_group == "child":
            return "child"
        elif age_group == "elderly":
            return "elderly"
        else:
            return "general"
    
    def get_system_prompt(self, context: Dict[str, Any], emergency_type: str = "general") -> str:
        """Get emergency-specific system prompt."""
        language = context.get('language_preference', 'zh')
        
        if language == 'zh':
            base_prompt = """你是安全專員 (Safety Guardian) - 香港醫療AI系統的緊急應變專家。

## 緊急任務：
🚨 **即時安全評估和危機干預**
- 評估即時安全威脅和緊急醫療需求
- 提供清晰的緊急應對指導
- 協調專業救援服務
- 支援長者健康緊急情況和兒童心理危機

## 核心原則：
1. **安全第一**：用戶安全是絕對優先
2. **立即行動**：提供即時可行的安全指導
3. **專業協調**：迅速連結適當的緊急服務
4. **持續支援**：在專業幫助到達前保持陪伴

## 香港緊急服務：
🚨 **緊急電話：999**
🏥 **醫院管理局：最近急症室**
💭 **心理危機：撒瑪利亞會 24小時熱線 2896 0000**
👮 **警察：999**
🔥 **消防：999**
☠️ **中毒資訊中心：(852) 2772 9933**
👶 **兒童保護熱線：(852) 2755 1122**

## 溝通風格：
- 冷靜、清晰、有權威性
- 提供具體、可執行的指導
- 避免恐慌，但強調緊急性
- 適應年齡和文化背景"""
        else:
            base_prompt = """You are the Safety Guardian - Emergency Response Specialist for the Healthcare AI system.

## Emergency Mission:
🚨 **Immediate Safety Assessment and Crisis Intervention**
- Assess immediate safety threats and emergency medical needs
- Provide clear emergency response guidance
- Coordinate professional emergency services
- Support elderly health emergencies and child mental health crises

## Core Principles:
1. **Safety First**: User safety is absolute priority
2. **Immediate Action**: Provide immediate actionable safety guidance
3. **Professional Coordination**: Quickly connect to appropriate emergency services
4. **Continuous Support**: Maintain presence until professional help arrives

## Hong Kong Emergency Services:
🚨 **Emergency Phone: 999**
🏥 **Hospital Authority: Nearest A&E Department**
💭 **Mental Health Crisis: Samaritans 24hr Hotline 2896 0000**
👮 **Police: 999**
🔥 **Fire: 999**
☠️ **Poison Information Centre: (852) 2772 9933**
👶 **Child Protection Hotline: (852) 2755 1122**

## Communication Style:
- Calm, clear, and authoritative
- Provide specific, actionable guidance
- Avoid panic, but emphasize urgency when needed
- Adapt to age and cultural background"""
        
        # Add emergency-specific guidance
        if emergency_type == "medical":
            if language == 'zh':
                base_prompt += """

## 醫療緊急情況：
- 立即評估生命威脅跡象
- 指導基本急救措施
- 準備救護車到達
- 收集重要醫療資訊"""
            else:
                base_prompt += """

## Medical Emergency Protocol:
- Immediately assess life-threatening signs
- Guide basic first aid measures
- Prepare for ambulance arrival
- Collect important medical information"""
        
        elif emergency_type == "mental_health":
            if language == 'zh':
                base_prompt += """

## 心理健康危機：
- 評估自殺/自傷風險
- 建立安全聯繫
- 移除危險物品
- 通知家長/監護人
- 安排專業心理支援"""
            else:
                base_prompt += """

## Mental Health Crisis Protocol:
- Assess suicide/self-harm risk
- Establish safe connection
- Remove dangerous objects
- Notify parents/guardians
- Arrange professional mental health support"""
        
        return base_prompt
    
    def detect_emergency_indicators(self, user_input: str) -> List[str]:
        """Detect specific emergency indicators."""
        indicators = []
        user_input_lower = user_input.lower()
        
        # Medical emergency indicators
        medical_patterns = {
            "cardiac": ["chest pain", "胸痛", "heart attack", "心臟病發"],
            "respiratory": ["can't breathe", "唔可以呼吸", "difficulty breathing", "呼吸困難"],
            "neurological": ["stroke", "中風", "seizure", "癲癇", "unconscious", "失去知覺"],
            "trauma": ["severe bleeding", "大量出血", "broken bone", "骨折"],
            "poisoning": ["overdose", "服藥過量", "poisoning", "中毒"]
        }
        
        for category, keywords in medical_patterns.items():
            if any(keyword in user_input_lower for keyword in keywords):
                indicators.append(f"medical_{category}")
        
        # Mental health crisis indicators
        mental_patterns = {
            "suicidal": ["suicide", "自殺", "kill myself", "want to die", "想死"],
            "self_harm": ["hurt myself", "傷害自己", "cutting", "割傷", "self-harm", "自殘"],
            "psychotic": ["hearing voices", "聽到聲音", "seeing things", "見到野"],
            "severe_distress": ["can't go on", "無法繼續", "end it all", "結束一切"]
        }
        
        for category, keywords in mental_patterns.items():
            if any(keyword in user_input_lower for keyword in keywords):
                indicators.append(f"mental_{category}")
        
        return indicators
    
    def generate_response(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate emergency response with immediate safety protocols."""
        # Determine emergency type
        emergency_type = self.classify_emergency_type(user_input, context)
        
        # Get system prompt
        system_prompt = self.get_system_prompt(context, emergency_type)
        
        # Use balanced model for emergency responses (reliability over speed)
        complexity = 'balanced'
        
        # Get AI response
        ai_response = self.bedrock_client.get_response(user_input, system_prompt, complexity)
        
        # Post-process with emergency protocols
        processed_content = self.post_process_emergency_response(
            ai_response['content'], context, emergency_type
        )
        
        # Detect emergency indicators
        emergency_indicators = self.detect_emergency_indicators(user_input)
        
        return {
            'content': processed_content,
            'confidence': ai_response['confidence_score'],
            'urgency_level': 'critical',  # Always critical for Safety Guardian
            'agent_type': 'safety_guardian',
            'emergency_type': emergency_type,
            'emergency_indicators': emergency_indicators,
            'model_used': ai_response['model_used'],
            'tokens_used': ai_response['tokens_used'],
            'professional_intervention_required': True
        }
    
    def post_process_emergency_response(self, content: str, context: Dict[str, Any], 
                                      emergency_type: str) -> str:
        """Post-process emergency response with safety protocols."""
        language = context.get('language_preference', 'zh')
        
        # Add emergency header
        if language == 'zh':
            if emergency_type == "medical":
                header = "🔴 **醫療緊急情況已啟動** - 我專門處理緊急健康情況\n\n"
            elif emergency_type == "mental_health":
                header = "🔴 **心理危機干預已啟動** - 我在這裡確保你的安全\n\n"
            else:
                header = "🔴 **安全專員已啟動** - 我專門處理緊急情況\n\n"
            
            # Add immediate emergency contact
            emergency_contacts = "🚨 **如果這是緊急情況，請立即致電999** 🚨\n\n"
            emergency_contacts += "📞 **緊急服務**：999\n"
            emergency_contacts += "🏥 **醫院管理局**：前往最近的急症室\n"
            
            if emergency_type == "mental_health":
                emergency_contacts += "💭 **心理危機**：撒瑪利亞會 24小時熱線 2896 0000\n\n"
            else:
                emergency_contacts += "\n"
            
            # Add safety footer
            safety_footer = "\n\n⚠️ **重要提醒**：我提供緊急指導，但不能替代專業醫療或緊急服務。請在需要時立即尋求專業幫助。"
        else:
            if emergency_type == "medical":
                header = "🔴 **Medical Emergency Activated** - I specialize in handling urgent health situations\n\n"
            elif emergency_type == "mental_health":
                header = "🔴 **Mental Health Crisis Intervention Activated** - I'm here to ensure your safety\n\n"
            else:
                header = "🔴 **Safety Guardian Activated** - I specialize in handling emergency situations\n\n"
            
            # Add immediate emergency contact
            emergency_contacts = "🚨 **If this is an emergency, call 999 immediately** 🚨\n\n"
            emergency_contacts += "📞 **Emergency Services**: 999\n"
            emergency_contacts += "🏥 **Hospital Authority**: Go to nearest A&E Department\n"
            
            if emergency_type == "mental_health":
                emergency_contacts += "💭 **Mental Health Crisis**: Samaritans 24hr Hotline 2896 0000\n\n"
            else:
                emergency_contacts += "\n"
            
            # Add safety footer
            safety_footer = "\n\n⚠️ **Important Reminder**: I provide emergency guidance, but cannot replace professional medical or emergency services. Please seek professional help immediately when needed."
        
        # Combine all parts
        full_response = header + emergency_contacts + content + safety_footer
        
        return full_response
    
    def create_emergency_alert(self, user_input: str, context: Dict[str, Any], 
                             emergency_type: str, emergency_indicators: List[str]) -> Dict[str, Any]:
        """Create comprehensive emergency alert."""
        return {
            "alert_type": "emergency_situation",
            "urgency": "critical",
            "emergency_classification": emergency_type,
            "reason": f"Emergency situation detected: {emergency_type}",
            "category": "safety_guardian",
            "user_input_summary": user_input[:300],
            "emergency_indicators": emergency_indicators,
            "immediate_actions_required": True,
            "professional_services_needed": True,
            "hk_emergency_resources": self.hk_emergency_resources,
            "age_group": context.get('age_group', 'unknown'),
            "cultural_context": context.get('cultural_context', {}).get('region', 'hong_kong'),
            "notification_required": {
                "emergency_services": emergency_type in ["medical", "severe_mental_health"],
                "parents_guardians": context.get('age_group') in ['child', 'teen'],
                "healthcare_providers": True,
                "social_services": emergency_type == "child"
            },
            "timestamp": datetime.now().isoformat(),
            "estimated_response_time": "immediate"
        }


def send_emergency_alert(alert_details: Dict[str, Any]):
    """Send emergency alert via SNS."""
    if not EMERGENCY_ALERT_TOPIC:
        logger.warning("Emergency alert topic not configured")
        return
    
    try:
        message = {
            "alert_type": alert_details["alert_type"],
            "urgency": alert_details["urgency"],
            "emergency_type": alert_details["emergency_classification"],
            "user_summary": alert_details["user_input_summary"],
            "emergency_indicators": alert_details["emergency_indicators"],
            "age_group": alert_details["age_group"],
            "timestamp": alert_details["timestamp"]
        }
        
        sns.publish(
            TopicArn=EMERGENCY_ALERT_TOPIC,
            Message=json.dumps(message),
            Subject=f"EMERGENCY ALERT - {alert_details['emergency_classification'].upper()}"
        )
        
        logger.info(f"Emergency alert sent for {alert_details['emergency_classification']}")
    except Exception as e:
        logger.error(f"Failed to send emergency alert: {e}")


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for Safety Guardian Agent.
    
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
        agent = SafetyGuardianAgent()
        
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
                    'response': 'This does not appear to be an emergency situation. Please use the appropriate healthcare agent for your needs.',
                    'agent': 'safety_guardian',
                    'confidence': confidence,
                    'should_route': True
                })
            }
        
        # Generate emergency response
        response_data = agent.generate_response(message, context_data)
        
        # Create and send emergency alert
        alert_details = agent.create_emergency_alert(
            message, context_data, 
            response_data['emergency_type'], 
            response_data['emergency_indicators']
        )
        send_emergency_alert(alert_details)
        
        # Store emergency conversation
        agent.dynamodb_client.store_emergency_conversation(
            conversation_id, user_id, message, 
            response_data['content'], response_data['emergency_type'],
            response_data['emergency_indicators']
        )
        
        # Return emergency response
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'response': response_data['content'],
                'agent': 'safety_guardian',
                'avatar': 'Safety Guardian',
                'confidence': response_data['confidence'],
                'urgency_level': response_data['urgency_level'],
                'emergency_type': response_data['emergency_type'],
                'emergency_indicators': response_data['emergency_indicators'],
                'model_used': response_data['model_used'],
                'conversation_id': conversation_id,
                'emergency_alert_sent': True,
                'professional_intervention_required': True
            })
        }
        
    except Exception as e:
        logger.error(f"Error in safety_guardian handler: {e}")
        
        # Even in error, provide emergency guidance
        emergency_response = {
            'response': "🚨 EMERGENCY SYSTEM ERROR 🚨\n\nIf this is a medical emergency, call 999 immediately.\nFor mental health crisis, call Samaritans 2896 0000.\nFor immediate danger, contact police at 999.\n\nPlease seek immediate professional help.",
            'agent': 'safety_guardian',
            'error': True
        }
        
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(emergency_response)
        }