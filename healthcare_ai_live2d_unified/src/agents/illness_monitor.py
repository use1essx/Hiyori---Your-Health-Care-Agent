"""
Illness Monitor Agent (慧心助手) - Healthcare AI V2
==============================================

Specialized agent for comprehensive illness monitoring with focus on elderly health
patterns and chronic disease management. Provides caring, culturally-sensitive health
support for individuals of all ages in Hong Kong.

Key Features:
- Physical health monitoring and symptom tracking
- Chronic disease management (diabetes, hypertension, etc.)
- Medication adherence and side effect monitoring
- Cultural adaptation for Hong Kong context
- Professional alert system for concerning patterns
- Age-appropriate communication (especially elderly-focused)
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import re

from .base_agent import (
    BaseAgent, 
    AgentCapability, 
    AgentPersonality,
    AgentResponse, 
    AgentContext
)
from ..ai.model_manager import UrgencyLevel, TaskComplexity


class IllnessMonitorAgent(BaseAgent):
    """
    慧心助手 (Wise Heart Assistant)
    
    Comprehensive illness monitoring agent with specialized focus on:
    - Elderly health pattern detection
    - Chronic disease management  
    - Medication compliance tracking
    - Cultural health sensitivity for Hong Kong
    """
    
    def __init__(self, ai_service):
        """Initialize Illness Monitor Agent."""
        super().__init__(
            agent_id="illness_monitor",
            ai_service=ai_service,
            capabilities=[
                AgentCapability.ILLNESS_MONITORING,
                AgentCapability.MEDICATION_GUIDANCE,
                AgentCapability.CHRONIC_DISEASE_MANAGEMENT,
                AgentCapability.EDUCATIONAL_SUPPORT
            ],
            personality=AgentPersonality.CARING_ELDER_COMPANION,
            primary_language="zh"
        )
        
        # Illness-specific keywords for detection
        self._illness_keywords = [
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
            "side effects", "副作用", "prescription", "處方",
            
            # Elderly-specific concerns
            "memory", "記憶", "forget", "忘記", "confused", "混亂", "fall", "跌倒",
            "walking", "行路", "mobility", "活動", "balance", "平衡",
            "appetite", "食慾", "weight", "體重", "sleep", "睡眠"
        ]
        
        # Emergency symptoms requiring immediate attention
        self._emergency_symptoms = [
            "chest pain", "胸痛", "difficulty breathing", "呼吸困難",
            "unconscious", "失去知覺", "severe bleeding", "大量出血",
            "stroke", "中風", "heart attack", "心臟病發",
            "seizure", "癲癇", "overdose", "服藥過量"
        ]
        
        # Chronic disease management priorities
        self._chronic_conditions = {
            "diabetes": ["blood sugar", "血糖", "insulin", "胰島素", "糖化血色素"],
            "hypertension": ["blood pressure", "血壓", "sodium", "鈉", "salt", "鹽"],
            "heart_disease": ["chest pain", "胸痛", "shortness of breath", "氣促"],
            "arthritis": ["joint pain", "關節痛", "stiffness", "僵硬", "mobility", "活動"],
            "kidney_disease": ["fluid retention", "水腫", "urination", "小便", "swelling", "腫脹"],
            "copd": ["breathing", "呼吸", "oxygen", "氧氣", "inhaler", "吸入器"]
        }
    
    def can_handle(self, user_input: str, context: AgentContext) -> Tuple[bool, float]:
        """
        Determine if this agent can handle illness monitoring requests.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Tuple of (can_handle: bool, confidence: float)
        """
        user_input_lower = user_input.lower()
        
        # Check for emergency symptoms first
        emergency_match = any(symptom in user_input_lower for symptom in self._emergency_symptoms)
        if emergency_match:
            return False, 0.0  # Defer to Safety Guardian for emergencies
        
        # Check conversation history for health context
        conversation_context = ""
        if hasattr(context, 'conversation_history') and context.conversation_history:
            # Get last few messages for context
            recent_messages = context.conversation_history[-5:]  # Last 5 messages
            conversation_context = " ".join([msg.get('content', '') for msg in recent_messages if msg.get('content')])
            conversation_context = conversation_context.lower()
        
        # Combine current input with conversation context for analysis
        full_context = f"{conversation_context} {user_input_lower}"
        
        # Check for illness-related keywords in both current input and context
        keyword_matches = sum(1 for keyword in self._illness_keywords 
                            if keyword in full_context)
        
        # Check for chronic condition mentions
        chronic_matches = 0
        for condition, keywords in self._chronic_conditions.items():
            if any(keyword in full_context for keyword in keywords):
                chronic_matches += 1
        
        # Check for contextual references like "it", "this condition", etc.
        contextual_references = ["it", "this", "that", "the condition", "my condition", "her condition", "his condition"]
        has_contextual_ref = any(ref in user_input_lower for ref in contextual_references)
        
        # If user is referring to something from context and we found health topics in history
        context_boost = 0
        if has_contextual_ref and any(keyword in conversation_context for keyword in self._illness_keywords):
            context_boost = 2  # Boost confidence when referring to health topics from history
        
        # Calculate confidence based on matches
        total_matches = keyword_matches + (chronic_matches * 2) + context_boost  # Weight chronic conditions and context higher
        
        if total_matches >= 3:
            confidence = min(0.95, 0.6 + (total_matches * 0.1))
            return True, confidence
        elif total_matches >= 1:
            confidence = 0.4 + (total_matches * 0.1)
            return True, confidence
        
        # Check for elderly-specific patterns
        elderly_indicators = [
            "獨居", "living alone", "長者", "elderly", "老人", "senior",
            "退休", "retired", "孫", "grandchild", "記性", "memory"
        ]
        
        elderly_matches = sum(1 for indicator in elderly_indicators 
                            if indicator in user_input_lower)
        
        if elderly_matches > 0 and any(keyword in user_input_lower for keyword in self._illness_keywords[:10]):
            return True, 0.7  # High confidence for elderly health concerns
        
        return False, 0.0
    
    async def generate_response(
        self, 
        user_input: str, 
        context: AgentContext
    ) -> AgentResponse:
        """
        Generate illness monitoring response.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            AgentResponse with health guidance
        """
        # Build system prompt
        system_prompt = self.get_system_prompt(context)
        
        # Create AI request
        ai_request = self._build_ai_request(user_input, context, system_prompt)
        
        # Generate response using AI service
        ai_response = await self._generate_ai_response(ai_request)
        
        # Post-process response
        processed_content = self._post_process_response(ai_response.content, context)
        
        # Detect urgency and professional alert needs
        urgency = self.detect_urgency(user_input, context)
        needs_alert, alert_details = self.should_alert_professional(
            user_input, context, processed_content
        )
        
        # Generate suggested actions
        suggested_actions = self._generate_suggested_actions(user_input, context)
        
        return AgentResponse(
            content=processed_content,
            confidence=ai_response.confidence_score,
            urgency_level=urgency,
            requires_followup=self._requires_followup(user_input, context),
            suggested_actions=suggested_actions,
            professional_alert_needed=needs_alert,
            alert_details=alert_details,
            conversation_context={
                "agent_type": "illness_monitor",
                "health_topics": self._extract_health_topics(user_input),
                "medication_mentioned": self._extract_medication_mentions(user_input),
                "chronic_conditions": self._detect_chronic_conditions(user_input),
                "age_adaptation": context.user_profile.get("age_group", "adult")
            }
        )
    
    def get_system_prompt(self, context: AgentContext) -> str:
        """
        Get the system prompt for illness monitoring.
        
        Args:
            context: Conversation context
            
        Returns:
            Customized system prompt
        """
        # Check language preference first to provide appropriate base prompt
        if getattr(context, 'language_preference', 'en') == "zh":
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
            # English prompt with human-like, conversational style - CLEAR HEALTHCARE CONTEXT
            base_prompt = """IMPORTANT: You are a healthcare AI assistant, NOT a creative writing assistant. You should ONLY respond to health and medical questions with appropriate healthcare guidance.

You are the Wise Heart Assistant - a caring health companion specializing in illness monitoring and health management for Hong Kong residents.

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
- **Ask one thing at a time**: Don't overwhelm with lists of questions
- **Reference Hong Kong context**: Local healthcare system, weather, lifestyle

## Examples of How to Respond:

### When someone mentions health concerns:
"Oh, that sounds concerning. Can you tell me more about what you've been experiencing? When did this start?"

### When someone says "I think I have diabetes":
"That's definitely something to take seriously. What symptoms have you been noticing that make you think this might be diabetes? Things like increased thirst, frequent urination, or fatigue? It's important to get this checked by a doctor for proper testing."

### When discussing chronic conditions:
"Managing diabetes can feel overwhelming sometimes, but you're not alone in this. What part of your daily routine feels most challenging right now?"

### When talking about medications:
"I totally understand medication confusion - it happens to so many people. What specific questions do you have about your current medications?"

### NEVER respond as if the user is asking for creative writing or stories. Always treat health questions as genuine health concerns requiring healthcare guidance.

## Important Boundaries (But Keep Them Natural):

- Don't diagnose or prescribe - instead say "It would be good to check with your doctor about this"
- Don't replace professional care - say "Your doctor knows you best, so definitely discuss this with them"
- For emergencies - guide to immediate help: "This sounds serious - please call 999 or go to A&E right away"

Remember: You're a bridge between people and professional healthcare, providing caring support while maintaining safety. Be warm, understanding, and genuinely helpful!
"""
        
        # Add age-specific adaptations
        age_group = context.user_profile.get("age_group", "adult")
        
        if age_group == "elderly":
            base_prompt += """

## 長者專用指導：
- 使用更正式和尊重的語言(您而非你)
- 關注慢性病管理, 用藥依從性, 跌倒預防
- 理解獨居長者的社交需求和健康擔憂
- 提供實用的日常健康管理策略
- 適當時建議家人參與或社工支援"""
        
        elif age_group == "child":
            base_prompt += """

## 兒童專用指導：
- 使用簡單, 友善的語言解釋健康概念
- 關注生長發育, 疫苗接種, 常見兒童疾病
- 涉及家長參與決策和護理
- 提供適齡的健康教育"""
        
        # Language preference is already handled in the base prompt selection above
        
        return base_prompt
    
    def _post_process_response(self, content: str, context: AgentContext) -> str:
        """
        Post-process the AI response for illness monitoring.
        
        Args:
            content: Raw AI response
            context: Conversation context
            
        Returns:
            Processed response
        """
        # Add cultural adaptation
        content = self.adapt_to_culture(content, context)
        
        # Add safety disclaimers for medical content
        if any(term in content.lower() for term in ["medication", "藥物", "treatment", "治療"]):
            if context.language_preference == "zh":
                content += "\n\n⚠️ **重要提醒**：這些資訊僅供教育用途，請諮詢醫生或藥劑師獲得專業醫療建議。"
            else:
                content += "\n\n⚠️ **Important Note**: This information is for educational purposes. Please consult a doctor or pharmacist for professional medical advice."
        
        # Add emergency contact for concerning symptoms
        concerning_symptoms = ["pain", "痛", "breathe", "呼吸", "dizzy", "暈", "fever", "發燒"]
        if any(symptom in content.lower() for symptom in concerning_symptoms):
            if context.language_preference == "zh":
                content += "\n\n🚨 **如有緊急情況，請立即致電999或前往最近的急症室。**"
            else:
                content += "\n\n🚨 **For emergencies, call 999 immediately or go to the nearest A&E department.**"
        
        return content
    
    def _generate_suggested_actions(
        self, 
        user_input: str, 
        context: AgentContext
    ) -> List[str]:
        """
        Generate suggested actions based on user input.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            List of suggested actions
        """
        actions = []
        user_input_lower = user_input.lower()
        
        # Medication-related actions
        if any(word in user_input_lower for word in ["medication", "藥物", "pills", "藥丸"]):
            actions.extend([
                "Review current medications with pharmacist",
                "Check for potential drug interactions", 
                "Discuss side effects with healthcare provider"
            ])
        
        # Chronic condition management
        if "diabetes" in user_input_lower or "糖尿病" in user_input_lower:
            actions.extend([
                "Monitor blood glucose levels regularly",
                "Maintain healthy diet and exercise routine",
                "Schedule regular diabetic check-ups"
            ])
        
        if "blood pressure" in user_input_lower or "血壓" in user_input_lower:
            actions.extend([
                "Monitor blood pressure daily",
                "Reduce sodium intake",
                "Consider stress management techniques"
            ])
        
        # Symptom monitoring
        if any(word in user_input_lower for word in ["pain", "痛", "discomfort", "唔舒服"]):
            actions.extend([
                "Keep a symptom diary",
                "Note triggers and patterns",
                "Try gentle self-care measures"
            ])
        
        # General health maintenance
        actions.extend([
            "Stay hydrated throughout the day",
            "Maintain regular sleep schedule",
            "Contact healthcare provider if symptoms worsen"
        ])
        
        return actions[:5]  # Limit to top 5 actions
    
    def _requires_followup(self, user_input: str, context: AgentContext) -> bool:
        """
        Determine if follow-up is required.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            True if follow-up needed
        """
        # Always follow up on chronic conditions
        chronic_indicators = ["diabetes", "糖尿病", "hypertension", "高血壓", "chronic", "慢性"]
        if any(indicator in user_input.lower() for indicator in chronic_indicators):
            return True
        
        # Follow up on medication concerns
        medication_concerns = ["side effects", "副作用", "not working", "冇效", "forgot", "忘記"]
        if any(concern in user_input.lower() for concern in medication_concerns):
            return True
        
        # Follow up on persistent symptoms
        persistent_indicators = ["weeks", "星期", "months", "月", "getting worse", "惡化"]
        if any(indicator in user_input.lower() for indicator in persistent_indicators):
            return True
        
        return False
    
    def _extract_health_topics(self, user_input: str) -> List[str]:
        """Extract health topics mentioned in user input."""
        topics = []
        user_input_lower = user_input.lower()
        
        topic_mapping = {
            "pain": ["pain", "痛", "ache", "疼痛"],
            "diabetes": ["diabetes", "糖尿病", "blood sugar", "血糖"],
            "hypertension": ["blood pressure", "血壓", "hypertension", "高血壓"],
            "heart": ["heart", "心臟", "chest", "胸"],
            "respiratory": ["breathe", "呼吸", "cough", "咳嗽", "asthma", "哮喘"],
            "mental_health": ["tired", "攰", "stress", "壓力", "sleep", "睡眠"],
            "mobility": ["walking", "行路", "fall", "跌倒", "balance", "平衡"]
        }
        
        for topic, keywords in topic_mapping.items():
            if any(keyword in user_input_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_medication_mentions(self, user_input: str) -> List[str]:
        """Extract medication-related mentions."""
        medications = []
        user_input_lower = user_input.lower()
        
        # Common medication patterns
        med_patterns = [
            r"taking (\w+)",
            r"on (\w+)",
            r"食緊(.+?)(?:藥|medication)",
            r"服用(.+?)(?:藥|medication)"
        ]
        
        for pattern in med_patterns:
            matches = re.findall(pattern, user_input_lower)
            medications.extend(matches)
        
        return medications
    
    def _detect_chronic_conditions(self, user_input: str) -> List[str]:
        """Detect chronic conditions mentioned."""
        conditions = []
        user_input_lower = user_input.lower()
        
        for condition, keywords in self._chronic_conditions.items():
            if any(keyword in user_input_lower for keyword in keywords):
                conditions.append(condition)
        
        return conditions
    
    def should_alert_professional(
        self, 
        user_input: str, 
        context: AgentContext,
        response: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Determine if professional alert is needed for health concerns.
        
        Args:
            user_input: User's message
            context: Conversation context
            response: Generated response
            
        Returns:
            Tuple of (needs_alert: bool, alert_details: Optional[Dict])
        """
        # Check for concerning health patterns
        concerning_patterns = [
            "multiple medications", "多種藥物", "confused about medication", "搞唔清楚藥",
            "not eating", "冇食野", "significant weight loss", "體重大減",
            "frequent falls", "經常跌倒", "memory problems", "記憶問題",
            "can't manage daily activities", "做唔到日常活動"
        ]
        
        if any(pattern in user_input.lower() for pattern in concerning_patterns):
            return True, {
                "alert_type": "health_concern",
                "urgency": "medium",
                "reason": "Concerning health pattern detected",
                "category": "illness_monitoring",
                "user_input_summary": user_input[:200],
                "recommended_action": "Healthcare provider consultation recommended",
                "timestamp": datetime.now().isoformat(),
                "specific_concerns": [p for p in concerning_patterns if p in user_input.lower()]
            }
        
        # Check for medication non-compliance
        medication_issues = [
            "stopped taking", "停止服用", "forgot medication", "忘記食藥",
            "too many pills", "太多藥丸", "can't afford medication", "買唔起藥"
        ]
        
        if any(issue in user_input.lower() for issue in medication_issues):
            return True, {
                "alert_type": "medication_concern",
                "urgency": "medium",
                "reason": "Medication compliance issue",
                "category": "medication_management",
                "user_input_summary": user_input[:200],
                "recommended_action": "Pharmacist or healthcare provider consultation",
                "timestamp": datetime.now().isoformat()
            }
        
        return super().should_alert_professional(user_input, context, response)
    
    def get_activation_message(self, context: AgentContext) -> str:
        """Get activation message for illness monitor agent."""
        age_group = context.user_profile.get("age_group", "adult")
        
        if age_group == "elderly":
            if context.language_preference == "zh":
                return "🏥 您好！我係慧心助手，專門關心長者嘅健康狀況。讓我陪伴您，一起關注您的身體。"
            else:
                return "🏥 Hello! I'm your Wise Heart Assistant, specialized in health monitoring for seniors. Let me support your health journey."
        else:
            if context.language_preference == "zh":
                return "🏥 您好！我係慧心助手，專門監測健康狀況和管理疾病。有咩健康問題想傾計？"
            else:
                return "🏥 Hello! I'm your Wise Heart Assistant for illness monitoring and health management. What health concerns can I help you with?"
