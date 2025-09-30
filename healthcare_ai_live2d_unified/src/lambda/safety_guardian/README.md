# Safety Guardian Lambda Function

AWS Lambda function for the Safety Guardian Agent - Emergency response specialist for dual-population crisis intervention handling medical emergencies and mental health crises in Hong Kong.

## Features

- **Medical Emergency Detection**: Cardiac, respiratory, neurological, trauma, and poisoning emergencies
- **Mental Health Crisis Intervention**: Suicide prevention, self-harm detection, psychotic episodes
- **Hong Kong Emergency Integration**: Complete integration with local emergency services (999, Hospital Authority)
- **Professional Escalation**: Automatic alerts to emergency services and healthcare providers
- **Dual-Population Support**: Specialized protocols for elderly health emergencies and child/teen mental health crises
- **Immediate Safety Assessment**: Real-time risk evaluation and safety guidance
- **Crisis Communication**: Clear, authoritative emergency response communication

## Architecture

```
Emergency Input → Lambda Handler → Safety Guardian → AWS Bedrock → Emergency Response
                      ↓                                    ↓
                 DynamoDB Storage                   Emergency Alert (SNS)
                      ↓
              Professional Services Alert
```

## Environment Variables

- `CONVERSATIONS_TABLE`: DynamoDB table for emergency conversation storage
- `USERS_TABLE`: DynamoDB table for user profiles
- `EMERGENCY_ALERT_TOPIC`: SNS topic for emergency alerts
- `ENVIRONMENT`: Deployment environment (dev/staging/prod)

## Input Format

```json
{
  "message": "I'm having severe chest pain and can't breathe",
  "conversation_id": "emergency_20241201",
  "user_id": "user123",
  "language_preference": "en"
}
```

## Output Format

```json
{
  "response": "🔴 **Medical Emergency Activated** - I specialize in handling urgent health situations...",
  "agent": "safety_guardian",
  "avatar": "Safety Guardian",
  "confidence": 0.95,
  "urgency_level": "critical",
  "emergency_type": "medical",
  "emergency_indicators": ["medical_cardiac", "medical_respiratory"],
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "conversation_id": "emergency_20241201",
  "emergency_alert_sent": true,
  "professional_intervention_required": true
}
```

## Emergency Types

### Medical Emergencies
- **Cardiac**: Chest pain, heart attack symptoms
- **Respiratory**: Difficulty breathing, choking, severe asthma
- **Neurological**: Stroke, seizures, unconsciousness
- **Trauma**: Severe bleeding, broken bones, burns
- **Poisoning**: Overdose, toxic ingestion, allergic reactions

### Mental Health Crises
- **Suicidal**: Active suicidal ideation, suicide plans
- **Self-harm**: Cutting, self-injury behaviors
- **Psychotic**: Hallucinations, delusions, reality distortion
- **Severe Distress**: Extreme hopelessness, complete breakdown

## Agent Capabilities

### Can Handle
- Life-threatening medical emergencies
- Active mental health crises
- Suicide prevention and intervention
- Child safety emergencies
- Elderly health crises
- Immediate danger situations

### Exclusions (Routes to Other Agents)
- General health questions about family members
- Non-urgent medical advice
- Wellness coaching requests
- Routine mental health support

## Hong Kong Emergency Resources

### Medical Services
- **Emergency Phone**: 999
- **Hospital Authority**: Nearest A&E Department
- **Poison Information Centre**: (852) 2772 9933

### Mental Health Crisis
- **Samaritans Hong Kong**: 2896 0000 (24/7)
- **Suicide Prevention**: 2382 0000
- **OpenUp WhatsApp**: 9101 2012
- **Child Protection**: 2755 1122

### Emergency Services
- **Police**: 999
- **Fire Department**: 999

## Emergency Response Protocol

1. **Immediate Assessment**: Classify emergency type and severity
2. **Safety Guidance**: Provide immediate actionable safety instructions
3. **Professional Alert**: Send SNS notification to emergency response team
4. **Resource Provision**: Include relevant Hong Kong emergency contacts
5. **Continuous Support**: Maintain engagement until professional help arrives

## Crisis Alert System

When emergencies are detected:

1. **Automatic SNS Alert**: Sent to emergency response team
2. **Professional Notification**: Healthcare providers and emergency services
3. **Parent/Guardian Alert**: For minors in crisis
4. **Extended Retention**: Emergency conversations stored for 90 days
5. **Priority Flagging**: Marked as CRITICAL priority in database

## Safety Features

- **Fallback Responses**: Even system failures provide emergency guidance
- **Low Temperature AI**: Consistent, reliable emergency responses (0.3 temperature)
- **Immediate Contact Info**: Always includes 999 and crisis hotlines
- **Professional Boundaries**: Clear guidance to seek immediate professional help
- **Cultural Adaptation**: Hong Kong-specific emergency services and protocols

## Model Optimization

- **Reliability Focus**: Balanced model selection for consistent emergency responses
- **Concise Responses**: 800 token limit for clear, actionable guidance
- **High Confidence**: 0.95 confidence score for safety responses
- **Emergency Fallback**: Comprehensive fallback response for system failures

## Age-Specific Protocols

### Children (Under 12)
- Immediate parent/guardian notification
- Child Protection Hotline integration
- Age-appropriate safety language
- Enhanced professional oversight

### Teenagers (13-18)
- Balance privacy with safety requirements
- School counselor notification protocols
- Peer support resource inclusion
- Parent notification for high-risk situations

### Elderly (65+)
- Medical emergency prioritization
- Fall prevention and mobility concerns
- Medication-related emergency protocols
- Family caregiver notification

## Testing

Run tests with:
```bash
python -m pytest test_handler.py -v
```

## Deployment

This Lambda function is deployed as part of the healthcare AI CloudFormation stack with:
- Emergency alert SNS topic integration
- High-priority DynamoDB storage
- IAM roles for emergency service notifications
- Enhanced monitoring and alerting

## Compliance and Safety

- **Mandatory Reporting**: Automatic alerts for all emergency situations
- **Professional Oversight**: All emergency conversations flagged for review
- **Extended Retention**: 90-day storage for emergency conversations
- **Audit Trail**: Complete logging of all emergency interventions
- **Quality Assurance**: Regular review of emergency response effectiveness