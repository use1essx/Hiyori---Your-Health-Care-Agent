# Healthcare AI Live2D System 🏥✨

> **Intelligent Healthcare Assistant with Live2D Avatars on AWS**

A comprehensive healthcare AI system featuring interactive Live2D avatars that provide personalized health support in English and Traditional Chinese. Built for Hong Kong healthcare needs with AWS cloud infrastructure.

![Healthcare AI Demo](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![AWS](https://img.shields.io/badge/AWS-Serverless-orange)
![Live2D](https://img.shields.io/badge/Live2D-Interactive-blue)
![Languages](https://img.shields.io/badge/Languages-EN%20%7C%20ZH--HK-red)

## 🌟 Features

### 🤖 **Four Specialized Healthcare Agents**
- **🩺 Illness Monitor (Hiyori)** - Health symptom analysis and medical guidance
- **🧠 Mental Health Support (Xiaoxing)** - Stress, anxiety, and emotional support
- **🚨 Safety Guardian** - Emergency detection and crisis intervention
- **💪 Wellness Coach** - Health education, prevention, and lifestyle guidance

### 🎭 **Interactive Live2D Avatars**
- Realistic animated characters with facial expressions
- Voice synthesis with agent-specific personalities
- Speech-to-text input for natural conversations
- Multi-language support (English + Traditional Chinese)

### ☁️ **AWS Cloud Infrastructure**
- **Serverless architecture** for automatic scaling
- **Cost-optimized** with pay-per-use billing
- **Global CDN** for fast worldwide access
- **Enterprise security** with encryption and monitoring

### 🌏 **Hong Kong Healthcare Integration**
- Traditional Chinese language support (繁體中文)
- Local healthcare system knowledge
- Cultural sensitivity in health advice
- Emergency contact integration (999, local hotlines)

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- AWS Account ([Create one here](https://aws.amazon.com/))
- AWS CLI installed and configured
- Python 3.8+ installed

### One-Command Deployment

```bash
# 1. Clone the repository
git clone https://github.com/your-username/healthcare-ai-live2d.git
cd healthcare_ai_live2d_unified

# 2. Configure AWS CLI (if not already done)
aws configure

# 3. Run automated setup
python setup_aws_deployment.py

# 4. Deploy to AWS
./quick_deploy.sh
```

**That's it!** Your Healthcare AI system will be live on AWS in minutes.

### What You Get
- ✅ **Live Website**: Accessible globally via CloudFront CDN
- ✅ **API Endpoints**: RESTful API for all healthcare agents
- ✅ **Interactive Avatars**: Live2D characters with voice synthesis
- ✅ **Cost Monitoring**: Automated cost tracking and alerts
- ✅ **Security**: Enterprise-grade AWS security
- ✅ **Scalability**: Handles 1 to 1M+ users automatically

## 💬 Try It Out

After deployment, you can interact with the healthcare agents:

### English Examples
```
User: "I have a headache and feel dizzy"
Hiyori (Illness Monitor): "I understand you're experiencing a headache and dizziness. These symptoms could indicate several conditions..."

User: "I'm feeling stressed about work"
Xiaoxing (Mental Health): "Work stress is very common. Let's explore some techniques to help you manage these feelings..."

User: "I'm having chest pain"
Safety Guardian: "Chest pain can be serious. I recommend seeking immediate medical attention. Should I help you contact emergency services?"
```

### Traditional Chinese Examples
```
用戶: "我頭痛同頭暈"
Hiyori: "我明白你正在經歷頭痛和頭暈。這些症狀可能表示幾種情況..."

用戶: "我對工作感到很大壓力"
Xiaoxing: "工作壓力很常見。讓我們探討一些技巧來幫助你管理這些感受..."

用戶: "我胸痛"
Safety Guardian: "胸痛可能很嚴重。我建議立即尋求醫療協助。我應該幫你聯絡緊急服務嗎？"
```

## 🏗️ Architecture

### System Overview
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudFront    │    │   API Gateway    │    │ Lambda Functions│
│   (Frontend)    │◄──►│   (REST API)     │◄──►│ (Healthcare AI) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   S3 Bucket     │    │   DynamoDB       │    │  Amazon Bedrock │
│ (Static Assets) │    │ (Conversations)  │    │   (AI Models)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Components
- **Frontend**: Live2D avatars, voice interface, responsive web app
- **API Layer**: RESTful endpoints for chat, speech, file upload
- **AI Agents**: Specialized healthcare assistants using Amazon Bedrock
- **Data Storage**: DynamoDB for conversations, S3 for files
- **Speech Services**: AWS Transcribe (STT) + Polly (TTS)
- **Monitoring**: CloudWatch logs, cost alerts, performance metrics

## 📊 Cost Breakdown

### Expected Monthly Costs (USD)
| Component | Development | Production |
|-----------|-------------|------------|
| Lambda Functions | $3-8 | $8-20 |
| DynamoDB | $2-5 | $5-15 |
| Amazon Bedrock | $5-15 | $15-40 |
| S3 + CloudFront | $1-3 | $3-8 |
| API Gateway | $1-3 | $3-10 |
| Speech Services | $1-5 | $3-12 |
| **Total** | **$13-39** | **$37-105** |

### Cost Optimization Features
- ✅ **Auto-scaling**: Pay only for actual usage
- ✅ **DynamoDB TTL**: Automatic cleanup of old conversations
- ✅ **S3 Lifecycle**: Automatic archiving of old files
- ✅ **Lambda optimization**: Right-sized memory and timeout
- ✅ **Cost alerts**: Email notifications when thresholds exceeded

## 🛠️ Development

### Project Structure
```
healthcare_ai_live2d_unified/
├── 📁 src/
│   ├── 📁 lambda/              # AWS Lambda functions
│   │   ├── 📁 agent_router/    # Routes messages to appropriate agents
│   │   ├── 📁 illness_monitor/ # Health symptom analysis (Hiyori)
│   │   ├── 📁 mental_health/   # Mental health support (Xiaoxing)
│   │   ├── 📁 safety_guardian/ # Emergency detection
│   │   ├── 📁 wellness_coach/  # Health education
│   │   ├── 📁 speech_to_text/  # Voice input processing
│   │   └── 📁 text_to_speech/  # Voice synthesis
│   └── 📁 aws/                 # AWS service clients
├── 📁 frontend/                # Live2D web interface
├── 📁 infrastructure/          # CloudFormation templates
├── 📁 tests/                   # Comprehensive test suite
├── 📁 scripts/                 # Deployment and utility scripts
└── 📁 docs/                    # Documentation
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt
npm install  # For frontend dependencies

# Set up local environment
cp infrastructure/config.env.template infrastructure/config.env
# Edit config.env with your settings

# Run local tests
python -m pytest tests/
python tests/test_framework.py

# Run integration tests
python run_final_integration_test.py --environment dev
```

### Adding New Agents

1. **Create Lambda function**:
   ```bash
   mkdir src/lambda/my_new_agent
   cp src/lambda/wellness_coach/handler.py src/lambda/my_new_agent/
   # Customize the handler for your agent
   ```

2. **Update agent router**:
   ```python
   # In src/lambda/agent_router/handler.py
   def route_message(message, context):
       if "my_condition" in message.lower():
           return "my_new_agent"
   ```

3. **Deploy**:
   ```bash
   cd src/lambda/my_new_agent
   python deploy.py --environment dev
   ```

## 🧪 Testing

### Automated Testing Suite

```bash
# Run all tests
./scripts/run_final_tests.sh --environment dev

# Run specific test categories
python run_final_integration_test.py --environment dev --cost-analysis

# Test individual agents
curl -X POST https://your-api-url/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I have a headache", "user_id": "test_user"}'
```

### Test Coverage
- ✅ **Unit Tests**: Individual function testing
- ✅ **Integration Tests**: End-to-end workflows
- ✅ **Performance Tests**: Response time and concurrency
- ✅ **Security Tests**: Authentication and authorization
- ✅ **Cost Tests**: Budget compliance validation
- ✅ **Accessibility Tests**: Multi-language and disability support

## 🔒 Security & Privacy

### Data Protection
- **Encryption at Rest**: All data encrypted in DynamoDB and S3
- **Encryption in Transit**: HTTPS/TLS for all communications
- **Access Control**: IAM roles with least-privilege principles
- **Data Retention**: Automatic cleanup of old conversations
- **Audit Logging**: CloudTrail for all API calls

### Privacy Features
- **Anonymous Mode**: No personal data required
- **Data Minimization**: Only essential data collected
- **User Control**: Users can delete their conversation history
- **Compliance**: Designed for healthcare data regulations

### Security Best Practices
- Regular security updates and patches
- Vulnerability scanning and monitoring
- Secure API key management (AWS Parameter Store)
- Network security with VPC (optional)

## 🌍 Internationalization

### Supported Languages
- **English (en-US)**: Full support with American medical terminology
- **Traditional Chinese (zh-HK)**: Hong Kong healthcare context

### Adding New Languages

1. **Update language configuration**:
   ```javascript
   // In frontend/config/aws-config.js
   supportedLanguages: ['en-US', 'zh-HK', 'your-language']
   ```

2. **Add language-specific prompts**:
   ```python
   # In src/lambda/agent_router/handler.py
   LANGUAGE_PROMPTS = {
       'your-language': 'Your healthcare prompt in the target language'
   }
   ```

3. **Configure speech services**:
   ```python
   # Add voice configuration for new language
   VOICE_CONFIG = {
       'your-language': {
           'voice_id': 'YourLanguageVoice',
           'engine': 'neural'
       }
   }
   ```

## 📈 Monitoring & Analytics

### Built-in Monitoring
- **Real-time Metrics**: Response times, error rates, usage patterns
- **Cost Tracking**: Daily/monthly spend with trend analysis
- **Health Checks**: Automated system health monitoring
- **User Analytics**: Conversation patterns and agent effectiveness

### Dashboards
- **CloudWatch Dashboard**: AWS service metrics
- **Cost Dashboard**: Spending analysis and projections
- **Usage Dashboard**: User engagement and agent performance

### Alerts
- **Cost Alerts**: Email when spending exceeds thresholds
- **Error Alerts**: Immediate notification of system issues
- **Performance Alerts**: Response time degradation warnings

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Development Setup
```bash
# Fork the repository
git clone https://github.com/your-username/healthcare-ai-live2d.git
cd healthcare_ai_live2d_unified

# Create development branch
git checkout -b feature/your-feature-name

# Set up development environment
python setup_aws_deployment.py --environment dev
```

### Contribution Guidelines
1. **Code Style**: Follow PEP 8 for Python, ESLint for JavaScript
2. **Testing**: Add tests for new features
3. **Documentation**: Update README and inline docs
4. **Security**: Follow security best practices
5. **Performance**: Consider cost and performance impact

### Pull Request Process
1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite: `./scripts/run_final_tests.sh`
4. Update documentation
5. Submit pull request with detailed description

## 📚 Documentation

### Quick Links
- 🚀 **[Quick Start Guide](QUICK_START_AWS.md)** - Get running in 5 minutes
- 🏗️ **[Detailed Deployment Guide](README_DEPLOYMENT.md)** - Complete setup instructions
- 🧪 **[Testing Guide](tests/README_FINAL_TESTING.md)** - Comprehensive testing documentation
- 💰 **[Cost Optimization Guide](OPTIMIZATION_README.md)** - Reduce your AWS costs

### API Documentation
- **Chat API**: `POST /chat` - Send messages to healthcare agents
- **Speech API**: `POST /speech` - Convert speech to text and text to speech
- **Upload API**: `POST /upload` - Upload files for analysis
- **Health API**: `GET /health` - System health check

### Agent Documentation
- **[Agent Router](src/lambda/agent_router/README.md)** - Message routing logic
- **[Illness Monitor](src/lambda/illness_monitor/README.md)** - Health symptom analysis
- **[Mental Health](src/lambda/mental_health/README.md)** - Emotional support
- **[Safety Guardian](src/lambda/safety_guardian/README.md)** - Emergency detection
- **[Wellness Coach](src/lambda/wellness_coach/README.md)** - Health education

## 🆘 Support

### Getting Help
1. **📖 Check Documentation**: Start with the guides above
2. **🐛 Search Issues**: Look for existing solutions
3. **💬 Ask Questions**: Create a new issue with details
4. **📧 Contact Support**: For urgent issues

### Common Issues
- **Deployment Failures**: Check AWS permissions and service limits
- **High Costs**: Review cost optimization guide
- **Performance Issues**: Check CloudWatch metrics
- **Agent Responses**: Verify Bedrock model configuration

### Troubleshooting Commands
```bash
# Check deployment status
aws cloudformation describe-stacks --stack-name healthcare-ai-prod

# View recent logs
aws logs tail /aws/lambda/healthcare-ai-prod-agent-router --follow

# Test API endpoints
python run_final_integration_test.py --environment prod --verbose

# Analyze costs
python scripts/cost_analysis.py --environment prod --output cost_report.json
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Live2D**: For the amazing avatar technology
- **AWS**: For the robust cloud infrastructure
- **Anthropic**: For the Claude AI models via Bedrock
- **Hong Kong Healthcare System**: For inspiration and requirements
- **Open Source Community**: For tools and libraries used

## 🔮 Roadmap

### Upcoming Features
- 🎯 **Advanced Analytics**: Detailed health insights and trends
- 🔗 **EHR Integration**: Connect with electronic health records
- 📱 **Mobile App**: Native iOS and Android applications
- 🤖 **More Agents**: Specialized agents for specific conditions
- 🌐 **More Languages**: Simplified Chinese, Japanese, Korean
- 🏥 **Hospital Integration**: Direct connection to healthcare providers

### Version History
- **v1.0.0** (Current): Initial release with 4 healthcare agents
- **v0.9.0**: Beta release with Live2D integration
- **v0.8.0**: Alpha release with basic chat functionality

---

## 🚀 Ready to Deploy?

Get your Healthcare AI system running on AWS in minutes:

```bash
git clone https://github.com/your-username/healthcare-ai-live2d.git
cd healthcare_ai_live2d_unified
python setup_aws_deployment.py
./quick_deploy.sh
```

**Questions?** Check out our [Quick Start Guide](QUICK_START_AWS.md) or [create an issue](https://github.com/your-username/healthcare-ai-live2d/issues).

---

<div align="center">

**Built with ❤️ for Healthcare**

[🌟 Star this repo](https://github.com/your-username/healthcare-ai-live2d) • [🐛 Report Bug](https://github.com/your-username/healthcare-ai-live2d/issues) • [💡 Request Feature](https://github.com/your-username/healthcare-ai-live2d/issues)

</div>