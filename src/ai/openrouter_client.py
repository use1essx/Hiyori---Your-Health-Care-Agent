"""
OpenRouter API client for Healthcare AI V2
Based on patterns from FYP healthcare_ai_system/src/ai.py
"""

import json
import time
import logging
import asyncio
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
import aiohttp

from src.config import settings
from src.core.exceptions import ExternalAPIError, ValidationError
from src.core.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ModelSpec:
    """Model specification with enhanced metadata"""
    model: str
    temperature: float
    cost_per_1k_tokens: Decimal
    max_tokens: int
    tier: str
    description: str
    capabilities: List[str]
    rate_limit_per_minute: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['cost_per_1k_tokens'] = float(self.cost_per_1k_tokens)
        return data


@dataclass
class UsageStats:
    """Token usage and cost tracking"""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: Decimal = Decimal('0.0')
    requests_count: int = 0
    
    def add_usage(self, prompt_tokens: int, completion_tokens: int, cost: Decimal):
        """Add usage data"""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += (prompt_tokens + completion_tokens)
        self.cost += cost
        self.requests_count += 1


@dataclass
class ModelResponse:
    """Standardized response from model"""
    content: str
    model: str
    usage: Dict[str, int]
    cost: Decimal
    processing_time_ms: int
    success: bool = True
    error_message: Optional[str] = None


class OpenRouterClient:
    """
    Production-ready OpenRouter API client with comprehensive features
    Based on patterns from healthcare_ai_system/src/ai.py post_openrouter()
    """
    
    # Model specifications - Google models only
    MODELS: Dict[str, ModelSpec] = {
        "free": ModelSpec(
            model="google/gemma-2-9b-it:free",
            temperature=0.3,
            cost_per_1k_tokens=Decimal('0.0'),
            max_tokens=1500,
            tier="free",
            description="Free tier model for basic queries",
            capabilities=["general", "basic_medical"],
            rate_limit_per_minute=20
        ),
        "lite": ModelSpec(
            model="google/gemini-2.5-flash-lite",
            temperature=0.3,
            cost_per_1k_tokens=Decimal('0.001'),
            max_tokens=2000,
            tier="lite",
            description="Fast, cost-effective model for routine queries",
            capabilities=["general", "medical", "fast_response"],
            rate_limit_per_minute=60
        ),
        "premium": ModelSpec(
            model="google/gemini-2.5-flash",
            temperature=0.2,
            cost_per_1k_tokens=Decimal('0.002'),
            max_tokens=3500,
            tier="premium",
            description="High-quality model for complex medical queries and critical assessments",
            capabilities=["general", "medical", "complex_reasoning", "emergency", "critical_care"],
            rate_limit_per_minute=60
        )
    }
    
    # Token calculation multipliers based on content type
    CONTENT_TOKEN_MULTIPLIERS = {
        "emergency_response": 2.5,
        "illness_assessment": 2.0,
        "mental_health_support": 1.8,
        "medication_guidance": 1.6,
        "health_education": 1.4,
        "daily_check_in": 1.2,
        "conversational": 1.0,
        "general": 1.0
    }
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.usage_stats: Dict[str, UsageStats] = {tier: UsageStats() for tier in self.MODELS.keys()}
        self.request_count = 0
        self.last_request_time = 0.0
        self._session: Optional[aiohttp.ClientSession] = None
        
    def _load_api_key(self) -> str:
        """
        Load OpenRouter API key with security best practices
        Never logs or exposes the actual key value
        """
        from src.core.api_security import APIKeyManager
        
        api_key = APIKeyManager.get_openrouter_key()
        if api_key and APIKeyManager.validate_api_key_format(api_key):
            return api_key
            
        raise RuntimeError(
            "OpenRouter API key not found or invalid format. "
            "Set OPENROUTER_API_KEY environment variable with a valid key."
        )
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Title": "Healthcare AI V2 - Hong Kong Medical Assistant",
                    "User-Agent": "HealthcareAI/2.0"
                }
            )
        return self._session
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def calculate_dynamic_tokens(
        self, 
        content_type: str, 
        prompt_length: int, 
        agent_type: str = "general"
    ) -> int:
        """
        Calculate dynamic token allocation based on content complexity
        Based on _calculate_dynamic_tokens() from healthcare_ai_system
        """
        # Base calculation from prompt length
        base_tokens = max(int(prompt_length * 0.7), 200)  # Conservative token estimation
        
        # Apply content type multiplier
        multiplier = self.CONTENT_TOKEN_MULTIPLIERS.get(content_type, 1.0)
        
        # Agent-specific adjustments
        if agent_type == "safety":
            multiplier *= 1.5  # Emergency responses need more tokens
        elif agent_type == "mental_health":
            multiplier *= 1.3  # Mental health needs nuanced responses
        elif agent_type == "illness_monitor":
            multiplier *= 1.2  # Medical assessments need detail
            
        final_tokens = int(base_tokens * multiplier)
        
        # Set bounds to prevent truncation while managing costs
        min_tokens = max(base_tokens, 300)
        max_tokens = min(final_tokens, 4000)
        
        return max(min_tokens, max_tokens)
    
    def detect_content_type(self, user_input: str, agent_type: str = "general") -> str:
        """
        Detect content type for optimal token allocation
        Based on detect_content_type() from healthcare_ai_system
        """
        lower_input = user_input.lower().strip()
        
        # Emergency detection (highest priority)
        emergency_keywords = [
            "emergency", "緊急", "urgent", "急", "help", "救命", "911", "999",
            "heart attack", "心臟病", "stroke", "中風", "bleeding", "出血",
            "unconscious", "暈倒", "can't breathe", "唔能夠呼吸", "chest pain", "胸口痛"
        ]
        
        if any(keyword in lower_input for keyword in emergency_keywords):
            return "emergency_response"
            
        # Illness assessment
        illness_keywords = [
            "symptom", "症狀", "pain", "痛", "fever", "發燒", "sick", "病",
            "headache", "頭痛", "cough", "咳", "nausea", "嘔心", "dizzy", "頭暈"
        ]
        
        if any(keyword in lower_input for keyword in illness_keywords):
            return "illness_assessment"
            
        # Mental health support
        mental_health_keywords = [
            "stress", "壓力", "anxiety", "焦慮", "depression", "抑鬱", "sad", "傷心",
            "worried", "擔心", "overwhelmed", "不知所措", "panic", "恐慌",
            "lonely", "孤獨", "mental health", "心理健康", "emotional", "情緒"
        ]
        
        if any(keyword in lower_input for keyword in mental_health_keywords):
            return "mental_health_support"
            
        # Medication guidance
        medication_keywords = [
            "medication", "藥物", "medicine", "藥", "pills", "藥丸", "dose", "劑量",
            "side effects", "副作用", "prescription", "處方"
        ]
        
        if any(keyword in lower_input for keyword in medication_keywords):
            return "medication_guidance"
            
        # Educational content
        educational_keywords = [
            "explain", "what is", "how does", "why", "tell me about",
            "點解", "咩係", "點樣", "解釋", "講解"
        ]
        
        if any(keyword in lower_input for keyword in educational_keywords):
            return "health_education"
            
        # Daily check-in
        daily_keywords = [
            "daily", "today", "recently", "lately", "最近", "今日", "昨日",
            "how are you", "點樣", "feeling", "感覺"
        ]
        
        if any(keyword in lower_input for keyword in daily_keywords):
            return "daily_check_in"
            
        return "conversational"
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int, model_spec: ModelSpec) -> Decimal:
        """Calculate cost based on token usage"""
        total_tokens = prompt_tokens + completion_tokens
        return (Decimal(total_tokens) / Decimal('1000')) * model_spec.cost_per_1k_tokens
    
    async def make_request(
        self,
        model_tier: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        agent_type: str = "general",
        content_type: Optional[str] = None
    ) -> ModelResponse:
        """
        Make request to OpenRouter API with comprehensive error handling
        Based on post_openrouter() pattern from healthcare_ai_system
        """
        start_time = time.time()
        
        # Get model specification
        if model_tier not in self.MODELS:
            raise ValidationError(f"Unknown model tier: {model_tier}")
            
        model_spec = self.MODELS[model_tier]
        
        # Auto-detect content type if not provided
        if content_type is None:
            content_type = self.detect_content_type(user_prompt, agent_type)
            
        # Calculate optimal token allocation
        if max_tokens is None:
            prompt_length = len(system_prompt) + len(user_prompt)
            max_tokens = self.calculate_dynamic_tokens(content_type, prompt_length, agent_type)
        
        # Use model defaults or override
        final_temperature = temperature if temperature is not None else model_spec.temperature
        
        # Prepare payload
        payload = {
            "model": model_spec.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": min(max_tokens, model_spec.max_tokens),
            "temperature": final_temperature,
            "stream": False
        }
        
        # Retry logic for transient failures
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                session = await self.get_session()
                
                async with session.post(self.base_url, json=payload) as response:
                    if response.status == 429:  # Rate limit
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise ExternalAPIError(
                                f"Rate limit exceeded after {max_retries} attempts",
                                service="openrouter"
                            )
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise ExternalAPIError(
                            f"OpenRouter API error {response.status}: {error_text}",
                            service="openrouter"
                        )
                    
                    data = await response.json()
                    
                    # Validate response structure
                    if "choices" not in data or not data["choices"]:
                        raise ValidationError("Invalid API response: missing choices")
                    
                    choice = data["choices"][0]
                    if "message" not in choice or "content" not in choice["message"]:
                        raise ValidationError("Invalid API response: missing message content")
                    
                    content = choice["message"]["content"].strip()
                    
                    # Extract usage information
                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    
                    # Calculate cost
                    cost = self._calculate_cost(prompt_tokens, completion_tokens, model_spec)
                    
                    # Update usage statistics
                    self.usage_stats[model_tier].add_usage(prompt_tokens, completion_tokens, cost)
                    self.request_count += 1
                    
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    
                    logger.info(
                        f"OpenRouter request successful",
                        extra={
                            "model": model_spec.model,
                            "tier": model_tier,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "cost": float(cost),
                            "processing_time_ms": processing_time_ms,
                            "content_type": content_type,
                            "agent_type": agent_type
                        }
                    )
                    
                    return ModelResponse(
                        content=content,
                        model=model_spec.model,
                        usage=usage,
                        cost=cost,
                        processing_time_ms=processing_time_ms,
                        success=True
                    )
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Request failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"OpenRouter request failed after {max_retries} attempts: {e}")
                    raise ExternalAPIError(
                        f"OpenRouter request failed: {str(e)}",
                        service="openrouter"
                    )
            
            except Exception as e:
                logger.error(f"Unexpected error in OpenRouter request: {e}")
                return ModelResponse(
                    content="",
                    model=model_spec.model,
                    usage={},
                    cost=Decimal('0.0'),
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    success=False,
                    error_message=str(e)
                )
        
        # This should not be reached due to the retry logic
        raise ExternalAPIError("Unexpected error in retry logic", service="openrouter")
    
    def get_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get usage statistics for all model tiers"""
        stats = {}
        for tier, usage in self.usage_stats.items():
            stats[tier] = {
                "total_tokens": usage.total_tokens,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "cost": float(usage.cost),
                "requests_count": usage.requests_count,
                "average_cost_per_request": float(usage.cost / usage.requests_count) if usage.requests_count > 0 else 0.0
            }
        return stats
    
    def get_model_specs(self) -> Dict[str, Dict[str, Any]]:
        """Get all model specifications"""
        return {tier: spec.to_dict() for tier, spec in self.MODELS.items()}
    
    def reset_usage_stats(self):
        """Reset usage statistics (useful for testing or periodic resets)"""
        self.usage_stats = {tier: UsageStats() for tier in self.MODELS.keys()}
        self.request_count = 0
        
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self._session and not self._session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except Exception:
                pass  # Ignore cleanup errors


# Global client instance
_openrouter_client: Optional[OpenRouterClient] = None


async def get_openrouter_client() -> OpenRouterClient:
    """Get or create the global OpenRouter client instance"""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient()
    return _openrouter_client


async def cleanup_openrouter_client():
    """Cleanup the global OpenRouter client"""
    global _openrouter_client
    if _openrouter_client:
        await _openrouter_client.close()
        _openrouter_client = None
