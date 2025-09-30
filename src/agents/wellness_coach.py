"""
Wellness Coach Agent - Healthcare AI V2
======================================

Preventive health coaching agent focused on wellness education and health promotion
for all ages with cultural adaptation for Hong Kong context.

Key Features:
- Preventive health education and coaching
- Age-appropriate wellness guidance
- Cultural adaptation for Hong Kong lifestyle
- Health habit formation and maintenance
- Motivational support for healthy behaviors
- Integration with other agents for comprehensive care
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


class WellnessCoachAgent(BaseAgent):
    """
    Wellness Coach - Preventive Health Specialist
    
    Preventive health coaching agent providing:
    - Health education and wellness promotion
    - Healthy habit formation guidance
    - Age-appropriate prevention strategies
    - Cultural adaptation for Hong Kong lifestyle
    """
    
    def __init__(self, ai_service):
        """Initialize Wellness Coach Agent."""
        super().__init__(
            agent_id="wellness_coach",
            ai_service=ai_service,
            capabilities=[
                AgentCapability.WELLNESS_COACHING,
                AgentCapability.EDUCATIONAL_SUPPORT
            ],
            personality=AgentPersonality.WELLNESS_MOTIVATOR,
            primary_language="zh"
        )
        
        # Wellness and prevention keywords
        self._wellness_keywords = [
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
        self._age_specific_wellness = {
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
        self._hk_wellness_context = {
            "environmental": ["air_quality", "空氣質素", "pollution", "污染", "heat", "炎熱"],
            "lifestyle": ["work_stress", "工作壓力", "commute", "通勤", "small_space", "小空間"],
            "cultural": ["traditional_medicine", "中醫", "herbal", "草藥", "tai_chi", "太極"],
            "dietary": ["dim_sum", "點心", "congee", "粥", "tea", "茶", "hot_pot", "火鍋"]
        }
    
    def can_handle(self, user_input: str, context: AgentContext) -> Tuple[bool, float]:
        """
        Determine if this agent can handle wellness coaching requests.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Tuple of (can_handle: bool, confidence: float)
        """
        user_input_lower = user_input.lower()
        
        # Check for wellness keywords
        wellness_matches = sum(1 for keyword in self._wellness_keywords 
                             if keyword in user_input_lower)
        
        # Check for age-specific wellness concerns
        age_group = context.user_profile.get("age_group", "adult")
        age_specific = self._age_specific_wellness.get(age_group, {})
        age_keywords = age_specific.get("keywords", [])
        age_matches = sum(1 for keyword in age_keywords if keyword in user_input_lower)
        
        # Check for Hong Kong specific wellness contexts
        hk_matches = 0
        for category, keywords in self._hk_wellness_context.items():
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
    
    async def generate_response(
        self, 
        user_input: str, 
        context: AgentContext
    ) -> AgentResponse:
        """
        Generate wellness coaching response.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            AgentResponse with wellness guidance
        """
        # Build system prompt
        system_prompt = self.get_system_prompt(context)
        
        # Create AI request
        ai_request = self._build_ai_request(user_input, context, system_prompt)
        
        # Generate response using AI service
        ai_response = await self._generate_ai_response(ai_request)
        
        # Post-process response
        processed_content = self._post_process_response(ai_response.content, context)
        
        # Detect urgency (usually low for wellness coaching)
        urgency = self.detect_urgency(user_input, context)
        
        # Generate suggested actions
        suggested_actions = self._generate_suggested_actions(user_input, context)
        
        # Usually no professional alerts needed for wellness coaching
        needs_alert, alert_details = self.should_alert_professional(
            user_input, context, processed_content
        )
        
        return AgentResponse(
            content=processed_content,
            confidence=ai_response.confidence_score,
            urgency_level=urgency,
            requires_followup=self._requires_followup(user_input, context),
            suggested_actions=suggested_actions,
            professional_alert_needed=needs_alert,
            alert_details=alert_details,
            conversation_context={
                "agent_type": "wellness_coach",
                "wellness_topics": self._extract_wellness_topics(user_input),
                "health_goals": self._extract_health_goals(user_input),
                "age_specific_focus": self._get_age_specific_focus(context),
                "cultural_adaptations": self._identify_cultural_needs(user_input, context)
            }
        )
    
    def get_system_prompt(self, context: AgentContext) -> str:
        """
        Get the system prompt for wellness coaching.
        
        Args:
            context: Conversation context
            
        Returns:
            Customized system prompt
        """
        # Load the proper English healthcare prompt
        try:
            import os
            prompt_file = os.path.join(os.path.dirname(__file__), '../../prompts/agents/wellness_coach/en.txt')
            with open(prompt_file, 'r', encoding='utf-8') as f:
                base_prompt = f.read()
        except Exception as e:
            # Fallback to proper healthcare prompt if file loading fails
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
        age_group = context.user_profile.get("age_group", "adult")
        if age_group == "child":
            base_prompt += """

## Child Health Focus:
- Growth and development support with age-appropriate nutrition
- Building foundation for lifelong healthy habits
- Importance of physical activity and active play
- Parent involvement and creating healthy family environments"""
        
        elif age_group == "teen":
            base_prompt += """

## Teen Health Focus:
- Academic stress management and mental wellness
- Adapting to physical changes and health education
- Healthy social relationships and peer influence navigation
- Building independent health decision-making skills"""
        
        elif age_group == "elderly":
            base_prompt += """

## Elderly Health Focus:
- Active aging and maintaining functional independence
- Chronic disease prevention and management
- Fall prevention and safe living strategies
- Social connection and mental health maintenance"""
        
        # Add language preference instruction
        language = getattr(context, 'language_preference', 'en')
        if language == "zh":
            base_prompt += "\n\n**Important: Respond in Traditional Chinese, providing practical health guidance.**"
        else:
            base_prompt += "\n\n**Important: Respond in English, providing clear health guidance and practical wellness advice.**"
        
        return base_prompt
    
    def _post_process_response(self, content: str, context: AgentContext) -> str:
        """
        Post-process the AI response for wellness coaching.
        
        Args:
            content: Raw AI response
            context: Conversation context
            
        Returns:
            Enhanced wellness coaching response
        """
        # Add cultural adaptation
        content = self.adapt_to_culture(content, context)
        
        # Add motivational elements if not present
        if not any(emoji in content for emoji in ["💪", "🌟", "✨", "🎯"]):
            content = "💪 " + content
        
        # Add disclaimer for health advice
        if any(term in content.lower() for term in ["exercise", "運動", "diet", "飲食", "supplement", "補充劑"]):
            if context.language_preference == "zh":
                content += "\n\n⚠️ **健康提醒**：開始新的運動或飲食計劃前，建議諮詢醫生或註冊營養師。"
            else:
                content += "\n\n⚠️ **Health Note**: Consult a doctor or registered dietitian before starting new exercise or diet programs."
        
        return content
    
    def _generate_suggested_actions(
        self, 
        user_input: str, 
        context: AgentContext
    ) -> List[str]:
        """
        Generate wellness-specific suggested actions.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            List of suggested wellness actions
        """
        actions = []
        user_input_lower = user_input.lower()
        age_group = context.user_profile.get("age_group", "adult")
        
        # Exercise and fitness actions
        if any(word in user_input_lower for word in ["exercise", "運動", "fitness", "健身", "active", "活躍"]):
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
        if any(word in user_input_lower for word in ["diet", "飲食", "nutrition", "營養", "eating", "食"]):
            actions.extend([
                "Focus on whole foods and balanced meals",
                "Stay hydrated throughout the day",
                "Consider keeping a food diary"
            ])
        
        # Sleep and rest actions
        if any(word in user_input_lower for word in ["sleep", "睡眠", "tired", "攰", "rest", "休息"]):
            actions.extend([
                "Establish consistent sleep schedule",
                "Create relaxing bedtime routine",
                "Limit screen time before bed"
            ])
        
        # Stress management actions
        if any(word in user_input_lower for word in ["stress", "壓力", "busy", "忙", "overwhelmed", "不知所措"]):
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
    
    def _requires_followup(self, user_input: str, context: AgentContext) -> bool:
        """
        Determine if follow-up is beneficial for wellness coaching.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            True if follow-up would be helpful
        """
        # Follow up on goal setting
        goal_indicators = ["goal", "目標", "plan", "計劃", "want to", "想", "start", "開始"]
        if any(indicator in user_input.lower() for indicator in goal_indicators):
            return True
        
        # Follow up on behavior change
        change_indicators = ["change", "改變", "improve", "改善", "better", "更好", "habit", "習慣"]
        if any(indicator in user_input.lower() for indicator in change_indicators):
            return True
        
        # Generally beneficial for wellness coaching to maintain engagement
        return True
    
    def _extract_wellness_topics(self, user_input: str) -> List[str]:
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
    
    def _extract_health_goals(self, user_input: str) -> List[str]:
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
    
    def _get_age_specific_focus(self, context: AgentContext) -> List[str]:
        """Get age-specific wellness focus areas."""
        age_group = context.user_profile.get("age_group", "adult")
        age_specific = self._age_specific_wellness.get(age_group, {})
        return age_specific.get("priorities", [])
    
    def _identify_cultural_needs(self, user_input: str, context: AgentContext) -> List[str]:
        """Identify cultural adaptation needs."""
        adaptations = []
        user_input_lower = user_input.lower()
        cultural_context = context.cultural_context
        
        # Hong Kong specific needs
        if cultural_context.get("region") == "hong_kong":
            if "work" in user_input_lower or "工作" in user_input_lower:
                adaptations.append("work_life_balance_hk")
            
            if "space" in user_input_lower or "空間" in user_input_lower:
                adaptations.append("small_space_living")
            
            if "traditional" in user_input_lower or "中醫" in user_input_lower:
                adaptations.append("tcm_integration")
        
        return adaptations
    
    def should_alert_professional(
        self, 
        user_input: str, 
        context: AgentContext,
        response: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Wellness coaching rarely needs professional alerts unless concerning patterns.
        
        Args:
            user_input: User's message
            context: Conversation context
            response: Generated response
            
        Returns:
            Tuple of (needs_alert: bool, alert_details: Optional[Dict])
        """
        # Check for concerning wellness patterns that might need professional input
        concerning_patterns = [
            "extreme diet", "極端飲食", "not eating for days", "幾日冇食野",
            "excessive exercise", "過度運動", "exercise addiction", "運動成癮",
            "supplements only", "只食補充劑", "avoid all medications", "避免所有藥物"
        ]
        
        if any(pattern in user_input.lower() for pattern in concerning_patterns):
            return True, {
                "alert_type": "wellness_concern",
                "urgency": "low",
                "reason": "Concerning wellness pattern requiring professional guidance",
                "category": "preventive_health",
                "user_input_summary": user_input[:200],
                "recommended_action": "Professional wellness or medical consultation recommended",
                "timestamp": datetime.now().isoformat()
            }
        
        return False, None
    
    def detect_urgency(self, user_input: str, context: AgentContext) -> UrgencyLevel:
        """Wellness coaching typically has low urgency unless specific concerns."""
        # Override to check for any urgent wellness concerns
        urgent_wellness = [
            "can't sleep for weeks", "幾個星期瞓唔到",
            "not eating anything", "咩都唔食",
            "extreme pain when exercising", "運動時劇痛"
        ]
        
        if any(concern in user_input.lower() for concern in urgent_wellness):
            return UrgencyLevel.MEDIUM
        
        return UrgencyLevel.LOW
    
    def get_activation_message(self, context: AgentContext) -> str:
        """Get activation message for wellness coach."""
        age_group = context.user_profile.get("age_group", "adult")
        
        if context.language_preference == "zh":
            if age_group == "elderly":
                return "💪 您好！我係健康教練，專門幫助長者建立健康生活習慣和積極老化。讓我們一起追求更好的健康！"
            else:
                return "💪 您好！我係健康教練，專門提供預防性健康指導和生活方式建議。準備好建立更健康的生活嗎？"
        else:
            if age_group == "elderly":
                return "💪 Hello! I'm your Wellness Coach, specializing in healthy aging and lifestyle guidance for seniors. Let's work together for better health!"
            else:
                return "💪 Hello! I'm your Wellness Coach for preventive health guidance and lifestyle improvement. Ready to build healthier habits?"
