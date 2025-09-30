"""
Smart model selection and management for Healthcare AI V2
Based on _enhanced_model_selection() patterns from healthcare_ai_system
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

from src.ai.openrouter_client import OpenRouterClient, ModelResponse, get_openrouter_client
from src.core.exceptions import ValidationError, AgentError
from src.core.logging import get_logger
from src.config import settings


logger = get_logger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for model selection"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"


class UrgencyLevel(Enum):
    """Urgency levels for model selection"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ModelPerformanceMetrics:
    """Track performance metrics for each model"""
    total_requests: int = 0
    successful_requests: int = 0
    average_response_time_ms: float = 0.0
    average_cost: Decimal = Decimal('0.0')
    user_satisfaction_score: float = 0.0
    error_rate: float = 0.0
    last_used: Optional[datetime] = None
    
    def update_metrics(
        self, 
        success: bool, 
        response_time_ms: int, 
        cost: Decimal,
        satisfaction_score: Optional[float] = None
    ):
        """Update performance metrics with new data"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            
        # Update average response time
        if self.total_requests == 1:
            self.average_response_time_ms = float(response_time_ms)
        else:
            self.average_response_time_ms = (
                (self.average_response_time_ms * (self.total_requests - 1) + response_time_ms) 
                / self.total_requests
            )
            
        # Update average cost
        if self.total_requests == 1:
            self.average_cost = cost
        else:
            self.average_cost = (
                (self.average_cost * (self.total_requests - 1) + cost) 
                / self.total_requests
            )
            
        # Update satisfaction score if provided
        if satisfaction_score is not None:
            if self.user_satisfaction_score == 0.0:
                self.user_satisfaction_score = satisfaction_score
            else:
                self.user_satisfaction_score = (
                    (self.user_satisfaction_score * 0.8) + (satisfaction_score * 0.2)
                )
                
        # Calculate error rate
        self.error_rate = 1.0 - (self.successful_requests / self.total_requests)
        self.last_used = datetime.utcnow()


@dataclass
class ModelSelectionCriteria:
    """Criteria for model selection"""
    agent_type: str
    content_type: str
    urgency_level: UrgencyLevel
    task_complexity: TaskComplexity
    user_id: Optional[int] = None
    conversation_context: Optional[Dict] = None
    cost_constraints: Optional[Dict] = None
    performance_requirements: Optional[Dict] = None


class ModelManager:
    """
    Smart model selection and management system
    Based on _enhanced_model_selection() logic from healthcare_ai_system
    """
    
    def __init__(self):
        self.client: Optional[OpenRouterClient] = None
        self.performance_metrics: Dict[str, ModelPerformanceMetrics] = {}
        self.usage_rotation: Dict[str, datetime] = {}
        self.fallback_chain: Dict[str, List[str]] = {}
        self._initialize_performance_tracking()
        self._setup_fallback_chains()
        
    def _initialize_performance_tracking(self):
        """Initialize performance tracking for all models"""
        # Get model tiers from OpenRouter client
        model_tiers = ["free", "lite", "premium"]
        for tier in model_tiers:
            self.performance_metrics[tier] = ModelPerformanceMetrics()
            
    def _setup_fallback_chains(self):
        """Setup fallback chains for different scenarios"""
        self.fallback_chain = {
            "emergency": ["premium", "lite", "free"],
            "critical": ["premium", "lite", "free"],
            "standard": ["lite", "premium", "free"],
            "cost_optimized": ["free", "lite", "premium"],
            "quality_optimized": ["premium", "lite", "free"]
        }
        
    async def get_client(self) -> OpenRouterClient:
        """Get or initialize OpenRouter client"""
        if self.client is None:
            self.client = await get_openrouter_client()
        return self.client
        
    def analyze_task_complexity(
        self, 
        user_input: str, 
        agent_type: str,
        conversation_context: Optional[Dict] = None
    ) -> TaskComplexity:
        """
        Analyze task complexity based on input content and context
        Based on complexity analysis patterns from healthcare_ai_system
        """
        lower_input = user_input.lower().strip()
        input_length = len(user_input)
        
        # Emergency scenarios are always critical
        emergency_keywords = [
            "emergency", "緊急", "urgent", "急", "help", "救命", "911", "999",
            "heart attack", "心臟病", "stroke", "中風", "unconscious", "暈倒"
        ]
        
        if any(keyword in lower_input for keyword in emergency_keywords):
            return TaskComplexity.CRITICAL
            
        # Complex medical scenarios
        complex_medical_keywords = [
            "diagnosis", "診斷", "treatment plan", "治療計劃", "medication interaction", "藥物相互作用",
            "chronic condition", "慢性病", "multiple symptoms", "多種症狀", "specialist", "專科醫生"
        ]
        
        if any(keyword in lower_input for keyword in complex_medical_keywords):
            return TaskComplexity.COMPLEX
            
        # Agent-specific complexity analysis
        if agent_type == "illness_monitor":
            illness_complexity_indicators = [
                "several", "multiple", "different", "various", "combined", "together",
                "幾個", "多個", "不同", "各種", "一齊", "同時"
            ]
            if any(indicator in lower_input for indicator in illness_complexity_indicators):
                return TaskComplexity.COMPLEX
                
        elif agent_type == "mental_health":
            mental_health_complexity = [
                "depression", "anxiety", "panic", "trauma", "suicidal", "self-harm",
                "抑鬱", "焦慮", "恐慌", "創傷", "自殺", "自我傷害"
            ]
            if any(keyword in lower_input for keyword in mental_health_complexity):
                return TaskComplexity.COMPLEX
                
        # Length-based complexity
        if input_length > 500:  # Long, detailed queries
            return TaskComplexity.COMPLEX
        elif input_length > 200:  # Medium queries
            return TaskComplexity.MODERATE
        else:  # Short queries
            return TaskComplexity.SIMPLE
            
    def determine_urgency_level(
        self, 
        user_input: str, 
        agent_type: str,
        conversation_context: Optional[Dict] = None
    ) -> UrgencyLevel:
        """
        Determine urgency level based on content and context
        Based on urgency detection from healthcare_ai_system
        """
        lower_input = user_input.lower().strip()
        
        # Emergency keywords (highest priority)
        emergency_keywords = [
            "emergency", "緊急", "urgent", "急", "help", "救命", "call ambulance", "叫救護車",
            "heart attack", "心臟病", "stroke", "中風", "can't breathe", "唔能夠呼吸",
            "severe pain", "劇痛", "unconscious", "暈倒", "bleeding heavily", "大量出血"
        ]
        
        if any(keyword in lower_input for keyword in emergency_keywords):
            return UrgencyLevel.EMERGENCY
            
        # High urgency indicators
        high_urgency_keywords = [
            "severe", "serious", "worried", "scared", "急", "嚴重", "擔心", "驚",
            "getting worse", "惡化", "can't sleep", "瞓唔著", "very painful", "好痛"
        ]
        
        if any(keyword in lower_input for keyword in high_urgency_keywords):
            return UrgencyLevel.HIGH
            
        # Medium urgency indicators
        medium_urgency_keywords = [
            "concerned", "uncomfortable", "不舒服", "關心", "bothering", "煩",
            "should I", "我應該", "what if", "如果", "is this normal", "係咪正常"
        ]
        
        if any(keyword in lower_input for keyword in medium_urgency_keywords):
            return UrgencyLevel.MEDIUM
            
        return UrgencyLevel.LOW
        
    def select_optimal_model(self, criteria: ModelSelectionCriteria) -> str:
        """
        Select optimal model based on criteria and performance metrics
        Based on _enhanced_model_selection() from healthcare_ai_system
        """
        # Emergency scenarios always use premium models
        if criteria.urgency_level == UrgencyLevel.EMERGENCY:
            return self._select_from_chain("emergency")
            
        # Critical tasks need high-quality models
        if criteria.task_complexity == TaskComplexity.CRITICAL:
            return self._select_from_chain("critical")
            
        # Cost-constrained scenarios
        if criteria.cost_constraints and criteria.cost_constraints.get("budget_limit"):
            budget_limit = Decimal(str(criteria.cost_constraints["budget_limit"]))
            return self._select_cost_optimized_model(budget_limit, criteria)
            
        # Performance-constrained scenarios
        if criteria.performance_requirements:
            if criteria.performance_requirements.get("max_response_time_ms"):
                return self._select_fast_model(criteria)
                
        # Agent-specific optimizations
        if criteria.agent_type == "safety":
            return self._select_from_chain("emergency")
        elif criteria.agent_type == "mental_health" and criteria.task_complexity == TaskComplexity.COMPLEX:
            return self._select_from_chain("quality_optimized")
        elif criteria.agent_type == "illness_monitor" and criteria.urgency_level in [UrgencyLevel.HIGH, UrgencyLevel.MEDIUM]:
            return self._select_from_chain("standard")
            
        # Default selection based on task complexity
        if criteria.task_complexity == TaskComplexity.COMPLEX:
            return self._select_from_chain("quality_optimized")
        elif criteria.task_complexity == TaskComplexity.MODERATE:
            return self._select_from_chain("standard")
        else:
            return self._select_from_chain("cost_optimized")
            
    def _select_from_chain(self, chain_type: str) -> str:
        """Select model from fallback chain considering performance metrics"""
        chain = self.fallback_chain.get(chain_type, self.fallback_chain["standard"])
        
        # Try each model in the chain, considering performance metrics
        for model_tier in chain:
            metrics = self.performance_metrics.get(model_tier)
            if metrics is None:
                continue
                
            # Skip models with high error rates (>20%)
            if metrics.error_rate > 0.2 and metrics.total_requests > 10:
                logger.warning(f"Skipping {model_tier} due to high error rate: {metrics.error_rate:.2%}")
                continue
                
            # Check if model was used recently (load balancing)
            last_used = self.usage_rotation.get(model_tier)
            if last_used and datetime.utcnow() - last_used < timedelta(minutes=1):
                continue
                
            self.usage_rotation[model_tier] = datetime.utcnow()
            return model_tier
            
        # If no model is available, return the first one in the chain
        return chain[0]
        
    def _select_cost_optimized_model(self, budget_limit: Decimal, criteria: ModelSelectionCriteria) -> str:
        """Select model based on budget constraints"""
        client = OpenRouterClient()  # Get static access to model specs
        
        # Filter models by cost
        suitable_models = []
        for tier, spec in client.MODELS.items():
            if spec.cost_per_1k_tokens <= budget_limit:
                metrics = self.performance_metrics.get(tier)
                suitable_models.append((tier, spec, metrics))
                
        if not suitable_models:
            # If no model fits budget, use the cheapest
            return "free"
            
        # Sort by performance and cost
        suitable_models.sort(key=lambda x: (
            x[2].error_rate if x[2] else 0.0,  # Lower error rate is better
            x[1].cost_per_1k_tokens  # Lower cost is better
        ))
        
        return suitable_models[0][0]
        
    def _select_fast_model(self, criteria: ModelSelectionCriteria) -> str:
        """Select model based on response time requirements"""
        max_response_time = criteria.performance_requirements.get("max_response_time_ms", 5000)
        
        # Filter models by average response time
        suitable_models = []
        for tier, metrics in self.performance_metrics.items():
            if metrics.total_requests > 0 and metrics.average_response_time_ms <= max_response_time:
                suitable_models.append((tier, metrics))
                
        if not suitable_models:
            # If no model meets requirements, use lite (usually fastest)
            return "lite"
            
        # Sort by response time
        suitable_models.sort(key=lambda x: x[1].average_response_time_ms)
        return suitable_models[0][0]
        
    async def make_request_with_fallback(
        self,
        criteria: ModelSelectionCriteria,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3
    ) -> ModelResponse:
        """
        Make request with automatic fallback on failure
        """
        client = await self.get_client()
        primary_model = self.select_optimal_model(criteria)
        
        # Try primary model first
        try:
            response = await client.make_request(
                model_tier=primary_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_type=criteria.agent_type,
                content_type=criteria.content_type
            )
            
            # Update performance metrics
            self.performance_metrics[primary_model].update_metrics(
                success=response.success,
                response_time_ms=response.processing_time_ms,
                cost=response.cost
            )
            
            if response.success:
                logger.info(f"Request successful with primary model: {primary_model}")
                return response
                
        except Exception as e:
            logger.warning(f"Primary model {primary_model} failed: {e}")
            self.performance_metrics[primary_model].update_metrics(
                success=False,
                response_time_ms=0,
                cost=Decimal('0.0')
            )
            
        # Try fallback models
        fallback_chain = self._get_fallback_chain_for_criteria(criteria)
        for model_tier in fallback_chain:
            if model_tier == primary_model:  # Skip primary model
                continue
                
            try:
                response = await client.make_request(
                    model_tier=model_tier,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    agent_type=criteria.agent_type,
                    content_type=criteria.content_type
                )
                
                # Update performance metrics
                self.performance_metrics[model_tier].update_metrics(
                    success=response.success,
                    response_time_ms=response.processing_time_ms,
                    cost=response.cost
                )
                
                if response.success:
                    logger.info(f"Request successful with fallback model: {model_tier}")
                    return response
                    
            except Exception as e:
                logger.warning(f"Fallback model {model_tier} failed: {e}")
                self.performance_metrics[model_tier].update_metrics(
                    success=False,
                    response_time_ms=0,
                    cost=Decimal('0.0')
                )
                continue
                
        # If all models failed, raise error
        raise AgentError(
            f"All models failed for agent_type: {criteria.agent_type}",
            agent_type=criteria.agent_type
        )
        
    def _get_fallback_chain_for_criteria(self, criteria: ModelSelectionCriteria) -> List[str]:
        """Get appropriate fallback chain based on criteria"""
        if criteria.urgency_level == UrgencyLevel.EMERGENCY:
            return self.fallback_chain["emergency"]
        elif criteria.task_complexity == TaskComplexity.CRITICAL:
            return self.fallback_chain["critical"]
        elif criteria.cost_constraints:
            return self.fallback_chain["cost_optimized"]
        else:
            return self.fallback_chain["standard"]
            
    def update_user_satisfaction(self, model_tier: str, satisfaction_score: float):
        """Update user satisfaction score for a model"""
        if model_tier in self.performance_metrics:
            metrics = self.performance_metrics[model_tier]
            if metrics.user_satisfaction_score == 0.0:
                metrics.user_satisfaction_score = satisfaction_score
            else:
                # Weighted average with more weight on recent feedback
                metrics.user_satisfaction_score = (
                    (metrics.user_satisfaction_score * 0.7) + (satisfaction_score * 0.3)
                )
                
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "models": {},
            "recommendations": []
        }
        
        for tier, metrics in self.performance_metrics.items():
            if metrics.total_requests > 0:
                report["models"][tier] = {
                    "total_requests": metrics.total_requests,
                    "success_rate": (metrics.successful_requests / metrics.total_requests) * 100,
                    "error_rate": metrics.error_rate * 100,
                    "average_response_time_ms": metrics.average_response_time_ms,
                    "average_cost": float(metrics.average_cost),
                    "user_satisfaction_score": metrics.user_satisfaction_score,
                    "last_used": metrics.last_used.isoformat() if metrics.last_used else None
                }
                
        # Generate recommendations
        report["recommendations"] = self._generate_recommendations()
        
        return report
        
    def _generate_recommendations(self) -> List[str]:
        """Generate performance-based recommendations"""
        recommendations = []
        
        for tier, metrics in self.performance_metrics.items():
            if metrics.total_requests < 10:
                continue
                
            if metrics.error_rate > 0.15:
                recommendations.append(
                    f"Model '{tier}' has high error rate ({metrics.error_rate:.2%}). "
                    "Consider investigating or reducing usage."
                )
                
            if metrics.user_satisfaction_score < 3.0 and metrics.user_satisfaction_score > 0:
                recommendations.append(
                    f"Model '{tier}' has low user satisfaction ({metrics.user_satisfaction_score:.1f}/5). "
                    "Consider adjusting usage patterns."
                )
                
            if metrics.average_response_time_ms > 10000:  # 10 seconds
                recommendations.append(
                    f"Model '{tier}' has slow response times ({metrics.average_response_time_ms:.0f}ms). "
                    "Consider using for non-urgent requests only."
                )
                
        return recommendations
        
    def reset_performance_metrics(self):
        """Reset all performance metrics"""
        self._initialize_performance_tracking()
        self.usage_rotation.clear()
        logger.info("Performance metrics reset")


# Global model manager instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get or create the global model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
