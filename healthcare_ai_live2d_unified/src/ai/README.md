# Healthcare AI V2 - OpenRouter Integration System

A comprehensive AI integration system for Healthcare AI V2 that provides intelligent model selection, cost optimization, and performance tracking using OpenRouter and future AWS Bedrock integration.

## 📁 System Architecture

```
src/ai/
├── __init__.py                 # AI module initialization
├── openrouter_client.py        # OpenRouter API client with advanced features
├── model_manager.py            # Smart model selection and performance tracking
├── cost_optimizer.py           # Usage analytics and budget management
├── ai_service.py              # Main AI service orchestrator
├── providers/                  # AI provider integrations
│   ├── __init__.py
│   └── aws_bedrock.py         # Future AWS Bedrock integration (commented)
└── examples/
    └── agent_integration.py   # Integration examples with healthcare agents
```

## 🚀 Key Features

### ✅ OpenRouter Integration
- **Multi-model support**: Free, Lite, Flash, and Premium tiers
- **Intelligent routing**: AI-powered model selection based on task complexity
- **Cost optimization**: Dynamic token allocation and budget management
- **Performance tracking**: Response time, success rate, and user satisfaction metrics
- **Fallback mechanisms**: Automatic failover between models

### ✅ Smart Model Selection
Based on patterns from the original healthcare_ai_system:
- **Task complexity analysis**: Simple, Moderate, Complex, Critical
- **Urgency detection**: Low, Medium, High, Emergency
- **Agent-specific optimization**: Different models for different healthcare agents
- **Content type detection**: Emergency, Illness Assessment, Mental Health, etc.
- **Cost-aware selection**: Budget constraints and performance requirements

### ✅ Cost Optimization
- **Real-time usage tracking**: Token usage, costs, and performance metrics
- **Budget limits**: Daily, weekly, monthly, yearly limits per user/agent
- **Cost analytics**: Detailed breakdowns by model, agent, and category
- **Optimization recommendations**: AI-generated suggestions for cost reduction
- **Alert system**: Budget warnings and usage notifications

### ✅ Future-Ready Architecture
- **AWS Bedrock preparation**: Commented code ready for future implementation
- **Provider abstraction**: Easy to add new AI providers
- **Modular design**: Each component can be used independently
- **Configuration-driven**: All settings configurable via environment variables

## 🔧 Configuration

Add these settings to your `.env` file:

```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_DEFAULT_MODEL=lite
OPENROUTER_APP_NAME="Healthcare AI V2"

# AWS Bedrock (Future)
AWS_BEDROCK_ENABLED=false
AWS_BEDROCK_REGION=us-east-1
AWS_BEDROCK_DEFAULT_MODEL=claude_3_haiku
```

## 📊 Model Specifications

### OpenRouter Models

| Tier | Model | Cost/1K Tokens | Max Tokens | Use Cases |
|------|-------|----------------|------------|-----------|
| **Free** | `google/gemma-2-9b-it:free` | $0.000 | 1,200 | Basic queries, testing |
| **Lite** | `google/gemini-2.5-flash-lite` | $0.001 | 2,000 | Routine health queries |
| **Premium** | `google/gemini-2.5-flash` | $0.002 | 3,500 | Complex medical analysis and critical assessments |

### Model Selection Logic

```python
# Emergency situations → Premium models
if urgency_level == "emergency":
    return "premium"

# Complex medical queries → High-quality models  
if task_complexity == "complex":
    return "premium" or "lite"

# Routine queries → Cost-effective models
if task_complexity == "simple":
    return "lite" or "free"

# Cost-constrained → Budget models
if budget_limit < 0.01:
    return "free" or "lite"
```

## 🏥 Healthcare Agent Integration

### Basic Usage

```python
from src.ai.ai_service import get_ai_service, AIRequest

# Initialize AI service
ai_service = await get_ai_service()

# Create request
request = AIRequest(
    user_input="我頭痛得很厲害",
    system_prompt="你是專業的醫療AI助手...",
    agent_type="illness_monitor",
    urgency_level="medium",
    user_id=12345
)

# Process with intelligent model selection
response = await ai_service.process_request(request)

print(f"Response: {response.content}")
print(f"Model: {response.model_used} (Cost: ${response.cost})")
```

### Enhanced Agent Example

```python
from src.ai.examples.agent_integration import EnhancedHealthcareAgent

# Create enhanced agent with AI service integration
agent = EnhancedHealthcareAgent("illness_monitor", "慧心助手")
await agent.initialize()

# Set budget limit
await agent.set_budget_limit(amount=5.0, period="daily")

# Process user input with automatic model selection
response = await agent.process_user_input(
    user_input="我最近頭痛得很厲害",
    user_id=12345
)

print(f"Response: {response['response']}")
print(f"Cost: ${response['cost']}")
print(f"Model: {response['model_used']}")
```

## 💰 Cost Management

### Setting Budget Limits

```python
# Daily budget for entire system
daily_budget = await ai_service.set_budget_limit(
    amount=10.0,
    period="daily"
)

# Monthly budget for specific user
user_budget = await ai_service.set_budget_limit(
    amount=50.0,
    period="monthly", 
    user_id=12345
)

# Budget for specific agent type
agent_budget = await ai_service.set_budget_limit(
    amount=20.0,
    period="weekly",
    agent_type="illness_monitor"
)
```

### Usage Analytics

```python
# Get comprehensive analytics
analytics = await ai_service.get_usage_analytics(
    user_id=12345,
    agent_type="illness_monitor",
    days=7
)

print(f"Total cost: ${analytics['cost_summary']['total_cost']}")
print(f"Total requests: {analytics['cost_summary']['total_requests']}")
print(f"Average cost per request: ${analytics['cost_summary']['average_cost_per_request']}")

# Get optimization recommendations
for rec in analytics['optimization_recommendations']:
    print(f"💡 {rec['title']}: {rec['suggestion']}")
```

## 🎯 Task Complexity Detection

The system automatically detects task complexity and selects appropriate models:

### Emergency Detection
```python
emergency_keywords = [
    "emergency", "緊急", "urgent", "急", "help", "救命",
    "heart attack", "心臟病", "stroke", "中風", "bleeding", "出血"
]
# → Uses premium models (Claude-3-Sonnet)
```

### Illness Assessment
```python
illness_keywords = [
    "symptom", "症狀", "pain", "痛", "fever", "發燒",
    "headache", "頭痛", "cough", "咳", "nausea", "嘔心"
]
# → Uses premium or lite models based on complexity
```

### Mental Health Support
```python
mental_keywords = [
    "stress", "壓力", "anxiety", "焦慮", "depression", "抑鬱",
    "worried", "擔心", "overwhelmed", "不知所措"
]
# → Uses specialized models with empathy focus
```

## 📈 Performance Monitoring

### Real-time Metrics
- **Response time tracking**: Average, median, max response times
- **Success rate monitoring**: Track failures and fallback usage
- **Cost per request**: Monitor cost efficiency across models
- **User satisfaction**: Track user feedback and ratings

### Model Performance Reports
```python
performance = await ai_service.get_usage_analytics()

for model_tier, metrics in performance['model_efficiency'].items():
    print(f"{model_tier}:")
    print(f"  Success rate: {metrics['success_rate']:.1f}%")
    print(f"  Avg response time: {metrics['average_response_time_ms']:.0f}ms")
    print(f"  Cost per request: ${metrics['average_cost_per_request']:.6f}")
```

## 🔮 Future AWS Bedrock Integration

The system is prepared for AWS Bedrock integration:

```python
# When ready to enable Bedrock:
# 1. Set AWS_BEDROCK_ENABLED=true
# 2. Configure AWS credentials
# 3. Uncomment Bedrock imports
# 4. Models will be available alongside OpenRouter

bedrock_models = {
    "claude_3_sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude_3_haiku": "anthropic.claude-3-haiku-20240307-v1:0", 
    "titan_text": "amazon.titan-text-express-v1"
}
```

## 🔒 Security & Best Practices

### API Key Management
- Environment variables for production
- Fallback to config files for development
- No hardcoded API keys in code

### Cost Protection
- Automatic budget limits and alerts
- Model fallback chains to prevent high costs
- Usage tracking and anomaly detection

### Error Handling
- Comprehensive retry logic with exponential backoff
- Graceful degradation when services are unavailable
- Detailed logging for debugging and monitoring

## 🧪 Testing

Run the integration examples:

```bash
cd healthcare_ai_v2
python -m src.ai.examples.agent_integration
```

This will demonstrate:
- ✅ Multi-agent integration with AI service
- ✅ Automatic model selection based on urgency
- ✅ Cost tracking and budget management
- ✅ Performance monitoring and analytics
- ✅ Real-world healthcare scenarios

## 📚 Based on Original System

This implementation is based on patterns from `FYP/healthcare_ai_system/src/ai.py`:

- **ModelSpec pattern**: Model specifications with costs and capabilities
- **post_openrouter() function**: Request handling with retry logic
- **_enhanced_model_selection()**: Intelligent model selection logic
- **_calculate_dynamic_tokens()**: Dynamic token allocation
- **Content type detection**: Emergency, illness, mental health classification
- **Cultural context**: Hong Kong-specific healthcare considerations

## 🎯 Integration with Existing V2 Architecture

- **Pydantic settings**: Configuration through `src/config.py`
- **Database models**: Usage tracking via `src/database/models_comprehensive.py`
- **Repository pattern**: Data access through existing repositories
- **FastAPI integration**: Ready for API endpoint integration
- **Logging system**: Uses existing structured logging
- **Error handling**: Consistent with V2 exception patterns

---

**Ready for Production**: This system provides enterprise-grade AI integration with comprehensive cost controls, performance monitoring, and future-ready architecture for Healthcare AI V2! 🚀
