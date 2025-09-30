# 🏥🎭 Healthcare AI V2 + Live2D Unified System

**Complete Healthcare AI Assistant with Interactive Live2D Avatars**

> A comprehensive, all-in-one healthcare AI system featuring specialized medical agents, interactive 3D avatars, and real-time Hong Kong healthcare data integration.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

## 🎯 System Overview

This unified system combines:
- **🏥 Healthcare AI V2 Backend** - Advanced multi-agent healthcare assistant
- **🎭 Live2D Avatar Frontend** - Interactive 3D healthcare assistants
- **🔊 Speech Integration** - Voice input/output with local STT/TTS
- **🇭🇰 Hong Kong Integration** - Real-time local healthcare data
- **🔐 Enterprise Security** - Healthcare-grade data protection

## 🤖 AI Healthcare Agents

### 1. 🏥 慧心助手 (Illness Monitor)
- **Avatar**: Hiyori (Professional, caring)
- **Specialization**: Physical health monitoring, chronic disease management
- **Target Users**: Elderly, chronic patients, general health concerns
- **Languages**: Traditional Chinese, English

### 2. 🌟 小星星 (Mental Health Support)
- **Avatar**: Haru (Gentle, supportive)
- **Specialization**: Mental health support, emotional wellness
- **Target Users**: Children, teenagers, mental health concerns
- **Style**: VTuber-inspired for youth engagement

### 3. 🚨 Safety Guardian (Emergency Response)
- **Avatar**: Mao (Alert, authoritative)
- **Specialization**: Emergency detection, crisis intervention
- **Target Users**: All users in emergency situations
- **Response**: Immediate escalation to emergency services

### 4. 💪 Wellness Coach (Health Education)
- **Avatar**: Natori (Energetic, motivational)
- **Specialization**: Preventive care, lifestyle guidance
- **Target Users**: General wellness and prevention
- **Focus**: Education and prevention strategies

## 🚀 Quick Start

### One-Command Startup
```bash
# Clone and start the complete system
git clone <your-repository>
cd healthcare_ai_live2d_unified
./scripts/deployment/start-all.sh
```

### Manual Setup
```bash
# 1. Copy environment configuration
cp env.example .env
# Edit .env with your API keys

# 2. Install Python dependencies (if running outside Docker)
pip install -r requirements.txt

# 3. Start the unified system
docker-compose up -d

# 4. Check system health
curl http://localhost:8000/health
curl http://localhost:8080/health
```

### 📦 Dependency Management
- **All Python dependencies** are managed through the root `requirements.txt`
- **No duplicate requirement files** - single source of truth
- **Modern Python tooling** available via `pyproject.toml`

## 🌐 Access Points

| Interface | URL | Purpose |
|-----------|-----|---------|
| **🎭 Live2D Chat** | http://localhost:8080 | Main user interface with avatars |
| **🏥 Healthcare API** | http://localhost:8000 | Backend API endpoints |
| **📚 API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **⚙️ Admin Panel** | http://localhost:8000/admin | System administration |
| **🗄️ pgAdmin** | http://localhost:5050 | Database management |

## 📁 Organized Project Structure

```
healthcare_ai_live2d_unified/
├── 🚀 ROOT FILES
│   ├── README.md                    # Main project documentation
│   ├── docker-compose.yml           # Complete system configuration
│   ├── Dockerfile                   # Healthcare AI backend
│   ├── requirements.txt             # Python dependencies (canonical)
│   ├── pyproject.toml               # Modern Python project config
│   └── env.example                  # Environment template
│
├── 📚 DOCUMENTATION
│   ├── docs/setup/                  # Setup and configuration guides
│   │   ├── DEMO_USERS.md           # Demo user credentials and profiles
│   │   ├── PGADMIN_SETUP_GUIDE.md  # Database admin setup
│   │   └── PROJECT_STRUCTURE.md    # Detailed project structure
│   ├── docs/cleanup/                # Repository cleanup documentation
│   │   ├── CLEANUP_PLAN.md         # Cleanup analysis and planning
│   │   ├── CHANGELOG.md            # Repository cleanup changes
│   │   ├── DEPRECATIONS.md         # Migration guide
│   │   └── POSTCHECK.md            # Post-cleanup verification
│   └── docs/guides/                 # Technical guides
│
├── 🔧 SCRIPTS
│   ├── scripts/deployment/          # Deployment and startup scripts
│   │   ├── start-all.sh            # Main system startup
│   │   ├── quick-setup.sh          # Quick restart script
│   │   └── deploy-with-auto-setup.sh # Complete deployment
│   └── scripts/maintenance/         # Maintenance scripts
│       └── restore-demo.sh         # Demo environment restoration
│
├── 🧠 SOURCE CODE
│   ├── src/                         # Main application source
│   │   ├── main.py                 # FastAPI application
│   │   ├── agents/                 # Multi-agent AI system
│   │   ├── web/live2d/frontend/    # Live2D web interface
│   │   ├── web/api/                # REST API endpoints
│   │   ├── web/auth/               # Authentication system
│   │   ├── database/               # Database layer
│   │   └── core/                   # Core utilities
│
├── ⚙️ CONFIGURATION
│   ├── config/                     # System configuration
│   ├── migrations/                 # Database migrations
│   ├── sql/                        # Database schemas
│   └── prompts/                    # AI agent prompts
│
└── 📊 RUNTIME DATA
    ├── logs/                       # Application logs
    └── tools/                      # Utility tools
```

## 🔧 Configuration

### Required API Keys
1. **OpenRouter API Key** - Get from [openrouter.ai](https://openrouter.ai/keys)
2. Add to your `.env` file: `OPENROUTER_API_KEY=your_key_here`

### Environment Variables
All configuration is done through the `.env` file. See `env.example` for complete options.

Key settings:
```bash
# API Keys
OPENROUTER_API_KEY=your_openrouter_key

# Ports
HEALTHCARE_AI_PORT=8000
LIVE2D_PORT=8080
PGADMIN_PORT=5050

# Features
ENABLE_LIVE2D=true
ENABLE_STT=false
ENABLE_ADMIN_INTERFACE=true
```

## 🧪 Testing

### Quick System Test
```bash
# Test Healthcare AI Backend
curl http://localhost:8000/health

# Test Live2D Frontend
curl http://localhost:8080/health

# Test Chat Integration
curl -X POST http://localhost:8080/live2d/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I have a headache"}'

# Test Chinese Language
curl -X POST http://localhost:8080/live2d/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "我頭痛", "language": "zh-HK"}'
```

### System Status
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f

# Monitor system health
watch -n 5 'curl -s http://localhost:8000/health && echo && curl -s http://localhost:8080/health'
```

## 🔒 Security Features

- **🔐 JWT Authentication** with refresh tokens
- **🛡️ Role-based Access Control** (User, Admin, Medical Reviewer)
- **⚡ Rate Limiting** to prevent API abuse
- **🔍 Audit Logging** for all user actions
- **🏥 Healthcare Data Encryption** in transit and at rest
- **🌐 CORS Protection** for web security
- **🔒 Input Validation** and sanitization

## 📱 Supported Features

### Healthcare AI Capabilities
- ✅ Multi-agent intelligent routing
- ✅ Traditional Chinese language support
- ✅ Hong Kong healthcare system integration
- ✅ Emergency detection and response
- ✅ Chronic disease management
- ✅ Mental health support
- ✅ Wellness coaching

### Live2D Avatar Features
- ✅ 4 specialized healthcare assistant models
- ✅ Emotional expressions based on conversation context
- ✅ Cultural gestures for Hong Kong users
- ✅ Voice interaction with STT/TTS
- ✅ Real-time avatar switching
- ✅ Background customization

### Integration Features
- ✅ Seamless backend-frontend communication
- ✅ WebSocket support for real-time chat
- ✅ User authentication across both systems
- ✅ Unified logging and monitoring
- ✅ Single Docker deployment

## 🚨 Troubleshooting

### Common Issues

**❌ "Services won't start"**
```bash
# Check Docker status
docker-compose ps

# Restart specific service
docker-compose restart healthcare_ai

# View service logs
docker-compose logs healthcare_ai
```

**❌ "Live2D avatars not loading"**
```bash
# Check Live2D service
curl http://localhost:8080/health

# Check model configuration
curl http://localhost:8080/live2d/models
```

**❌ "Database connection failed"**
```bash
# Check PostgreSQL
docker-compose exec postgres pg_isready -U admin

# Reset database
docker-compose down
docker volume rm healthcare_ai_live2d_unified_postgres_data
docker-compose up -d
```

**❌ "API key not working"**
```bash
# Check API key configuration
curl http://localhost:8000/api/v1/health/api-key-status

# Update .env file with valid OpenRouter API key
```

### Log Locations
- **Application Logs**: `logs/` directory
- **Docker Logs**: `docker-compose logs -f [service_name]`
- **Database Logs**: `docker-compose logs postgres`
- **Live2D Logs**: `docker-compose logs live2d_frontend`

## 📊 Monitoring

### Health Endpoints
- **Overall System**: `http://localhost:8080/health`
- **Healthcare AI**: `http://localhost:8000/health`
- **Live2D System**: `http://localhost:8080/live2d/health`
- **Database**: Check via pgAdmin or Docker logs

### Performance Monitoring
- **Admin Dashboard**: `http://localhost:8000/admin`
- **API Metrics**: `http://localhost:8000/docs`
- **Live2D Status**: `http://localhost:8080/live2d/admin/status`

## 🛠️ Development

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run in development mode
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest src/tests/
```

### Code Quality
```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

## 🌟 Key Features

### For End Users
- **Interactive Avatars** - 4 specialized healthcare assistants
- **Voice Interaction** - Speak naturally with the AI
- **Traditional Chinese** - Full support for Hong Kong users
- **Emergency Response** - Immediate help for urgent situations
- **Personalized Care** - Tailored advice based on user profile

### For Healthcare Providers
- **Professional Dashboard** - Monitor and manage the system
- **Data Analytics** - Track usage and effectiveness
- **Content Management** - Upload and manage medical documents
- **User Management** - Manage user accounts and permissions
- **Audit Trails** - Complete logging for compliance

### For Administrators
- **System Monitoring** - Real-time health and performance metrics
- **Database Management** - pgAdmin interface for data management
- **Security Monitoring** - Track and respond to security events
- **Configuration Management** - Easy system configuration
- **Backup & Recovery** - Automated backup and restore capabilities

## 🔮 Future Enhancements

- **📱 Mobile App** - Native iOS and Android applications
- **🌍 Multi-language** - Support for additional languages
- **🏥 EHR Integration** - Electronic Health Record connectivity
- **☁️ Cloud Deployment** - AWS/Azure production deployment
- **📊 Advanced Analytics** - ML-powered health insights
- **🔗 IoT Integration** - Health monitoring device connectivity

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

### Getting Help
1. **Check Health Endpoints** - Verify all services are running
2. **Review Logs** - Check application and Docker logs
3. **Test Integration** - Use provided test commands
4. **Documentation** - See organized guides in:
   - `docs/setup/` - Setup and configuration guides
   - `docs/cleanup/` - Repository cleanup documentation
   - `docs/guides/` - Technical guides and examples

### Emergency Contacts (Hong Kong)
- **Medical Emergency**: 999
- **Mental Health Crisis**: Samaritans (2896 0000)
- **Child Protection**: 2755 1122

---

**🎉 Ready to Get Started?**

Run `./scripts/deployment/start-all.sh` and visit `http://localhost:8000` to begin your healthcare AI journey!

---

*Healthcare AI V2 + Live2D Unified System - Bringing compassionate AI healthcare assistance to Hong Kong with interactive avatars* 🇭🇰💙