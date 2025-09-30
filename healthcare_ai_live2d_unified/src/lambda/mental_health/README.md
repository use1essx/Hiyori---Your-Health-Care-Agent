# Mental Health Support Lambda Function

AWS Lambda function for the Mental Health Agent (小星星) - VTuber-style AI companion specialized in mental health support for children and teenagers in Hong Kong.

## Features

- **VTuber Personality**: Engaging, youth-friendly communication style with emojis and internet language
- **Crisis Detection**: Automatic detection of self-harm, suicidal ideation, and severe distress
- **Youth-Focused**: Specialized support for children and teenagers (ages 6-18)
- **Cultural Sensitivity**: Understanding of Hong Kong education system and family dynamics
- **Crisis Intervention**: Automatic alerts and professional referrals for high-risk situations
- **Traditional Chinese Support**: Full Traditional Chinese language support
- **Privacy Protection**: Age-appropriate privacy measures with safety overrides

## Architecture

```
User Input → Lambda Handler → Mental Health Agent → AWS Bedrock → VTuber Response
                ↓                                      ↓
            DynamoDB Storage                    Crisis Alert (SNS)
```

## Environment Variables

- `CONVERSATIONS_TABLE`: DynamoDB table for conversation storage
- `USERS_TABLE`: DynamoDB table for user profiles
- `CRISIS_ALERT_TOPIC`: SNS topic for crisis alerts
- `ENVIRONMENT`: Deployment environment (dev/staging/prod)

## Input Format

```json
{
  "message": "I'm feeling really sad and stressed about school",
  "conversation_id": "teen123_20241201",
  "user_id": "teen123",
  "language_preference": "zh"
}
```

## Output Format

```json
{
  "response": "✨ Hey! 我係Little Star！💙 我明白學校壓力真係好大...",
  "agent": "mental_health",
  "avatar": "Little Star",
  "confidence": 0.85,
  "urgency_level": "medium",
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "conversation_id": "teen123_20241201",
  "requires_followup": true,
  "crisis_alert_sent": false
}
```

## Agent Capabilities

### Can Handle
- School stress and academic pressure (DSE, exams, grades)
- Peer relationships and social anxiety
- Family conflicts and cultural pressures
- Identity formation and self-esteem issues
- Mild to moderate depression and anxiety
- Bullying and cyberbullying concerns
- Sleep and eating pattern disruptions

### Cannot Handle (Defers to Safety Guardian)
- Active suicidal ideation or self-harm
- Severe mental health crises
- Substance abuse emergencies
- Psychotic episodes or severe dissociation

## Crisis Detection

The agent automatically detects and categorizes crisis indicators:

- **Self-harm**: Cutting, self-injury references
- **Suicidal ideation**: Death wishes, suicide plans
- **Hopelessness**: Extreme despair, worthlessness
- **Isolation**: Complete social withdrawal
- **Substance use**: Drug or alcohol abuse
- **Eating issues**: Severe eating disorders

## VTuber Personality Features

- **Emojis**: ✨💙😅🎮😔💫
- **Mixed Language**: English + Traditional Chinese + internet slang
- **Excited Reactions**: "OMG that's so cool!", "等等等，講多啲！"
- **Gentle Teasing**: "你真係好鬼gaming 😏"
- **Supportive Language**: "你好勇敢講出嚟！", "我明白你嘅感受！"

## Age-Specific Adaptations

### Children (6-12 years)
- Simple, playful language
- Emotion comparison to colors/weather/animals
- Parent involvement in support decisions
- Age-appropriate coping strategies

### Teenagers (13-18 years)
- Understanding of DSE and school pressures
- Respect for privacy with safety overrides
- Teen slang and internet language
- Independence-building approaches

## Crisis Alert System

When crisis indicators are detected:

1. **Immediate Response**: Provide crisis resources and safety information
2. **Professional Alert**: Send SNS notification to crisis response team
3. **Parent Notification**: Alert parents/guardians for minors
4. **Follow-up Flagging**: Mark conversation for professional review

## Hong Kong Cultural Context

- **Education System**: DSE pressure, tutoring culture, academic competition
- **Family Dynamics**: Filial piety, face-saving, generation gaps
- **Living Conditions**: Small spaces, multi-generational households
- **Social Pressures**: Economic concerns, future uncertainty

## Safety Features

- **Crisis Resources**: Automatic inclusion of Samaritans hotline (2896 0000)
- **Professional Boundaries**: Clear referral to mental health professionals
- **Privacy Protection**: Age-appropriate privacy with safety overrides
- **Mandatory Reporting**: Automatic alerts for high-risk situations

## Testing

Run tests with:
```bash
python -m pytest test_handler.py -v
```

## Deployment

This Lambda function is deployed as part of the healthcare AI CloudFormation stack with:
- Crisis alert SNS topic integration
- DynamoDB tables for conversation storage
- IAM roles for Bedrock and SNS access

## Model Optimization

- **Preferred Model**: Claude-3-Haiku for consistent, safe mental health responses
- **Lower Temperature**: 0.6 for more predictable, supportive responses
- **Longer Responses**: Up to 1200 tokens for comprehensive support
- **Fallback Strategy**: Graceful degradation with crisis resource information