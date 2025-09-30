# Wellness Coach Lambda Function

AWS Lambda function for the Wellness Coach Agent - Preventive health coaching specialist focused on wellness education and health promotion for all ages with cultural adaptation for Hong Kong lifestyle.

## Features

- **Preventive Health Focus**: Disease prevention and health optimization strategies
- **Lifestyle Coaching**: Exercise, nutrition, sleep, and stress management guidance
- **Behavior Change Support**: Goal setting, habit formation, and motivation
- **Age-Appropriate Guidance**: Specialized approaches for children, teens, adults, and elderly
- **Cultural Adaptation**: Hong Kong-specific lifestyle, environmental, and dietary considerations
- **Motivational Support**: Positive reinforcement and achievable goal setting
- **Holistic Wellness**: Physical, mental, and social aspects of health

## Architecture

```
User Input → Lambda Handler → Wellness Coach → AWS Bedrock → Motivational Response
                ↓                                    ↓
            DynamoDB Storage                  Wellness Tracking
```

## Environment Variables

- `CONVERSATIONS_TABLE`: DynamoDB table for conversation storage
- `USERS_TABLE`: DynamoDB table for user profiles
- `ENVIRONMENT`: Deployment environment (dev/staging/prod)

## Input Format

```json
{
  "message": "I want to start exercising but don't know where to begin",
  "conversation_id": "wellness_20241201",
  "user_id": "user123",
  "language_preference": "en"
}
```

## Output Format

```json
{
  "response": "💪 That's fantastic that you want to start exercising! Starting is often the hardest part...",
  "agent": "wellness_coach",
  "avatar": "Wellness Coach",
  "confidence": 0.8,
  "urgency_level": "low",
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "conversation_id": "wellness_20241201",
  "wellness_topics": ["exercise", "fitness"],
  "health_goals": ["start", "exercising"],
  "suggested_actions": [
    "Set realistic weekly exercise goals",
    "Find activities you enjoy for consistency",
    "Start slowly and gradually increase intensity"
  ],
  "requires_followup": true
}
```

## Agent Capabilities

### Can Handle
- Exercise and fitness guidance
- Nutrition and dietary advice
- Weight management strategies
- Sleep optimization
- Stress management techniques
- Preventive health screening
- Healthy aging strategies
- Lifestyle habit formation
- Health goal setting and tracking

### Cannot Handle (Defers to Other Agents)
- Medical emergencies or acute symptoms
- Mental health crises
- Specific medical diagnoses or treatments
- Medication management

## Wellness Topics

### Exercise & Fitness
- Age-appropriate exercise recommendations
- Hong Kong climate considerations (heat, humidity)
- Small space workout solutions
- Traditional activities (tai chi, qigong)

### Nutrition & Diet
- Balanced meal planning
- Hong Kong dietary culture adaptation
- Weight management strategies
- Hydration in tropical climate

### Sleep & Recovery
- Sleep hygiene practices
- Managing shift work (common in HK)
- Stress-related sleep issues
- Recovery optimization

### Stress Management
- Work-life balance (HK work culture)
- Commuting stress management
- Family pressure coping strategies
- Mindfulness and relaxation techniques

### Preventive Care
- Health screening schedules
- Vaccination recommendations
- Early detection strategies
- Risk factor management

## Age-Specific Adaptations

### Children (6-12 years)
- Growth and development support
- Building healthy habits foundation
- Active play and physical activity
- Parent involvement strategies

### Teenagers (13-18 years)
- Academic stress management
- Body image and self-esteem
- Peer pressure navigation
- Independence building

### Adults (19-64 years)
- Work-life balance optimization
- Chronic disease prevention
- Family health management
- Career stress handling

### Elderly (65+ years)
- Active aging strategies
- Fall prevention programs
- Cognitive health maintenance
- Social connection importance

## Hong Kong Cultural Adaptations

### Environmental Factors
- **Air Quality**: Indoor exercise recommendations during poor air quality days
- **Climate**: Heat and humidity exercise modifications
- **Space Constraints**: Small apartment workout solutions

### Work Culture
- **Long Hours**: Micro-workout integration into busy schedules
- **Commuting**: Active commuting strategies
- **Stress**: Traditional stress relief methods

### Dietary Culture
- **Dim Sum**: Healthier choices at yum cha
- **Tea Culture**: Leveraging tea for health benefits
- **Street Food**: Navigating local food options healthily

### Traditional Medicine
- **TCM Integration**: Combining Western wellness with traditional approaches
- **Herbal Remedies**: Safe integration with modern wellness
- **Holistic Approaches**: Mind-body wellness concepts

## Motivational Features

- **Positive Reinforcement**: Celebrating small victories and progress
- **Realistic Goals**: Achievable milestones that build confidence
- **Personalization**: Adapting recommendations to individual circumstances
- **Progress Tracking**: Monitoring and adjusting health goals
- **Empowerment**: Building confidence in healthy choice-making

## Safety Features

- **Professional Referrals**: Clear guidance on when to consult healthcare providers
- **Disclaimer Inclusion**: Appropriate health advice disclaimers
- **Boundary Respect**: Staying within wellness coaching scope
- **Risk Assessment**: Identifying when medical consultation is needed

## Goal Tracking

The agent automatically extracts and tracks:
- **Wellness Topics**: Exercise, nutrition, sleep, stress management
- **Health Goals**: Specific objectives mentioned by users
- **Progress Indicators**: Achievements and milestones
- **Follow-up Needs**: Areas requiring continued support

## Testing

Run tests with:
```bash
python -m pytest test_handler.py -v
```

## Deployment

This Lambda function is deployed as part of the healthcare AI CloudFormation stack with:
- DynamoDB integration for wellness tracking
- Bedrock access for motivational AI responses
- Cultural adaptation for Hong Kong context

## Model Optimization

- **Balanced Approach**: Claude-3-Haiku for consistent wellness guidance
- **Motivational Temperature**: 0.7 for creative, encouraging responses
- **Comprehensive Responses**: Up to 1000 tokens for detailed guidance
- **Fallback Support**: Motivational fallback responses for system issues

## Compliance

- **Evidence-Based**: All recommendations based on established health guidelines
- **Professional Boundaries**: Clear scope limitations and referral protocols
- **Cultural Sensitivity**: Respectful adaptation to Hong Kong lifestyle
- **Privacy Protection**: Secure handling of wellness and health data