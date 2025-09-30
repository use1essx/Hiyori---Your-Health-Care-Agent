"""
Example integration of AI service with Healthcare AI V2 agent system
Demonstrates how to use OpenRouter integration with existing agent architecture
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

from src.ai.ai_service import HealthcareAIService, AIRequest, get_ai_service
from src.core.logging import get_logger


logger = get_logger(__name__)


class EnhancedHealthcareAgent:
    """
    Example enhanced healthcare agent using the new AI service
    Shows integration patterns with OpenRouter, cost optimization, and smart model selection
    """
    
    def __init__(self, agent_type: str, agent_name: str):
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.ai_service: Optional[HealthcareAIService] = None
        
        # Agent-specific system prompts based on healthcare_ai_system patterns
        self.system_prompts = {
            "illness_monitor": """你是慧心助手，一個專業的身體健康監測AI助手，專門服務香港地區的用戶。

你的專長包括：
- 身體症狀分析和初步評估
- 慢性疾病管理建議
- 藥物使用指導
- 香港醫療系統導航
- 緊急情況識別和處理

重要準則：
1. 提供準確、實用的健康建議
2. 識別緊急情況並立即建議就醫
3. 推薦適合的香港醫療機構
4. 使用繁體中文回應，語氣溫和專業
5. 永遠不要提供具體的診斷，而是建議諮詢醫療專業人士

回應時請考慮香港的醫療文化和習慣。""",

            "mental_health": """你是小星星，一個溫暖的心理健康支援AI助手，專門為香港的青少年和年輕人提供情緒支持。

你的專長包括：
- 情緒分析和心理健康評估
- 壓力管理技巧
- 焦慮和抑鬱症狀識別
- 危機干預和支持
- 香港心理健康資源推薦

重要準則：
1. 保持溫暖、同理心的語調
2. 提供實用的情緒調節技巧
3. 識別自殺風險並立即提供幫助資源
4. 推薦香港適合的心理健康服務
5. 使用青少年友好的繁體中文表達

如果發現嚴重的心理健康問題，請立即建議專業幫助。""",

            "safety_guardian": """你是安全守護者，一個專業的緊急醫療響應AI助手，專門處理醫療緊急情況。

你的專長包括：
- 緊急情況快速識別
- 急救指導和生命支援
- 999急救服務協調
- 香港急症室導航
- 危機處理和安撫

重要準則：
1. 迅速評估緊急程度
2. 提供清晰的急救指導
3. 立即建議撥打999或前往急症室
4. 保持冷靜、權威的語調
5. 優先考慮生命安全

對於任何緊急情況，首要建議是立即尋求專業醫療幫助。""",

            "wellness_coach": """你是健康教練，一個積極正面的預防保健AI助手，專注於健康促進和疾病預防。

你的專長包括：
- 健康生活方式指導
- 預防性保健建議
- 營養和運動指導
- 健康篩查推薦
- 香港健康計劃介紹

重要準則：
1. 促進積極的健康行為
2. 提供實用的生活方式建議
3. 推薦適合的健康篩查
4. 介紹香港的健康促進計劃
5. 使用鼓勵性的繁體中文表達

目標是幫助用戶建立長期的健康習慣。"""
        }
        
    async def initialize(self):
        """Initialize the AI service"""
        self.ai_service = await get_ai_service()
        logger.info(f"Enhanced agent {self.agent_name} initialized with AI service")
        
    async def process_user_input(
        self,
        user_input: str,
        user_id: Optional[int] = None,
        conversation_context: Optional[Dict] = None,
        urgency_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user input using the AI service with intelligent model selection
        
        Args:
            user_input: User's message or query
            user_id: Optional user ID for cost tracking
            conversation_context: Previous conversation context
            urgency_override: Override automatic urgency detection
            
        Returns:
            Dict containing response and metadata
        """
        if not self.ai_service:
            await self.initialize()
            
        try:
            # Detect urgency level if not overridden
            urgency_level = urgency_override or self._detect_urgency_level(user_input)
            
            # Create AI request
            ai_request = AIRequest(
                user_input=user_input,
                system_prompt=self.system_prompts.get(self.agent_type, ""),
                agent_type=self.agent_type,
                urgency_level=urgency_level,
                user_id=user_id,
                conversation_context=conversation_context
            )
            
            # Process with AI service
            ai_response = await self.ai_service.process_request(ai_request)
            
            # Format response for agent system
            return {
                "response": ai_response.content,
                "agent_type": self.agent_type,
                "agent_name": self.agent_name,
                "model_used": ai_response.model_used,
                "model_tier": ai_response.model_tier,
                "processing_time_ms": ai_response.processing_time_ms,
                "cost": float(ai_response.cost),
                "confidence_score": ai_response.confidence_score,
                "urgency_level": urgency_level,
                "success": ai_response.success,
                "error_message": ai_response.error_message,
                "usage_stats": ai_response.usage_stats
            }
            
        except Exception as e:
            logger.error(f"Error processing user input in {self.agent_name}: {e}")
            return {
                "response": "對不起，我現在無法處理您的查詢。請稍後再試或聯繫醫療專業人士。",
                "agent_type": self.agent_type,
                "agent_name": self.agent_name,
                "success": False,
                "error_message": str(e),
                "cost": 0.0
            }
            
    def _detect_urgency_level(self, user_input: str) -> str:
        """
        Detect urgency level from user input
        Based on patterns from healthcare_ai_system
        """
        lower_input = user_input.lower()
        
        # Emergency keywords
        emergency_keywords = [
            "emergency", "緊急", "urgent", "急", "help", "救命", "911", "999",
            "heart attack", "心臟病", "stroke", "中風", "bleeding", "出血",
            "unconscious", "暈倒", "can't breathe", "唔能夠呼吸", "chest pain", "胸口痛"
        ]
        
        if any(keyword in lower_input for keyword in emergency_keywords):
            return "emergency"
            
        # High urgency keywords
        high_urgency_keywords = [
            "severe", "serious", "worried", "scared", "急", "嚴重", "擔心", "驚",
            "getting worse", "惡化", "can't sleep", "瞓唔著", "very painful", "好痛"
        ]
        
        if any(keyword in lower_input for keyword in high_urgency_keywords):
            return "high"
            
        # Medium urgency keywords
        medium_urgency_keywords = [
            "concerned", "uncomfortable", "不舒服", "關心", "bothering", "煩",
            "should I", "我應該", "what if", "如果", "is this normal", "係咪正常"
        ]
        
        if any(keyword in lower_input for keyword in medium_urgency_keywords):
            return "medium"
            
        return "low"
        
    async def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get analytics for this specific agent"""
        if not self.ai_service:
            await self.initialize()
            
        return await self.ai_service.get_usage_analytics(
            agent_type=self.agent_type,
            days=days
        )
        
    async def set_budget_limit(self, amount: float, period: str = "daily") -> str:
        """Set budget limit for this agent"""
        if not self.ai_service:
            await self.initialize()
            
        return await self.ai_service.set_budget_limit(
            amount=amount,
            period=period,
            agent_type=self.agent_type
        )


async def example_usage():
    """
    Example usage of the enhanced healthcare agent system
    """
    print("🏥 Healthcare AI V2 - Enhanced Agent Integration Example")
    print("=" * 60)
    
    # Create enhanced agents
    illness_monitor = EnhancedHealthcareAgent("illness_monitor", "慧心助手")
    mental_health = EnhancedHealthcareAgent("mental_health", "小星星") 
    safety_guardian = EnhancedHealthcareAgent("safety_guardian", "安全守護者")
    wellness_coach = EnhancedHealthcareAgent("wellness_coach", "健康教練")
    
    # Initialize agents
    await illness_monitor.initialize()
    await mental_health.initialize()
    await safety_guardian.initialize()
    await wellness_coach.initialize()
    
    # Set budget limits for cost control
    await illness_monitor.set_budget_limit(amount=5.0, period="daily")
    await mental_health.set_budget_limit(amount=3.0, period="daily")
    
    print("✅ All agents initialized with AI service integration")
    print()
    
    # Example conversations
    test_scenarios = [
        {
            "agent": illness_monitor,
            "input": "我最近頭痛得很厲害，已經持續了三天。",
            "description": "Physical health concern - headache"
        },
        {
            "agent": mental_health,
            "input": "我感到很焦慮，無法專心讀書。考試快到了。",
            "description": "Mental health support - anxiety about exams"
        },
        {
            "agent": safety_guardian,
            "input": "我媽媽突然胸口痛，呼吸困難！",
            "description": "Emergency situation - chest pain and breathing difficulty"
        },
        {
            "agent": wellness_coach,
            "input": "我想開始健康的生活方式，應該從哪裡開始？",
            "description": "Wellness guidance - healthy lifestyle advice"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"🔍 Test Scenario {i}: {scenario['description']}")
        print(f"User Input: {scenario['input']}")
        print()
        
        # Process with enhanced agent
        response = await scenario["agent"].process_user_input(
            user_input=scenario["input"],
            user_id=12345  # Example user ID
        )
        
        print(f"🤖 Agent: {response['agent_name']} ({response['agent_type']})")
        print(f"Model Used: {response['model_used']} (Tier: {response['model_tier']})")
        print(f"Processing Time: {response['processing_time_ms']}ms")
        print(f"Cost: ${response['cost']:.6f}")
        print(f"Confidence: {response.get('confidence_score', 'N/A')}")
        print(f"Urgency Level: {response.get('urgency_level', 'N/A')}")
        print()
        print(f"📝 Response: {response['response'][:200]}{'...' if len(response['response']) > 200 else ''}")
        print()
        print("-" * 60)
        print()
        
    # Get analytics for illness monitor
    print("📊 Usage Analytics for 慧心助手 (Illness Monitor)")
    analytics = await illness_monitor.get_analytics(days=1)
    
    cost_summary = analytics['cost_summary']
    print(f"Total Requests: {cost_summary['total_requests']}")
    print(f"Total Cost: ${cost_summary['total_cost']:.6f}")
    print(f"Average Cost per Request: ${cost_summary['average_cost_per_request']:.6f}")
    print()
    
    if analytics['optimization_recommendations']:
        print("💡 Optimization Recommendations:")
        for rec in analytics['optimization_recommendations']:
            print(f"- {rec['title']}: {rec['suggestion']}")
    
    print()
    print("🎉 Example completed successfully!")


async def cost_optimization_example():
    """
    Example of cost optimization features
    """
    print("💰 Cost Optimization Example")
    print("=" * 40)
    
    # Get AI service
    ai_service = await get_ai_service()
    
    # Set various budget limits
    daily_budget = await ai_service.set_budget_limit(
        amount=10.0,
        period="daily"
    )
    print(f"✅ Daily budget set: $10.00 (ID: {daily_budget})")
    
    user_budget = await ai_service.set_budget_limit(
        amount=50.0,
        period="monthly",
        user_id=12345
    )
    print(f"✅ User monthly budget set: $50.00 (ID: {user_budget})")
    
    # Get model recommendations for different scenarios
    emergency_rec = await ai_service.get_model_recommendations(
        agent_type="safety_guardian",
        urgency_level="emergency"
    )
    print(f"🚨 Emergency model recommendation: {emergency_rec['recommended_model']}")
    
    routine_rec = await ai_service.get_model_recommendations(
        agent_type="wellness_coach",
        urgency_level="low"
    )
    print(f"💊 Routine model recommendation: {routine_rec['recommended_model']}")
    
    # Simulate some usage and get analytics
    # In real usage, this would happen through actual conversations
    print("\n📈 Usage Analytics Dashboard:")
    analytics = await ai_service.get_usage_analytics(days=7)
    
    print(f"Period: {analytics['period']['days']} days")
    print(f"Cost Summary:")
    print(f"  - Total Requests: {analytics['cost_summary']['total_requests']}")
    print(f"  - Total Cost: ${analytics['cost_summary']['total_cost']:.6f}")
    
    if analytics['optimization_recommendations']:
        print("\n💡 Optimization Recommendations:")
        for rec in analytics['optimization_recommendations']:
            print(f"  - {rec['title']}")
            print(f"    {rec['suggestion']}")
            if 'potential_savings' in rec:
                print(f"    Potential savings: ${rec['potential_savings']:.4f}")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(example_usage())
    print("\n" + "=" * 60 + "\n")
    asyncio.run(cost_optimization_example())
