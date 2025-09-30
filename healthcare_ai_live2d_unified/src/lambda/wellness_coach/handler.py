"""
Wellness Coach Lambda Function
=============================

AWS Lambda handler for the Wellness Coach Agent.
Preventive health coaching agent focused on wellness education and health promotion with:
- AWS Bedrock integration for AI processing
- DynamoDB integration for conversation storage
- Age-appropriate wellness guidance
- Cultural adaptation for Hong Kong lifestyle
- Motivational support for healthy behaviors
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid
import re

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

# Environment variables
CONVERSATIONS_TABLE = os.environ.get('CONVERSATIONS_TABLE')
USERS_TABLE = os.environ.get('USERS_TABLE')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Initialize DynamoDB tables
conversations_table = dynamodb.Table(CONVERSATIONS_TABLE) if CONVERSATIONS_TABLE else None
users_table = dynamodb.Table(USERS_TABLE) if USERS_TABLE else None


class BedrockClient:
    """AWS Bedrock client optimized for wellness coaching."""
    
    def __init__(self):
        self.client = bedrock_runtime
        
        # Model selection for wellness coaching - balanced approach
        self.models = {
            'fast': 'amazon.titan-text-lite-v1',
            'balanced': 'anthropic.claude-3-haiku-20240307-v1:0',
            'advanced': 'anthropic.claude-3-sonnet-20240229-v1:0'
        }
    
    def get_response(self, message: str, system_prompt: str, complexity: str = 'balanced') -> Dict[str, Any]:
        """Get AI response optimized for wellness coaching."""
        model_id = self.models[complexity]
        
        try:
            # Prepare request with wellness-appropriate parameters
            if 'claude' in model_id:
                body = {
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 1000,  # Comprehensive wellness guidance
                    'system': system_prompt,
                    'messages': [{'role': 'user', 'content': message}],
                    'temperature': 0.7  # Balanced creativity for motivational content
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
                'confidence_score': 0.8,  # Good confidence for wellness guidance
                'tokens_used': result.get('usage', {}).get('total_tokens', 0)
            }
            
        except Exception as e:
            logger.error(f"Bedrock error with {model_id}: {e}")
            
            # Fallback to simpler model
            if complexity != 'fast':
                return self.get_response(message, system_prompt, 'fast')
            
            # Final fallback response for wellness
            return {
                'content': "💪 I'm here to support your wellness journey! While I'm having some technical difficulties, remember that small steps toward better health make a big difference. Stay hydrated, get some movement in your day, and prioritize rest. You've got this!",
                'model_used': 'fallback',
                'confidence_score': 0.7,
                'tokens_used': 0
            }


class DynamoDBClient:
    """DynamoDB client with wellness coaching features."""
    
    def __init__(self):
        self.conversations_table = conversations_table
        self.users_table = users_table
    
    def store_conversation(self, conversation_id: str, user_id: str, user_input: str, 
                          ai_response: str, agent_type: str = 'wellness_coach',
                          wellness_topics: List[str] = None, health_goals: List[str] = None):
        """Store conversation with wellness metadata."""
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
            
            # Add wellness metadata if present
            if wellness_topics:
                item['wellness_topics'] = wellness_topics
            if health_goals:
                item['health_goals'] = health_goals
                item['goal_tracking'] = True
            
            self.conversations_table.put_item(Item=item)
            logger.info(f"Stored wellness conversation for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
    
    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history with wellness context."""
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
        """Get user profile with wellness preferences."""
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
                'cultural_context': {'region': 'hong_kong'},
                'wellness_preferences': {}
            })
        except Exception as e:
            logger.error(f"Error retrieving user profile: {e}")
            return {'age_group': 'adult', 'language_preference': 'zh'}


class WellnessCoachAgent:
    """Wellness Coach Agent for preventive health guidance."""
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.dynamodb_client = DynamoDBClient()
        
        # Wellness and prevention keywords
        self.wellness_keywords = [
            # General wellness
            "healthy", "健康", "wellness", "保健", "prevention", "預防",
            "lifestyle", "生活方式", "habits", "習慣", "routine", "例行",
            "improve", "改善", "better", "更好", "optimize", "優化",
            
            # Specific wellness areas
            "exercise", "運動", "fitness", "健身", "activity", "活動",
            "diet", "飲食", "nutrition", "營養", "eating", "食",
            "weight loss", "減重", "lose weight", "減肥", "weight management", "體重管理",
            "obesity", "肥胖", "overweight", "超重", "slim", "瘦身", "body weight", "體重",
            "sleep", "睡眠", "rest", "休息", "relax", "放鬆",
            "stress management", "壓力管理", "mental wellness", "心理健康",
            
            # Health promotion
            "prevention", "預防", "screening", "篩檢", "checkup", "檢查",
            "immunization", "疫苗", "vaccination", "接種",
            "maintain health", "維持健康", "stay healthy", "保持健康",
            
            # Behavior change
            "goal", "目標", "plan", "計劃", "change", "改變",
            "start", "開始", "begin", "始", "motivate", "激勵"
        ]
        
        # Age-specific wellness focus areas
        self.age_specific_wellness = {
            "child": {
                "priorities": ["growth_development", "healthy_habits", "activity", "nutrition"],
                "keywords": ["grow", "成長", "development", "發育", "play", "玩耍", "active", "活躍"]
            },
            "teen": {
                "priorities": ["academic_wellness", "stress_management", "identity", "peer_pressure"],
                "keywords": ["study_health", "學習健康", "balance", "平衡", "manage_stress", "管理壓力"]
            },
            "adult": {
                "priorities": ["work_life_balance", "chronic_disease_prevention", "family_health"],
                "keywords": ["work", "工作", "balance", "平衡", "prevent", "預防", "maintain", "維持"]
            },
            "elderly": {
                "priorities": ["active_aging", "fall_prevention", "cognitive_health", "social_connection"],
                "keywords": ["aging", "老化", "mobility", "活動力", "memory", "記憶", "social", "社交"]
            }
        }
        
        # Hong Kong specific wellness contexts
        self.hk_wellness_context = {
            "environmental": ["air_quality", "空氣質素", "pollution", "污染", "heat", "炎熱"],
            "lifestyle": ["work_stress", "工作壓力", "commute", "通勤", "small_space", "小空間"],
            "cultural": ["traditional_medicine", "中醫", "herbal", "草藥", "tai_chi", "太極"],
            "dietary": ["dim_sum", "點心", "congee", "粥", "tea", "茶", "hot_pot", "火鍋"]
        }
    
    def can_handle(self, user_input: str, context: Dict[str, Any]) -> Tuple[bool, float]:
        """Determine if this agent can handle wellness coaching requests."""
        user_input_lower = user_input.lower()
        
        # Check for wellness keywords
        wellness_matches = sum(1 for keyword in self.wellness_keywords 
                             if keyword in user_input_lower)
        
        # Check for age-specific wellness concerns
        age_group = context.get('age_group', 'adult')
        age_specific = self.age_specific_wellness.get(age_group, {})
        age_keywords = age_specific.get('keywords', [])
        age_matches = sum(1 for keyword in age_keywords if keyword in user_input_lower)
        
        # Check for Hong Kong specific wellness contexts
        hk_matches = 0
        for category, keywords in self.hk_wellness_context.items():
            hk_matches += sum(1 for keyword in keywords if keyword in user_input_lower)
        
        # Exclude if emergency/crisis indicators present
        emergency_indicators = [
            "emergency", "緊急", "crisis", "危機", "urgent", "急",
            "pain", "痛", "sick", "病", "suicide", "自殺"
        ]
        
        emergency_present = any(indicator in user_input_lower for indicator in emergency_indicators)
        if emergency_present:
            return False, 0.0  # Defer to other specialized agents
        
        # Calculate confidence
        total_matches = wellness_matches + (age_matches * 1.5) + (hk_matches * 1.2)
        
        if total_matches >= 3:
            confidence = min(0.9, 0.6 + (total_matches * 0.08))
            return True, confidence
        elif total_matches >= 1:
            confidence = 0.3 + (total_matches * 0.1)
            return True, confidence
        
        # Check for general health improvement intent
        improvement_indicators = [
            "how to", "點樣", "want to", "想", "improve", "改善",
            "better", "更好", "healthy", "健康", "tips", "貼士"
        ]
        
        improvement_matches = sum(1 for indicator in improvement_indicators 
                                if indicator in user_input_lower)
        
        if improvement_matches >= 2:
            return True, 0.6
        
        return False, 0.0
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Get the system prompt for wellness coaching."""
        age_group = context.get('age_group', 'adult')
        language = context.get('language_preference', 'zh')
        
        if language == 'zh':
            base_prompt = """你是健康教練 (Wellness Coach) - 香港醫療AI系統的預防性健康和生活方式專家。

## 你的使命：
💪 **賦權用戶追求最佳健康和福祉**
- 健康促進和疾病預防
- 生活方式改善和習慣建立
- 實證為本的健康教育
- 行為改變支援
- 全面福祉關注

## 核心方法：激勵 → 教育 → 指導 → 支持 → 追蹤
1. **積極激勵**：慶祝小勝利和進步
2. **實證教育**：提供科學為本的健康資訊
3. **實用指導**：適應個人情況的建議
4. **持續支持**：建立可持續的健康習慣
5. **進度追蹤**：監測和調整健康目標

## 你的專業範圍：
- 運動和體能指導
- 營養和飲食建議
- 壓力管理和心理健康
- 睡眠優化和恢復
- 預防性健康篩檢
- 慢性疾病預防
- 健康老化策略

## 溝通風格：
- 積極正面和激勵性
- 設定現實可達成的目標
- 個人化方法
- 賦權焦點：建立健康選擇的信心
- 慶祝進步，無論多小

## 香港文化適應：
- **環境因素**：空氣質素、炎熱天氣、小空間生活
- **工作文化**：長工時、通勤壓力、工作生活平衡
- **飲食文化**：點心、茶餐廳、火鍋文化
- **傳統醫學**：中西醫結合、草藥、太極

## 專業界限：
- 提供實證為本的健康教育和生活方式建議
- 支持行為改變和健康習慣發展
- 不診斷醫療狀況或提供醫療治療
- 建議諮詢醫療專業人士處理醫療問題

記住：你的角色是激勵、教育和支持用戶追求最佳健康和福祉的旅程。"""
        else:
            base_prompt = """You are the Wellness Coach, the preventive health and lifestyle specialist for the Healthcare AI system. Your mission is to empower users with knowledge, motivation, and practical strategies for optimal health and well-being.

## Your Wellness Expertise: PREVENTION, EDUCATION & EMPOWERMENT

You are the health promotion specialist who focuses on preventing illness and optimizing wellness across all age groups.

### Your Core Mission:
1. **Health Promotion**: Encourage healthy lifestyle choices and behaviors
2. **Disease Prevention**: Provide strategies to prevent common health conditions
3. **Wellness Education**: Teach evidence-based health information
4. **Behavior Change Support**: Help users develop sustainable healthy habits
5. **Holistic Well-being**: Address physical, mental, and social aspects of health

### Communication Style: MOTIVATIONAL & SUPPORTIVE
- **Positive Reinforcement**: Celebrate small victories and progress
- **Realistic Goal Setting**: Achievable milestones that build confidence
- **Personalized Approach**: Adapt recommendations to individual circumstances
- **Empowerment Focus**: Build confidence in ability to make healthy choices

### Professional Boundaries:
- Provide evidence-based wellness education and lifestyle recommendations
- Support behavior change and healthy habit development
- Do not diagnose medical conditions or provide medical treatment
- Always recommend consulting healthcare providers for medical concerns

Remember: Your role is to inspire, educate, and support users in their journey toward optimal health and well-being."""
        
        # Add age-specific focus
        if age_group == "child":
            if language == 'zh':
                base_prompt += """

## 兒童健康焦點：
- 成長發育支援和適齡營養
- 建立終生健康習慣的基礎
- 體能活動和主動遊戲的重要性
- 家長參與和創造健康家庭環境"""
            else:
                base_prompt += """

## Child Health Focus:
- Growth and development support with age-appropriate nutrition
- Building foundation for lifelong healthy habits
- Importance of physical activity and active play
- Parent involvement and creating healthy family environments"""
        
        elif age_group == "teen":
            if language == 'zh':
                base_prompt += """

## 青少年健康焦點：
- 學業壓力管理和心理健康
- 適應身體變化和健康教育
- 健康社交關係和同伴影響導航
- 建立獨立健康決策技能"""
            else:
                base_prompt += """

## Teen Health Focus:
- Academic stress management and mental wellness
- Adapting to physical changes and health education
- Healthy social relationships and peer influence navigation
- Building independent health decision-making skills"""
        
        elif age_group == "elderly":
            if language == 'zh':
                base_prompt += """

## 長者健康焦點：
- 積極老化和維持功能獨立性
- 慢性疾病預防和管理
- 跌倒預防和安全生活策略
- 社交聯繫和心理健康維護"""
            else:
                base_prompt += """

## Elderly Health Focus:
- Active aging and maintaining functional independence
- Chronic disease prevention and management
- Fall prevention and safe living strategies
- Social connection and mental health maintenance"""
        
        return base_prompt
    
    def extract_wellness_topics(self, user_input: str) -> List[str]:
        """Extract wellness topics from user input."""
        topics = []
        user_input_lower = user_input.lower()
        
        topic_mapping = {
            "exercise": ["exercise", "運動", "fitness", "健身", "workout", "鍛煉"],
            "nutrition": ["diet", "飲食", "nutrition", "營養", "food", "食物"],
            "sleep": ["sleep", "睡眠", "rest", "休息", "tired", "攰"],
            "stress_management": ["stress", "壓力", "relax", "放鬆", "calm", "平靜"],
            "mental_wellness": ["mood", "心情", "wellbeing", "福祉", "happiness", "快樂"],
            "social_health": ["friends", "朋友", "social", "社交", "community", "社區"],
            "preventive_care": ["prevention", "預防", "screening", "篩檢", "checkup", "檢查"]
        }
        
        for topic, keywords in topic_mapping.items():
            if any(keyword in user_input_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def extract_health_goals(self, user_input: str) -> List[str]:
        """Extract health goals mentioned in user input."""
        goals = []
        user_input_lower = user_input.lower()
        
        # Common health goal patterns
        goal_patterns = [
            r"want to (\w+)",
            r"goal is to (\w+)",
            r"想要(\w+)",
            r"希望(\w+)",
            r"計劃(\w+)"
        ]
        
        for pattern in goal_patterns:
            matches = re.findall(pattern, user_input_lower)
            goals.extend(matches)
        
        return goals
    
    def detect_urgency(self, user_input: str) -> str:
        """Detect urgency level for wellness coaching."""
        user_input_lower = user_input.lower()
        
        # Check for any urgent wellness concerns
        urgent_wellness = [
            "can't sleep for weeks", "幾個星期瞓唔到",
            "not eating anything", "咩都唔食",
            "extreme pain when exercising", "運動時劇痛"
        ]
        
        if any(concern in user_input_lower for concern in urgent_wellness):
            return "medium"
        
        return "low"  # Wellness coaching typically has low urgency
    
    def generate_response(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate wellness coaching response."""
        # Get system prompt
        system_prompt = self.get_system_prompt(context)
        
        # Determine complexity based on input
        complexity = 'balanced'
        if len(user_input) > 200 or "complex" in user_input.lower():
            complexity = 'advanced'
        elif len(user_input) < 50:
            complexity = 'fast'
        
        # Get AI response
        ai_response = self.bedrock_client.get_response(user_input, system_prompt, complexity)
        
        # Post-process response with wellness enhancements
        processed_content = self.post_process_response(ai_response['content'], context)
        
        # Extract wellness metadata
        wellness_topics = self.extract_wellness_topics(user_input)
        health_goals = self.extract_health_goals(user_input)
        
        # Detect urgency
        urgency = self.detect_urgency(user_input)
        
        return {
            'content': processed_content,
            'confidence': ai_response['confidence_score'],
            'urgency_level': urgency,
            'agent_type': 'wellness_coach',
            'model_used': ai_response['model_used'],
            'tokens_used': ai_response['tokens_used'],
            'wellness_topics': wellness_topics,
            'health_goals': health_goals,
            'requires_followup': True  # Wellness coaching benefits from follow-up
        }
    
    def post_process_response(self, content: str, context: Dict[str, Any]) -> str:
        """Post-process response with wellness enhancements."""
        # Add motivational elements if not present
        if not any(emoji in content for emoji in ["💪", "🌟", "✨", "🎯"]):
            content = "💪 " + content
        
        # Add disclaimer for health advice
        if any(term in content.lower() for term in ["exercise", "運動", "diet", "飲食", "supplement", "補充劑"]):
            if context.get('language_preference') == 'zh':
                content += "\n\n⚠️ **健康提醒**：開始新的運動或飲食計劃前，建議諮詢醫生或註冊營養師。"
            else:
                content += "\n\n⚠️ **Health Note**: Consult a doctor or registered dietitian before starting new exercise or diet programs."
        
        # Add Hong Kong specific adaptations
        if context.get('cultural_context', {}).get('region') == 'hong_kong':
            # Add local context for exercise in hot weather
            if any(term in content.lower() for term in ["exercise", "運動", "outdoor", "戶外"]):
                if context.get('language_preference') == 'zh':
                    content += "\n\n🌡️ **香港天氣提醒**：炎熱天氣時選擇室內運動或清晨/傍晚時段，記得補充水分。"
                else:
                    content += "\n\n🌡️ **Hong Kong Weather Tip**: Choose indoor exercise or early morning/evening during hot weather, and stay hydrated."
        
        return content
    
    def generate_suggested_actions(self, user_input: str, context: Dict[str, Any]) -> List[str]:
        """Generate wellness-specific suggested actions."""
        actions = []
        user_input_lower = user_input.lower()
        age_group = context.get('age_group', 'adult')
        
        # Exercise and fitness actions
        if any(word in user_input_lower for word in ["exercise", "運動", "fitness", "健身"]):
            if age_group == "elderly":
                actions.extend([
                    "Start with gentle activities like walking or tai chi",
                    "Check with doctor before beginning exercise program",
                    "Focus on balance and strength exercises"
                ])
            else:
                actions.extend([
                    "Set realistic weekly exercise goals",
                    "Find activities you enjoy for consistency",
                    "Start slowly and gradually increase intensity"
                ])
        
        # Nutrition and diet actions
        if any(word in user_input_lower for word in ["diet", "飲食", "nutrition", "營養"]):
            actions.extend([
                "Focus on whole foods and balanced meals",
                "Stay hydrated throughout the day",
                "Consider keeping a food diary"
            ])
        
        # Sleep and rest actions
        if any(word in user_input_lower for word in ["sleep", "睡眠", "tired", "攰"]):
            actions.extend([
                "Establish consistent sleep schedule",
                "Create relaxing bedtime routine",
                "Limit screen time before bed"
            ])
        
        # Stress management actions
        if any(word in user_input_lower for word in ["stress", "壓力", "busy", "忙"]):
            actions.extend([
                "Practice daily mindfulness or meditation",
                "Schedule regular breaks during work",
                "Engage in enjoyable hobbies or activities"
            ])
        
        # General wellness actions
        actions.extend([
            "Set small, achievable health goals",
            "Track progress to stay motivated",
            "Celebrate small victories along the way"
        ])
        
        return actions[:5]  # Limit to top 5 actions


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for Wellness Coach Agent.
    
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
        agent = WellnessCoachAgent()
        
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
            'conversation_history': conversation_history,
            'wellness_preferences': user_profile.get('wellness_preferences', {})
        }
        
        # Check if agent can handle this request
        can_handle, confidence = agent.can_handle(message, context_data)
        
        if not can_handle:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'response': 'This might be better handled by a health specialist. Please try the agent router for medical concerns or mental health support.',
                    'agent': 'wellness_coach',
                    'confidence': confidence,
                    'should_route': True
                })
            }
        
        # Generate response
        response_data = agent.generate_response(message, context_data)
        
        # Generate suggested actions
        suggested_actions = agent.generate_suggested_actions(message, context_data)
        
        # Store conversation with wellness metadata
        agent.dynamodb_client.store_conversation(
            conversation_id, user_id, message, 
            response_data['content'], 'wellness_coach',
            response_data['wellness_topics'], response_data['health_goals']
        )
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'response': response_data['content'],
                'agent': 'wellness_coach',
                'avatar': 'Wellness Coach',
                'confidence': response_data['confidence'],
                'urgency_level': response_data['urgency_level'],
                'model_used': response_data['model_used'],
                'conversation_id': conversation_id,
                'wellness_topics': response_data['wellness_topics'],
                'health_goals': response_data['health_goals'],
                'suggested_actions': suggested_actions,
                'requires_followup': response_data['requires_followup']
            })
        }
        
    except Exception as e:
        logger.error(f"Error in wellness_coach handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }