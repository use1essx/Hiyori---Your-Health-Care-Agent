"""
Main AI service for Healthcare AI V2
Integrates OpenRouter client, model manager, and cost optimizer
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal

from src.ai.openrouter_client import OpenRouterClient, ModelResponse, get_openrouter_client
from src.ai.model_manager import (
    ModelManager, ModelSelectionCriteria, TaskComplexity, UrgencyLevel, get_model_manager
)
from src.ai.cost_optimizer import CostOptimizer, get_cost_optimizer
from src.ai.providers.aws_bedrock import BedrockClient, is_bedrock_available
from src.core.logging import get_logger
from src.core.exceptions import AgentError, ExternalAPIError
from src.config import settings


logger = get_logger(__name__)


@dataclass
class AIRequest:
    """Standardized AI request structure"""
    user_input: str
    system_prompt: str
    agent_type: str
    content_type: Optional[str] = None
    urgency_level: str = "medium"
    user_id: Optional[int] = None
    conversation_context: Optional[Dict] = None
    cost_constraints: Optional[Dict] = None
    performance_requirements: Optional[Dict] = None


@dataclass
class AIResponse:
    """Standardized AI response structure"""
    content: str
    model_used: str
    model_tier: str
    agent_type: str
    processing_time_ms: int
    cost: Decimal
    usage_stats: Dict[str, Any]
    success: bool = True
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "content": self.content,
            "model_used": self.model_used,
            "model_tier": self.model_tier,
            "agent_type": self.agent_type,
            "processing_time_ms": self.processing_time_ms,
            "cost": float(self.cost),
            "usage_stats": self.usage_stats,
            "success": self.success,
            "error_message": self.error_message,
            "confidence_score": self.confidence_score
        }


class HealthcareAIService:
    """
    Main AI service that orchestrates all AI operations for Healthcare AI V2
    Provides unified interface for agent interactions with intelligent model selection and cost optimization
    """
    
    def __init__(self):
        self.openrouter_client: Optional[OpenRouterClient] = None
        self.model_manager: Optional[ModelManager] = None
        self.cost_optimizer: Optional[CostOptimizer] = None
        self.bedrock_client: Optional[BedrockClient] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize all AI service components"""
        if self._initialized:
            return
            
        try:
            # Initialize core components
            self.openrouter_client = await get_openrouter_client()
            self.model_manager = get_model_manager()
            self.cost_optimizer = get_cost_optimizer()
            
            # Initialize Bedrock if available (future)
            if is_bedrock_available():
                self.bedrock_client = BedrockClient(settings.aws_bedrock_region)
                logger.info("AWS Bedrock client initialized")
            
            self._initialized = True
            logger.info("Healthcare AI Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Healthcare AI Service: {e}")
            raise
            
    async def process_request(self, request: AIRequest) -> AIResponse:
        """
        Process AI request with intelligent model selection and cost optimization
        
        Args:
            request: AIRequest object containing user input and configuration
            
        Returns:
            AIResponse object with generated content and metadata
        """
        if not self._initialized:
            await self.initialize()
            
        start_time = datetime.utcnow()
        
        try:
            # Analyze task complexity and urgency
            task_complexity = self.model_manager.analyze_task_complexity(
                user_input=request.user_input,
                agent_type=request.agent_type,
                conversation_context=request.conversation_context
            )
            
            urgency_level = self._parse_urgency_level(request.urgency_level)
            
            # Create model selection criteria
            criteria = ModelSelectionCriteria(
                agent_type=request.agent_type,
                content_type=request.content_type or "general",
                urgency_level=urgency_level,
                task_complexity=task_complexity,
                user_id=request.user_id,
                conversation_context=request.conversation_context,
                cost_constraints=request.cost_constraints,
                performance_requirements=request.performance_requirements
            )
            
            # Make request with fallback handling
            model_response = await self.model_manager.make_request_with_fallback(
                criteria=criteria,
                system_prompt=request.system_prompt,
                user_prompt=request.user_input
            )
            
            # Record usage for cost optimization
            self.cost_optimizer.record_usage(
                model_tier=self.model_manager.select_optimal_model(criteria),
                model_name=model_response.model,
                agent_type=request.agent_type,
                content_type=criteria.content_type,
                urgency_level=request.urgency_level,
                prompt_tokens=model_response.usage.get("prompt_tokens", 0),
                completion_tokens=model_response.usage.get("completion_tokens", 0),
                cost=model_response.cost,
                processing_time_ms=model_response.processing_time_ms,
                success=model_response.success,
                user_id=request.user_id,
                error_message=model_response.error_message
            )
            
            # Calculate total processing time
            total_processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Calculate confidence score based on model performance
            confidence_score = self._calculate_confidence_score(
                model_response, task_complexity, urgency_level
            )
            
            response = AIResponse(
                content=model_response.content,
                model_used=model_response.model,
                model_tier=self.model_manager.select_optimal_model(criteria),
                agent_type=request.agent_type,
                processing_time_ms=total_processing_time,
                cost=model_response.cost,
                usage_stats=model_response.usage,
                success=model_response.success,
                error_message=model_response.error_message,
                confidence_score=confidence_score
            )
            
            logger.info(
                f"AI request processed successfully",
                extra={
                    "agent_type": request.agent_type,
                    "model_used": response.model_used,
                    "cost": float(response.cost),
                    "processing_time_ms": response.processing_time_ms,
                    "user_id": request.user_id,
                    "task_complexity": task_complexity.value,
                    "urgency_level": urgency_level.value
                }
            )
            
            return response
            
        except Exception as e:
            total_processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            logger.error(
                f"AI request failed: {e}",
                extra={
                    "agent_type": request.agent_type,
                    "user_id": request.user_id,
                    "error": str(e)
                }
            )
            
            return AIResponse(
                content="",
                model_used="unknown",
                model_tier="unknown",
                agent_type=request.agent_type,
                processing_time_ms=total_processing_time,
                cost=Decimal('0.0'),
                usage_stats={},
                success=False,
                error_message=str(e)
            )
            
    def _parse_urgency_level(self, urgency_input) -> UrgencyLevel:
        """Parse urgency level string or enum to enum"""
        # If already a UrgencyLevel enum, return as-is
        if isinstance(urgency_input, UrgencyLevel):
            return urgency_input
        
        # If it's a string, convert to lowercase and map
        if isinstance(urgency_input, str):
            urgency_mapping = {
                "low": UrgencyLevel.LOW,
                "medium": UrgencyLevel.MEDIUM,
                "high": UrgencyLevel.HIGH,
                "emergency": UrgencyLevel.EMERGENCY,
                "critical": UrgencyLevel.CRITICAL
            }
            return urgency_mapping.get(urgency_input.lower(), UrgencyLevel.MEDIUM)
        
        # Default fallback
        return UrgencyLevel.MEDIUM
        
    def _calculate_confidence_score(
        self, 
        model_response: ModelResponse, 
        task_complexity: TaskComplexity,
        urgency_level: UrgencyLevel
    ) -> float:
        """Calculate confidence score based on various factors"""
        base_confidence = 0.8  # Base confidence for successful responses
        
        if not model_response.success:
            return 0.0
            
        # Adjust based on task complexity
        complexity_adjustments = {
            TaskComplexity.SIMPLE: 0.1,
            TaskComplexity.MODERATE: 0.0,
            TaskComplexity.COMPLEX: -0.1,
            TaskComplexity.CRITICAL: -0.2
        }
        
        # Adjust based on urgency level
        urgency_adjustments = {
            UrgencyLevel.LOW: 0.0,
            UrgencyLevel.MEDIUM: 0.0,
            UrgencyLevel.HIGH: -0.05,
            UrgencyLevel.EMERGENCY: -0.1
        }
        
        # Adjust based on response length (very short responses might be incomplete)
        response_length_penalty = 0.0
        if len(model_response.content) < 50:
            response_length_penalty = -0.2
        elif len(model_response.content) < 100:
            response_length_penalty = -0.1
            
        final_confidence = (
            base_confidence +
            complexity_adjustments.get(task_complexity, 0.0) +
            urgency_adjustments.get(urgency_level, 0.0) +
            response_length_penalty
        )
        
        return max(0.0, min(1.0, final_confidence))  # Clamp between 0 and 1
        
    async def get_usage_analytics(
        self, 
        user_id: Optional[int] = None,
        agent_type: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get comprehensive usage analytics"""
        if not self._initialized:
            await self.initialize()
            
        # Get cost summary
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        cost_summary = self.cost_optimizer.get_cost_summary(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            agent_type=agent_type
        )
        
        # Get performance metrics
        performance_report = self.model_manager.get_performance_report()
        
        # Get optimization recommendations
        recommendations = self.cost_optimizer.get_optimization_recommendations()
        
        # Get model efficiency report
        efficiency_report = self.cost_optimizer.get_model_efficiency_report()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "cost_summary": cost_summary.to_dict(),
            "performance_metrics": performance_report,
            "optimization_recommendations": recommendations,
            "model_efficiency": efficiency_report,
            "active_alerts": self.cost_optimizer.get_active_alerts()
        }
        
    async def set_budget_limit(
        self,
        amount: float,
        period: str = "daily",
        user_id: Optional[int] = None,
        agent_type: Optional[str] = None
    ) -> str:
        """Set budget limit for cost control"""
        if not self._initialized:
            await self.initialize()
            
        from src.ai.cost_optimizer import BudgetPeriod
        
        period_mapping = {
            "daily": BudgetPeriod.DAILY,
            "weekly": BudgetPeriod.WEEKLY,
            "monthly": BudgetPeriod.MONTHLY,
            "yearly": BudgetPeriod.YEARLY
        }
        
        budget_period = period_mapping.get(period.lower(), BudgetPeriod.DAILY)
        
        budget_id = self.cost_optimizer.set_budget_limit(
            amount=Decimal(str(amount)),
            period=budget_period,
            user_id=user_id,
            agent_type=agent_type
        )
        
        logger.info(
            f"Budget limit set: ${amount} per {period}",
            extra={
                "budget_id": budget_id,
                "amount": amount,
                "period": period,
                "user_id": user_id,
                "agent_type": agent_type
            }
        )
        
        return budget_id
        
    async def update_user_satisfaction(
        self, 
        model_tier: str, 
        satisfaction_score: float
    ):
        """Update user satisfaction score for model performance tracking"""
        if not self._initialized:
            await self.initialize()
            
        self.model_manager.update_user_satisfaction(model_tier, satisfaction_score)
        
        logger.info(
            f"User satisfaction updated for {model_tier}: {satisfaction_score}",
            extra={
                "model_tier": model_tier,
                "satisfaction_score": satisfaction_score
            }
        )
        
    async def get_model_recommendations(
        self, 
        agent_type: str,
        urgency_level: str = "medium"
    ) -> Dict[str, Any]:
        """Get model recommendations for specific agent and urgency"""
        if not self._initialized:
            await self.initialize()
            
        # Create criteria for recommendation
        criteria = ModelSelectionCriteria(
            agent_type=agent_type,
            content_type="general",
            urgency_level=self._parse_urgency_level(urgency_level),
            task_complexity=TaskComplexity.MODERATE
        )
        
        # Get optimal model
        recommended_model = self.model_manager.select_optimal_model(criteria)
        
        # Get model specifications
        model_specs = self.openrouter_client.get_model_specs()
        
        return {
            "recommended_model": recommended_model,
            "model_specs": model_specs.get(recommended_model, {}),
            "alternative_models": [
                tier for tier in model_specs.keys() 
                if tier != recommended_model
            ],
            "selection_criteria": {
                "agent_type": agent_type,
                "urgency_level": urgency_level,
                "task_complexity": "moderate"
            }
        }
        
    async def cleanup(self):
        """Cleanup AI service resources"""
        if self.openrouter_client:
            await self.openrouter_client.close()
            
        logger.info("Healthcare AI Service cleaned up")


# Global AI service instance
_ai_service: Optional[HealthcareAIService] = None


async def get_ai_service() -> HealthcareAIService:
    """Get or create the global AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = HealthcareAIService()
        await _ai_service.initialize()
    return _ai_service


async def cleanup_ai_service():
    """Cleanup the global AI service"""
    global _ai_service
    if _ai_service:
        await _ai_service.cleanup()
        _ai_service = None
