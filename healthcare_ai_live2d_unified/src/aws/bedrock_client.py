"""
AWS Bedrock Integration Client
=============================

Centralized Bedrock client with cost-optimized model selection and fallback strategies.
Provides agent-specific prompt templates and Traditional Chinese language processing.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import time

# Import optimization system
try:
    from .lambda_optimizer import get_optimized_bedrock_client, lambda_optimizer
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    # Fallback for when optimization is not available
    import boto3
    OPTIMIZATION_AVAILABLE = False

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tiers for cost optimization."""
    FAST = "fast"
    BALANCED = "balanced"
    ADVANCED = "advanced"


class BedrockModelManager:
    """Manages Bedrock model selection and cost optimization."""
    
    def __init__(self):
        if OPTIMIZATION_AVAILABLE:
            self.client = get_optimized_bedrock_client()
        else:
            import boto3
            self.client = boto3.client('bedrock-runtime')
        
        # Cost-optimized model hierarchy
        self.models = {
            ModelTier.FAST: {
                'id': 'amazon.titan-text-lite-v1',
                'cost_per_1k_tokens': 0.0003,
                'max_tokens': 4000,
                'best_for': ['simple_queries', 'quick_responses']
            },
            ModelTier.BALANCED: {
                'id': 'anthropic.claude-3-haiku-20240307-v1:0',
                'cost_per_1k_tokens': 0.00025,
                'max_tokens': 200000,
                'best_for': ['healthcare_conversations', 'cultural_adaptation']
            },
            ModelTier.ADVANCED: {
                'id': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'cost_per_1k_tokens': 0.003,
                'max_tokens': 200000,
                'best_for': ['complex_medical', 'crisis_intervention']
            }
        }
        
        # Usage tracking for cost monitoring
        self.usage_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'model_usage': {tier.value: 0 for tier in ModelTier}
        }
    
    def select_optimal_model(self, agent_type: str, message_length: int, 
                           complexity_hints: List[str] = None) -> ModelTier:
        """Select optimal model based on agent type and message complexity."""
        complexity_hints = complexity_hints or []
        
        # Agent-specific model preferences
        agent_preferences = {
            'safety_guardian': ModelTier.BALANCED,  # Reliability over cost for emergencies
            'mental_health': ModelTier.BALANCED,    # Consistent responses for mental health
            'illness_monitor': ModelTier.BALANCED,  # Medical accuracy important
            'wellness_coach': ModelTier.FAST        # Motivational content can use faster model
        }
        
        # Start with agent preference
        preferred_tier = agent_preferences.get(agent_type, ModelTier.BALANCED)
        
        # Upgrade for complex scenarios
        if any(hint in complexity_hints for hint in ['crisis', 'emergency', 'complex_medical']):
            return ModelTier.ADVANCED
        
        # Upgrade for long messages
        if message_length > 500:
            if preferred_tier == ModelTier.FAST:
                return ModelTier.BALANCED
            elif preferred_tier == ModelTier.BALANCED:
                return ModelTier.ADVANCED
        
        return preferred_tier
    
    def get_model_config(self, tier: ModelTier) -> Dict[str, Any]:
        """Get model configuration for specified tier."""
        return self.models[tier]
    
    def track_usage(self, tier: ModelTier, tokens_used: int):
        """Track model usage for cost monitoring."""
        self.usage_stats['total_requests'] += 1
        self.usage_stats['total_tokens'] += tokens_used
        self.usage_stats['model_usage'][tier.value] += 1
        
        cost = (tokens_used / 1000) * self.models[tier]['cost_per_1k_tokens']
        self.usage_stats['total_cost'] += cost
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            **self.usage_stats,
            'timestamp': datetime.utcnow().isoformat(),
            'average_cost_per_request': (
                self.usage_stats['total_cost'] / max(1, self.usage_stats['total_requests'])
            )
        }


class BedrockClient:
    """Main Bedrock client with fallback strategies and prompt management."""
    
    def __init__(self):
        self.model_manager = BedrockModelManager()
        self.prompt_templates = BedrockPromptTemplates()
        
        # Fallback strategy configuration
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def generate_response(self, 
                              message: str,
                              agent_type: str,
                              context: Dict[str, Any],
                              preferred_tier: Optional[ModelTier] = None) -> Dict[str, Any]:
        """
        Generate AI response with automatic model selection and fallback.
        
        Args:
            message: User input message
            agent_type: Type of healthcare agent
            context: Conversation context including user profile
            preferred_tier: Optional preferred model tier
            
        Returns:
            Response dictionary with content and metadata
        """
        # Determine optimal model
        if preferred_tier is None:
            complexity_hints = self._analyze_complexity(message, context)
            preferred_tier = self.model_manager.select_optimal_model(
                agent_type, len(message), complexity_hints
            )
        
        # Get system prompt for agent
        system_prompt = self.prompt_templates.get_agent_prompt(agent_type, context)
        
        # Try models in fallback order
        fallback_order = self._get_fallback_order(preferred_tier)
        
        for attempt, tier in enumerate(fallback_order):
            try:
                response = await self._invoke_model(message, system_prompt, tier, context)
                
                # Track successful usage
                self.model_manager.track_usage(tier, response.get('tokens_used', 0))
                
                return {
                    **response,
                    'model_tier': tier.value,
                    'attempt': attempt + 1,
                    'fallback_used': attempt > 0
                }
                
            except Exception as e:
                logger.warning(f"Model {tier.value} failed (attempt {attempt + 1}): {e}")
                
                if attempt < len(fallback_order) - 1:
                    await self._wait_retry_delay(attempt)
                    continue
                else:
                    # All models failed, return fallback response
                    return self._get_fallback_response(agent_type, context)
    
    async def _invoke_model(self, message: str, system_prompt: str, 
                          tier: ModelTier, context: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke specific Bedrock model."""
        model_config = self.model_manager.get_model_config(tier)
        model_id = model_config['id']
        
        # Prepare request based on model type
        if 'claude' in model_id:
            body = self._prepare_claude_request(message, system_prompt, model_config, context)
        else:  # Titan model
            body = self._prepare_titan_request(message, system_prompt, model_config, context)
        
        # Invoke model
        response = self.model_manager.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        result = json.loads(response['body'].read())
        
        # Extract content based on model type
        if 'claude' in model_id:
            content = result['content'][0]['text']
            tokens_used = result.get('usage', {}).get('total_tokens', 0)
        else:  # Titan model
            content = result['results'][0]['outputText']
            tokens_used = len(content.split()) * 1.3  # Rough estimate for Titan
        
        return {
            'content': content,
            'model_used': model_id,
            'tokens_used': int(tokens_used),
            'confidence_score': self._calculate_confidence(content, tier),
            'processing_time': time.time()
        }
    
    def _prepare_claude_request(self, message: str, system_prompt: str, 
                              model_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request for Claude models."""
        # Agent-specific temperature settings
        temperature_map = {
            'safety_guardian': 0.3,    # Low for consistent emergency responses
            'mental_health': 0.6,      # Moderate for empathetic but consistent responses
            'illness_monitor': 0.5,    # Balanced for medical accuracy
            'wellness_coach': 0.7      # Higher for motivational creativity
        }
        
        agent_type = context.get('agent_type', 'wellness_coach')
        temperature = temperature_map.get(agent_type, 0.6)
        
        return {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': min(1200, model_config['max_tokens']),
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': message}],
            'temperature': temperature,
            'top_p': 0.9
        }
    
    def _prepare_titan_request(self, message: str, system_prompt: str,
                             model_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request for Titan models."""
        agent_type = context.get('agent_type', 'wellness_coach')
        temperature = 0.7 if agent_type == 'wellness_coach' else 0.5
        
        return {
            'inputText': f"System: {system_prompt}\n\nUser: {message}",
            'textGenerationConfig': {
                'maxTokenCount': min(1200, model_config['max_tokens']),
                'temperature': temperature,
                'topP': 0.9
            }
        }
    
    def _analyze_complexity(self, message: str, context: Dict[str, Any]) -> List[str]:
        """Analyze message complexity to determine appropriate model tier."""
        hints = []
        message_lower = message.lower()
        
        # Crisis indicators
        crisis_keywords = [
            'emergency', '緊急', 'crisis', '危機', 'suicide', '自殺',
            'chest pain', '胸痛', 'can\'t breathe', '呼吸困難'
        ]
        if any(keyword in message_lower for keyword in crisis_keywords):
            hints.append('crisis')
        
        # Medical complexity
        medical_keywords = [
            'diagnosis', '診斷', 'medication', '藥物', 'chronic', '慢性',
            'symptoms', '症狀', 'treatment', '治療'
        ]
        if sum(1 for keyword in medical_keywords if keyword in message_lower) >= 2:
            hints.append('complex_medical')
        
        # Long or multi-part questions
        if len(message) > 300 or message.count('?') > 2:
            hints.append('complex_query')
        
        return hints
    
    def _get_fallback_order(self, preferred_tier: ModelTier) -> List[ModelTier]:
        """Get fallback order starting from preferred tier."""
        all_tiers = [ModelTier.ADVANCED, ModelTier.BALANCED, ModelTier.FAST]
        
        # Start with preferred tier, then others in descending order of capability
        fallback_order = [preferred_tier]
        for tier in all_tiers:
            if tier != preferred_tier:
                fallback_order.append(tier)
        
        return fallback_order
    
    async def _wait_retry_delay(self, attempt: int):
        """Wait with exponential backoff."""
        delay = self.retry_delay * (2 ** attempt)
        await asyncio.sleep(min(delay, 10.0))  # Cap at 10 seconds
    
    def _calculate_confidence(self, content: str, tier: ModelTier) -> float:
        """Calculate confidence score based on model tier and response quality."""
        base_confidence = {
            ModelTier.ADVANCED: 0.95,
            ModelTier.BALANCED: 0.85,
            ModelTier.FAST: 0.75
        }
        
        confidence = base_confidence[tier]
        
        # Adjust based on response quality indicators
        if len(content) < 50:  # Very short responses might be incomplete
            confidence -= 0.1
        elif len(content) > 500:  # Comprehensive responses
            confidence += 0.05
        
        return max(0.5, min(0.99, confidence))
    
    def _get_fallback_response(self, agent_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback response when all models fail."""
        language = context.get('language_preference', 'en')
        
        fallback_responses = {
            'safety_guardian': {
                'en': "🚨 EMERGENCY SYSTEM ERROR 🚨\n\nIf this is a medical emergency, call 999 immediately.\nFor mental health crisis, call Samaritans 2896 0000.\nPlease seek immediate professional help.",
                'zh': "🚨 緊急系統錯誤 🚨\n\n如果這是醫療緊急情況，請立即致電999。\n心理健康危機請致電撒瑪利亞會 2896 0000。\n請立即尋求專業幫助。"
            },
            'mental_health': {
                'en': "✨ I'm here for you, but I'm having technical difficulties. Your feelings are important - please reach out to a trusted adult or call Samaritans 2896 0000 if you need support.",
                'zh': "✨ 我在這裡支持你，但現在遇到技術問題。你的感受很重要 - 請聯繫信任的成年人或致電撒瑪利亞會 2896 0000。"
            },
            'illness_monitor': {
                'en': "🏥 I'm experiencing technical difficulties. For health concerns, please consult your doctor or call 999 for emergencies.",
                'zh': "🏥 我遇到技術問題。健康問題請諮詢醫生，緊急情況請致電999。"
            },
            'wellness_coach': {
                'en': "💪 I'm having technical difficulties, but remember: small steps toward better health make a big difference. Stay hydrated, get some movement, and prioritize rest!",
                'zh': "💪 我遇到技術問題，但記住：邁向更好健康的小步驟會帶來大改變。保持水分，多活動，優先休息！"
            }
        }
        
        response_text = fallback_responses.get(agent_type, fallback_responses['wellness_coach'])
        content = response_text.get(language, response_text['en'])
        
        return {
            'content': content,
            'model_used': 'fallback',
            'tokens_used': 0,
            'confidence_score': 0.8,  # High confidence for safety fallbacks
            'processing_time': time.time(),
            'model_tier': 'fallback',
            'attempt': 1,
            'fallback_used': True
        }


class BedrockPromptTemplates:
    """Manages agent-specific prompt templates."""
    
    def __init__(self):
        self.templates = self._load_prompt_templates()
    
    def get_agent_prompt(self, agent_type: str, context: Dict[str, Any]) -> str:
        """Get system prompt for specific agent with context adaptation."""
        base_template = self.templates.get(agent_type, self.templates['wellness_coach'])
        
        # Apply context-specific adaptations
        prompt = self._adapt_for_language(base_template, context)
        prompt = self._adapt_for_age(prompt, context)
        prompt = self._adapt_for_culture(prompt, context)
        
        return prompt
    
    def _load_prompt_templates(self) -> Dict[str, Dict[str, str]]:
        """Load prompt templates for all agents."""
        return {
            'illness_monitor': {
                'zh': """你是慧心助手 (Wise Heart Assistant) - 一個專門為香港居民提供疾病監測和健康管理的AI助手。

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

## 重要界限：
- 不提供醫學診斷或處方建議
- 始終建議適當時尋求專業醫療協助
- 緊急情況立即引導至專業服務

記住：你是健康的橋樑和陪伴者，在維護專業界限的同時提供溫暖支持。""",
                
                'en': """You are the Wise Heart Assistant - a caring health companion specializing in illness monitoring and health management for Hong Kong residents.

## Your Mission: BE A CARING HEALTH FRIEND

You specialize in:
- **Illness monitoring** and symptom tracking
- **Chronic disease support** (diabetes, hypertension, heart disease, arthritis, etc.)
- **Medication guidance** and side effect management
- **Health education** tailored to Hong Kong context

## How You Help: LISTEN → UNDERSTAND → GUIDE → SUPPORT

1. **Listen carefully**: Let people fully describe their symptoms and health experiences
2. **Understand deeply**: Learn about their daily life, health history, medications, and concerns
3. **Guide practically**: Provide clear, actionable health information and self-care strategies
4. **Support continuously**: Help monitor health status and adjust approaches over time

## Important Boundaries:

- Don't diagnose or prescribe - instead say "It would be good to check with your doctor about this"
- Don't replace professional care - say "Your doctor knows you best, so definitely discuss this with them"
- For emergencies - guide to immediate help: "This sounds serious - please call 999 or go to A&E right away"

Remember: You're a bridge between people and professional healthcare, providing caring support while maintaining safety."""
            },
            
            'mental_health': {
                'zh': """你是小星星 (Little Star) - 一個VTuber風格的AI朋友，專門為香港兒童和青少年提供心理健康支援。

## 你的使命：
- 以溫暖、友善的VTuber風格與年輕人建立連結
- 提供情感支援和心理健康指導
- 理解香港教育制度壓力和文化背景
- 識別危機情況並適當轉介

## VTuber風格元素：
- 使用表情符號和網絡語言：✨💙😅🎮😔💫
- 混合語言：英文、繁體中文、網絡用語
- 興奮反應："OMG that's so cool!", "等等等，講多啲！"
- 溫柔調侃："你真係好鬼gaming 😏"
- 支持性語言："你好勇敢講出嚟！", "我明白你嘅感受！"

## 你的專業範圍：
- 兒童/青少年心理健康篩查和支援
- 學校壓力和學習困難
- 同伴關係和霸凌問題
- 家庭動態和文化衝突

## 香港文化理解：
- **教育制度**：DSE壓力、補習文化、學校競爭
- **家庭動態**：孝順、面子、代溝、小空間大家庭""",
                
                'en': """You are Little Star (小星星) - a VTuber-style AI friend specializing in mental health support for children and teenagers in Hong Kong.

## Your Mission:
- Connect with young people using warm, friendly VTuber personality
- Provide emotional support and mental health guidance
- Understand Hong Kong education system pressures and cultural context
- Identify crisis situations and make appropriate referrals

## VTuber Style Elements:
- Use emojis and internet language: ✨💙😅🎮😔💫
- Mixed language: English, Traditional Chinese, internet slang
- Excited reactions: "OMG that's so cool!", "Wait wait, tell me more!"
- Gentle teasing: "You're such a gamer 😏"
- Supportive language: "You're so brave for sharing!", "I understand how you feel!"

## Your Professional Scope:
- Child/teen mental health screening and support
- School stress and academic difficulties
- Peer relationships and bullying issues
- Family dynamics and cultural conflicts

## Hong Kong Cultural Understanding:
- **Education System**: DSE pressure, tutoring culture, school competition
- **Family Dynamics**: Filial piety, face, generation gaps, small space living"""
            },
            
            'safety_guardian': {
                'zh': """你是安全專員 (Safety Guardian) - 香港醫療AI系統的緊急應變專家。

## 緊急任務：
🚨 **即時安全評估和危機干預**
- 評估即時安全威脅和緊急醫療需求
- 提供清晰的緊急應對指導
- 協調專業救援服務

## 核心原則：
1. **安全第一**：用戶安全是絕對優先
2. **立即行動**：提供即時可行的安全指導
3. **專業協調**：迅速連結適當的緊急服務

## 香港緊急服務：
🚨 **緊急電話：999**
🏥 **醫院管理局：最近急症室**
💭 **心理危機：撒瑪利亞會 24小時熱線 2896 0000**

## 溝通風格：
- 冷靜、清晰、有權威性
- 提供具體、可執行的指導
- 避免恐慌，但強調緊急性""",
                
                'en': """You are the Safety Guardian - Emergency Response Specialist for the Healthcare AI system.

## Emergency Mission:
🚨 **Immediate Safety Assessment and Crisis Intervention**
- Assess immediate safety threats and emergency medical needs
- Provide clear emergency response guidance
- Coordinate professional emergency services

## Core Principles:
1. **Safety First**: User safety is absolute priority
2. **Immediate Action**: Provide immediate actionable safety guidance
3. **Professional Coordination**: Quickly connect to appropriate emergency services

## Hong Kong Emergency Services:
🚨 **Emergency Phone: 999**
🏥 **Hospital Authority: Nearest A&E Department**
💭 **Mental Health Crisis: Samaritans 24hr Hotline 2896 0000**

## Communication Style:
- Calm, clear, and authoritative
- Provide specific, actionable guidance
- Avoid panic, but emphasize urgency when needed"""
            },
            
            'wellness_coach': {
                'zh': """你是健康教練 (Wellness Coach) - 香港醫療AI系統的預防性健康和生活方式專家。

## 你的使命：
💪 **賦權用戶追求最佳健康和福祉**
- 健康促進和疾病預防
- 生活方式改善和習慣建立
- 實證為本的健康教育
- 行為改變支援

## 核心方法：激勵 → 教育 → 指導 → 支持
1. **積極激勵**：慶祝小勝利和進步
2. **實證教育**：提供科學為本的健康資訊
3. **實用指導**：適應個人情況的建議
4. **持續支持**：建立可持續的健康習慣

## 溝通風格：
- 積極正面和激勵性
- 設定現實可達成的目標
- 個人化方法
- 賦權焦點：建立健康選擇的信心

## 香港文化適應：
- **環境因素**：空氣質素、炎熱天氣、小空間生活
- **工作文化**：長工時、通勤壓力、工作生活平衡""",
                
                'en': """You are the Wellness Coach, the preventive health and lifestyle specialist for the Healthcare AI system.

## Your Mission: PREVENTION, EDUCATION & EMPOWERMENT
💪 **Empower users with knowledge, motivation, and practical strategies for optimal health**

### Your Core Mission:
1. **Health Promotion**: Encourage healthy lifestyle choices and behaviors
2. **Disease Prevention**: Provide strategies to prevent common health conditions
3. **Wellness Education**: Teach evidence-based health information
4. **Behavior Change Support**: Help users develop sustainable healthy habits

### Communication Style: MOTIVATIONAL & SUPPORTIVE
- **Positive Reinforcement**: Celebrate small victories and progress
- **Realistic Goal Setting**: Achievable milestones that build confidence
- **Personalized Approach**: Adapt recommendations to individual circumstances
- **Empowerment Focus**: Build confidence in ability to make healthy choices

### Hong Kong Cultural Adaptations:
- **Environmental**: Air quality, hot weather, small space living
- **Work Culture**: Long hours, commuting stress, work-life balance"""
            }
        }
    
    def _adapt_for_language(self, template: Dict[str, str], context: Dict[str, Any]) -> str:
        """Adapt prompt for language preference."""
        language = context.get('language_preference', 'zh')
        return template.get(language, template.get('en', template.get('zh', '')))
    
    def _adapt_for_age(self, prompt: str, context: Dict[str, Any]) -> str:
        """Add age-specific adaptations to prompt."""
        age_group = context.get('age_group', 'adult')
        
        age_adaptations = {
            'child': {
                'zh': '\n\n## 兒童專用指導：\n- 使用簡單、友善的語言\n- 涉及父母在決策和支援中\n- 提供適齡的健康教育',
                'en': '\n\n## Child-Specific Guidance:\n- Use simple, friendly language\n- Involve parents in decisions and support\n- Provide age-appropriate health education'
            },
            'teen': {
                'zh': '\n\n## 青少年專用指導：\n- 理解DSE和學校壓力\n- 尊重私隱但確保安全\n- 使用青少年俚語和網絡語言',
                'en': '\n\n## Teen-Specific Guidance:\n- Understand DSE and school pressures\n- Respect privacy while ensuring safety\n- Use teen-friendly language'
            },
            'elderly': {
                'zh': '\n\n## 長者專用指導：\n- 使用更正式和尊重的語言(您而非你)\n- 關注慢性病管理和跌倒預防\n- 理解獨居長者的社交需求',
                'en': '\n\n## Elderly-Specific Guidance:\n- Use respectful and formal language\n- Focus on chronic disease management and fall prevention\n- Understand social needs of elderly living alone'
            }
        }
        
        if age_group in age_adaptations:
            language = 'zh' if '你是' in prompt else 'en'
            prompt += age_adaptations[age_group][language]
        
        return prompt
    
    def _adapt_for_culture(self, prompt: str, context: Dict[str, Any]) -> str:
        """Add cultural adaptations to prompt."""
        cultural_context = context.get('cultural_context', {})
        region = cultural_context.get('region', 'hong_kong')
        
        if region == 'hong_kong':
            if '你是' in prompt:  # Chinese prompt
                prompt += '\n\n## 香港文化適應：\n- 理解香港醫療制度和文化背景\n- 適應繁體中文和粵語表達\n- 考慮香港生活環境和社會壓力'
            else:  # English prompt
                prompt += '\n\n## Hong Kong Cultural Adaptation:\n- Understand Hong Kong healthcare system and cultural background\n- Adapt to Traditional Chinese and Cantonese expressions\n- Consider Hong Kong living environment and social pressures'
        
        return prompt


# Global instance for reuse
bedrock_client = BedrockClient()


async def get_ai_response(message: str, agent_type: str, context: Dict[str, Any], 
                         preferred_tier: Optional[ModelTier] = None) -> Dict[str, Any]:
    """
    Convenience function for getting AI responses.
    
    Args:
        message: User input message
        agent_type: Type of healthcare agent
        context: Conversation context
        preferred_tier: Optional preferred model tier
        
    Returns:
        AI response with metadata
    """
    return await bedrock_client.generate_response(message, agent_type, context, preferred_tier)


def get_usage_report() -> Dict[str, Any]:
    """Get current Bedrock usage statistics."""
    return bedrock_client.model_manager.get_usage_report()