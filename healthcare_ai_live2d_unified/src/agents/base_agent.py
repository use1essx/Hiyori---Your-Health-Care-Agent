"""
Base Agent Class for Healthcare AI V2
=====================================

Abstract base class that defines the interface and core functionality
for all healthcare AI agents in the system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
from datetime import datetime

from ..ai.ai_service import HealthcareAIService, AIRequest, AIResponse
from ..ai.model_manager import UrgencyLevel, TaskComplexity


class AgentCapability(Enum):
    """Agent capabilities for routing and selection."""
    ILLNESS_MONITORING = "illness_monitoring"
    MENTAL_HEALTH_SUPPORT = "mental_health_support"
    EMERGENCY_RESPONSE = "emergency_response"
    WELLNESS_COACHING = "wellness_coaching"
    MEDICATION_GUIDANCE = "medication_guidance"
    CHRONIC_DISEASE_MANAGEMENT = "chronic_disease_management"
    CRISIS_INTERVENTION = "crisis_intervention"
    EDUCATIONAL_SUPPORT = "educational_support"


class AgentPersonality(Enum):
    """Agent personality types for cultural and age adaptation."""
    CARING_ELDER_COMPANION = "caring_elder_companion"  # 慧心助手
    VTUBER_FRIEND = "vtuber_friend"  # 小星星
    PROFESSIONAL_RESPONDER = "professional_responder"  # Safety Guardian
    WELLNESS_MOTIVATOR = "wellness_motivator"  # Wellness Coach


@dataclass
class AgentResponse:
    """Structured response from an agent."""
    content: str
    confidence: float  # 0.0 - 1.0
    urgency_level: UrgencyLevel
    requires_followup: bool
    suggested_actions: List[str]
    professional_alert_needed: bool
    alert_details: Optional[Dict[str, Any]] = None
    conversation_context: Optional[Dict[str, Any]] = None


@dataclass
class AgentContext:
    """Context information for agent processing."""
    user_id: str
    session_id: str
    conversation_history: List[Dict[str, Any]]
    user_profile: Dict[str, Any]
    cultural_context: Dict[str, Any]
    language_preference: str  # "en", "zh", "auto"
    timestamp: datetime


class BaseAgent(ABC):
    """
    Abstract base class for all healthcare AI agents.
    
    Provides standard interface and core functionality for:
    - Agent capability assessment
    - Response generation with confidence scoring
    - Context management
    - Emergency detection
    - Professional alert generation
    """
    
    def __init__(
        self,
        agent_id: str,
        ai_service: HealthcareAIService,
        capabilities: List[AgentCapability],
        personality: AgentPersonality,
        primary_language: str = "zh",
    ):
        """
        Initialize base agent.
        
        Args:
            agent_id: Unique identifier for this agent
            ai_service: AI service for model interactions
            capabilities: List of agent capabilities
            personality: Agent personality type
            primary_language: Primary language for responses
        """
        self.agent_id = agent_id
        self.ai_service = ai_service
        self.capabilities = capabilities
        self.personality = personality
        self.primary_language = primary_language
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # Agent-specific configuration
        self._confidence_threshold = 0.7
        self._emergency_keywords = []
        self._cultural_adaptations = {}
        
    @abstractmethod
    def can_handle(self, user_input: str, context: AgentContext) -> Tuple[bool, float]:
        """
        Determine if this agent can handle the user input.
        
        Args:
            user_input: User's message/question
            context: Conversation context
            
        Returns:
            Tuple of (can_handle: bool, confidence: float)
        """
        pass
    
    @abstractmethod
    async def generate_response(
        self, 
        user_input: str, 
        context: AgentContext
    ) -> AgentResponse:
        """
        Generate a response to user input.
        
        Args:
            user_input: User's message/question
            context: Conversation context
            
        Returns:
            AgentResponse with content and metadata
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self, context: AgentContext) -> str:
        """
        Get the system prompt for this agent.
        
        Args:
            context: Conversation context for personalization
            
        Returns:
            System prompt string
        """
        pass
    
    # Core functionality methods
    
    def detect_urgency(self, user_input: str, context: AgentContext) -> UrgencyLevel:
        """
        Detect urgency level of user input.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Detected urgency level
        """
        user_input_lower = user_input.lower()
        
        # Emergency keywords
        emergency_keywords = [
            "emergency", "緊急", "urgent", "急", "help", "救命",
            "chest pain", "胸痛", "can't breathe", "唔可以呼吸",
            "suicide", "自殺", "kill myself", "hurt myself", "傷害自己",
            "overdose", "服藥過量", "unconscious", "失去知覺"
        ]
        
        if any(keyword in user_input_lower for keyword in emergency_keywords):
            return UrgencyLevel.CRITICAL
        
        # High urgency indicators
        high_urgency_keywords = [
            "severe", "嚴重", "intense", "劇烈", "very worried", "好擔心",
            "getting worse", "惡化", "can't sleep", "瞓唔到",
            "haven't eaten", "冇食野", "can't function", "做唔到野"
        ]
        
        if any(keyword in user_input_lower for keyword in high_urgency_keywords):
            return UrgencyLevel.HIGH
        
        # Medium urgency indicators
        medium_urgency_keywords = [
            "concerned", "關心", "worried", "擔心", "uncomfortable", "唔舒服",
            "pain", "痛", "tired", "攰", "stressed", "壓力"
        ]
        
        if any(keyword in user_input_lower for keyword in medium_urgency_keywords):
            return UrgencyLevel.MEDIUM
        
        return UrgencyLevel.LOW
    
    def detect_complexity(self, user_input: str, context: AgentContext) -> TaskComplexity:
        """
        Detect task complexity based on user input and context.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Detected task complexity
        """
        # Multiple symptoms or conditions
        if len(user_input.split()) > 50:
            return TaskComplexity.COMPLEX
        
        # Multiple questions or concerns
        question_count = user_input.count("?") + user_input.count("？")
        if question_count > 2:
            return TaskComplexity.COMPLEX
        
        # Complex medical terminology
        medical_terms = [
            "diagnosis", "診斷", "medication", "藥物", "treatment", "治療",
            "chronic", "慢性", "syndrome", "症候群", "disorder", "失調"
        ]
        
        if sum(1 for term in medical_terms if term in user_input.lower()) > 2:
            return TaskComplexity.MODERATE
        
        return TaskComplexity.SIMPLE
    
    def should_alert_professional(
        self, 
        user_input: str, 
        context: AgentContext,
        response: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Determine if professional alert is needed.
        
        Args:
            user_input: User's message
            context: Conversation context
            response: Generated response
            
        Returns:
            Tuple of (needs_alert: bool, alert_details: Optional[Dict])
        """
        urgency = self.detect_urgency(user_input, context)
        
        if urgency == UrgencyLevel.CRITICAL:
            return True, {
                "alert_type": "emergency",
                "urgency": "critical",
                "reason": "Emergency keywords detected",
                "user_input_summary": user_input[:200],
                "recommended_action": "Immediate professional intervention",
                "timestamp": datetime.now().isoformat()
            }
        
        # Agent-specific alert conditions (to be overridden by subclasses)
        return False, None
    
    def adapt_to_culture(self, response: str, context: AgentContext) -> str:
        """
        Adapt response to cultural context.
        
        Args:
            response: Generated response
            context: Conversation context
            
        Returns:
            Culturally adapted response
        """
        cultural_context = context.cultural_context
        
        # Hong Kong specific adaptations
        if cultural_context.get("region") == "hong_kong":
            # Add appropriate honorifics for elderly
            if context.user_profile.get("age_group") == "elderly":
                # Use more respectful language
                response = response.replace("你", "您")
            
            # Add local emergency information
            if "emergency" in response.lower():
                response += "\n\n🚨 香港緊急電話：999"
        
        return response
    
    def _build_ai_request(
        self, 
        user_input: str, 
        context: AgentContext,
        system_prompt: str
    ) -> AIRequest:
        """
        Build AI request with agent-specific configuration.
        
        Args:
            user_input: User's message
            context: Conversation context
            system_prompt: System prompt for the agent
            
        Returns:
            Configured AI request
        """
        urgency = self.detect_urgency(user_input, context)
        complexity = self.detect_complexity(user_input, context)
        
        # Ensure no sensitive data (like API keys) gets logged in context
        safe_context = {
            "history": context.conversation_history[-5:],  # Last 5 exchanges
            "user_profile": {k: v for k, v in context.user_profile.items() if not k.lower().endswith('_key')},
            "cultural_context": context.cultural_context
        }
        
        return AIRequest(
            user_input=user_input,
            system_prompt=system_prompt,
            agent_type=self.agent_id,
            conversation_context=safe_context,
            urgency_level=urgency.value if hasattr(urgency, 'value') else str(urgency)
        )
    
    async def _generate_ai_response(
        self, 
        ai_request: AIRequest
    ) -> AIResponse:
        """
        Generate AI response using the AI service.
        
        Args:
            ai_request: Configured AI request
            
        Returns:
            AI response
        """
        try:
            return await self.ai_service.process_request(ai_request)
        except Exception as e:
            self.logger.error(f"AI service error: {e}")
            # Return fallback response
            return AIResponse(
                content="I'm experiencing technical difficulties. Please try again or contact support if this persists.",
                model_used="fallback",
                tokens_used=0,
                confidence_score=0.5,
                processing_time=0.0,
                cost=0.0
            )
    
    def get_activation_message(self, context: AgentContext) -> str:
        """
        Get agent activation message.
        
        Args:
            context: Conversation context
            
        Returns:
            Activation message for this agent
        """
        # Default activation message (to be overridden by subclasses)
        return f"🤖 {self.agent_id} activated to assist you."
