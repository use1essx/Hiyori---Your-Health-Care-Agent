# Agent Router Lambda Function

The Agent Router Lambda Function is the main routing component of the Healthcare AI system. It intelligently determines which healthcare agent should handle each user request based on message content analysis and user context.

## Features

### Intelligent Agent Selection (Requirement 4.1)
- **Keyword Analysis**: Matches user messages against agent-specific keywords in English and Traditional Chinese
- **Pattern Recognition**: Uses regex patterns to identify specific health concerns and contexts
- **Confidence Scoring**: Assigns confidence scores to agent selections based on match quality
- **Context Awareness**: Considers user profile and conversation history for better routing

### Multi-Agent Support (Requirement 4.2)
- **Four Healthcare Agents**: Routes to illness_monitor, mental_health, safety_guardian, or wellness_coach
- **Fallback Mechanism**: Defaults to wellness_coach for general health questions
- **Manual Override**: Supports explicit agent selection when specified by user

### Asynchronous Agent Invocation (Requirement 4.3)
- **Lambda-to-Lambda**: Invokes specific agent Lambda functions using AWS Lambda client
- **Synchronous Calls**: Uses RequestResponse invocation for immediate responses
- **Payload Management**: Passes user context and routing information to selected agents

### Error Handling and Fallbacks (Requirement 4.4)
- **Emergency Override**: Automatically routes emergency situations to Safety Guardian
- **Graceful Degradation**: Provides fallback responses when agent invocation fails
- **Confidence Thresholds**: Warns about low-confidence selections
- **Error Logging**: Comprehensive logging for debugging and monitoring

## Agent Selection Logic

### Safety Guardian (Emergency Priority)
**Triggers:**
- Emergency keywords: "emergency", "緊急", "urgent", "救命"
- Crisis indicators: "suicide", "自殺", "can't breathe", "chest pain"
- Medical emergencies: "overdose", "heart attack", "call ambulance"

**Confidence Boost:** +0.3 (highest priority)

### Illness Monitor (Physical Health)
**Triggers:**
- Symptom keywords: "pain", "痛", "sick", "病", "fever", "headache"
- Medical terms: "medication", "doctor", "hospital", "diagnosis"
- Chronic conditions: "diabetes", "hypertension", "chronic"

**Confidence Boost:** +0.2

### Mental Health (Emotional Support)
**Triggers:**
- Emotional keywords: "stress", "壓力", "anxiety", "depression", "sad"
- Mental health terms: "worried", "scared", "lonely", "overwhelmed"
- Mood indicators: "emotional", "心情", "mental health"

**Confidence Boost:** +0.2

### Wellness Coach (Prevention & Lifestyle)
**Triggers:**
- Health improvement: "healthy", "exercise", "diet", "nutrition"
- Lifestyle terms: "fitness", "wellness", "prevention", "habits"
- General wellness: "improve", "better", "lifestyle"

**Confidence Boost:** +0.1 (default fallback)

## Usage

### Direct Lambda Invocation
```python
import boto3
import json

lambda_client = boto3.client('lambda')

payload = {
    'message': 'I have a severe headache',
    'user_id': 'user123',
    'conversation_id': 'conv456'
}

response = lambda_client.invoke(
    FunctionName='dev-healthcare-agent-router',
    Payload=json.dumps(payload)
)
```

### API Gateway Integration
```bash
curl -X POST https://api-gateway-url/dev/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I feel very anxious",
    "user_id": "user123"
  }'
```

### Response Format
```json
{
  "response": "I understand you're feeling anxious...",
  "agent": "mental_health",
  "avatar": "Xiaoxing",
  "conversation_id": "uuid-here",
  "routing_info": {
    "confidence": 0.85,
    "reasons": ["Matched 2 keywords", "Matched 1 patterns"],
    "emergency_override": false
  }
}
```

## Configuration

### Environment Variables
- `ENVIRONMENT`: Deployment environment (dev/staging/prod)
- `CONVERSATIONS_TABLE`: DynamoDB table for conversation storage
- `USERS_TABLE`: DynamoDB table for user profiles

### Agent Function Mapping
```python
AGENT_FUNCTIONS = {
    'illness_monitor': f"{ENVIRONMENT}-healthcare-illness-monitor",
    'mental_health': f"{ENVIRONMENT}-healthcare-mental-health", 
    'safety_guardian': f"{ENVIRONMENT}-healthcare-safety-guardian",
    'wellness_coach': f"{ENVIRONMENT}-healthcare-wellness-coach"
}
```

## Testing

### Local Testing
```bash
cd healthcare_ai_live2d_unified/src/lambda/agent_router
python test_router.py
```

### Test Cases Covered
- Agent selection for different message types
- Emergency detection and override
- Confidence scoring accuracy
- Lambda handler integration
- Error handling scenarios

## Deployment

### Package Creation
```bash
python deploy.py [environment]
```

### CloudFormation Integration
The function is automatically deployed via the CloudFormation template with:
- Appropriate IAM permissions
- Environment variable configuration
- API Gateway integration
- CloudWatch logging

## Monitoring

### CloudWatch Metrics
- Invocation count and duration
- Error rates and types
- Agent selection distribution
- Confidence score trends

### Logging
- Request/response logging
- Agent selection reasoning
- Error details and stack traces
- Performance metrics

## Cost Optimization

### Lambda Configuration
- **Memory**: 256MB (optimized for routing logic)
- **Timeout**: 30 seconds
- **Reserved Concurrency**: 10 (cost control)

### Pay-per-Use Model
- No charges when idle
- Scales automatically with demand
- Minimal cold start impact due to lightweight code

## Security

### IAM Permissions
- DynamoDB read/write access to conversation and user tables
- Lambda invoke permissions for agent functions
- CloudWatch logs write access
- No external API access required

### Data Handling
- No sensitive data stored in function code
- User data encrypted in transit and at rest
- Conversation TTL for automatic cleanup
- CORS headers for web integration

## Future Enhancements

### Planned Features
- AI-powered agent selection using AWS Bedrock
- Multi-agent collaboration scenarios
- Real-time confidence adjustment based on outcomes
- Advanced context analysis including conversation sentiment
- Integration with user feedback for routing improvement