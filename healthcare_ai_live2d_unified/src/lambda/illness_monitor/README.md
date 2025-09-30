# Illness Monitor Lambda Function

AWS Lambda function for the Illness Monitor Agent (慧心助手) - specialized in comprehensive illness monitoring and health management for Hong Kong residents.

## Features

- **Illness Monitoring**: Symptom tracking and health pattern detection
- **Chronic Disease Support**: Diabetes, hypertension, heart disease management
- **Medication Guidance**: Side effect monitoring and compliance support
- **Traditional Chinese Support**: Full Traditional Chinese language support
- **AWS Bedrock Integration**: Cost-optimized AI processing with fallback models
- **DynamoDB Storage**: Conversation history and user profile management
- **Cultural Adaptation**: Hong Kong healthcare system and cultural context

## Architecture

```
User Input → Lambda Handler → Illness Monitor Agent → AWS Bedrock → Response
                ↓
            DynamoDB (Conversations & User Profiles)
```

## Environment Variables

- `CONVERSATIONS_TABLE`: DynamoDB table for conversation storage
- `USERS_TABLE`: DynamoDB table for user profiles
- `ENVIRONMENT`: Deployment environment (dev/staging/prod)

## Input Format

```json
{
  "message": "I have a headache and feel dizzy",
  "conversation_id": "user123_20241201",
  "user_id": "user123",
  "language_preference": "zh"
}
```

## Output Format

```json
{
  "response": "我理解您頭痛和頭暈的情況...",
  "agent": "illness_monitor",
  "avatar": "Hiyori",
  "confidence": 0.85,
  "urgency_level": "medium",
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "conversation_id": "user123_20241201"
}
```

## Agent Capabilities

### Can Handle
- Physical symptoms (pain, fever, fatigue, etc.)
- Chronic conditions (diabetes, hypertension, arthritis)
- Medication concerns and side effects
- Health monitoring and tracking
- Age-specific health concerns (especially elderly)

### Cannot Handle (Defers to Other Agents)
- Medical emergencies (chest pain, difficulty breathing)
- Mental health crises (suicide, self-harm)
- General wellness coaching
- Non-health related queries

## Cost Optimization

- **Model Selection**: Automatic fallback from advanced → balanced → fast models
- **DynamoDB**: On-demand billing with TTL for automatic cleanup
- **Serverless**: Pay-per-request pricing with no idle costs

## Testing

Run tests with:
```bash
python -m pytest test_handler.py -v
```

## Deployment

This Lambda function is deployed as part of the healthcare AI CloudFormation stack. See the main infrastructure documentation for deployment instructions.

## Traditional Chinese Support

The agent provides full Traditional Chinese support including:
- Traditional Chinese system prompts and responses
- Hong Kong cultural context and medical system awareness
- Appropriate honorifics for elderly users (您 vs 你)
- Local emergency service information (999, Hospital Authority)

## Safety Features

- Automatic safety disclaimers for medical advice
- Emergency contact information for concerning symptoms
- Professional referral recommendations
- Age-appropriate communication adaptations