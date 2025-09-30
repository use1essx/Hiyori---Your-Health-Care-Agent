# 🏗️ **Healthcare AI Live2D - Project Structure**

> **Updated:** September 28, 2025  
> **Status:** ✅ Cleaned and Demo-Ready  
> **Version:** Healthcare AI V2 + Live2D Unified

---

## 📁 **PROJECT DIRECTORY STRUCTURE**

### **🔧 Core Configuration Files**
- **`.env`** - Environment variables (API keys, database settings)
- **`docker-compose.yml`** - Docker services configuration
- **`Dockerfile`** - Container build instructions
- **`requirements.txt`** - Python dependencies
- **`pyproject.toml`** - Python project configuration
- **`env.example`** - Environment template file

### **📚 Documentation**
- **`README.md`** - Main project documentation
- **`DEMO_USERS.md`** - Complete demo user guide and credentials
- **`PROJECT_STRUCTURE.md`** - This file - project organization guide

### **🚀 Startup Scripts**
- **`start-all.sh`** - ⭐ **MAIN STARTUP SCRIPT** - Full system startup with user creation
- **`quick-setup.sh`** - Quick restart without rebuild
- **`setup-pgadmin.sh`** - pgAdmin specific setup

### **💾 Data & Database**
- **`data/`** - Docker volume data (postgres, redis, pgadmin)
- **`pgadmin/`** - pgAdmin configuration files
  - `servers.json` - Auto-configured database connection
  - `pgpass` - Database credentials for auto-login
- **`sql/`** - Database schema and migration files
- **`migrations/`** - Database migration scripts

### **🧠 Source Code**
- **`src/`** - Main application source code
  - **`src/web/live2d/frontend/`** - Live2D web interface
    - `index.html` - Main Live2D chat interface
    - `profile.html` - User profile management
    - `admin-dashboard.html` - Admin control panel
    - `auth.html` - User authentication
  - **`src/web/api/v1/`** - REST API endpoints
  - **`src/agents/`** - AI agent system
  - **`src/ai/`** - AI service and model management
  - **`src/database/`** - Database models and connections
  - **`src/core/`** - Core utilities and security

### **📋 System Files**
- **`logs/`** - Application logs (agents, security, main)
- **`config/`** - System configuration files
- **`docker/`** - Docker-related configuration
- **`scripts/`** - Utility and maintenance scripts
- **`prompts/`** - AI agent prompts and templates
- **`docs/`** - Technical documentation and examples

---

## 🎯 **QUICK START GUIDE**

### **🚀 Full System Startup:**
```bash
./start-all.sh
```
**What it does:**
- Stops and cleans existing containers
- Rebuilds and starts all services
- Creates demo users with health profiles
- Opens web interfaces automatically

### **⚡ Quick Restart:**
```bash
./quick-setup.sh
```
**What it does:**
- Restarts services without rebuild
- Faster for minor changes

### **🔧 pgAdmin Setup:**
```bash
./setup-pgadmin.sh
```
**What it does:**
- Restarts pgAdmin with auto-configuration
- Useful if database connection issues occur

---

## 🌐 **ACCESS POINTS**

### **Main Interfaces:**
- **Live2D Chat Interface:** `http://localhost:8000/live2d/`
- **User Authentication:** `http://localhost:8000/auth.html`
- **User Profile Management:** `http://localhost:8000/profile.html`
- **Admin Dashboard:** `http://localhost:8000/admin-dashboard.html`

### **Database Management:**
- **pgAdmin Interface:** `http://localhost:5050`
- **Auto-login configured** (username: admin, password: healthcare_ai_2025)

---

## 👥 **DEMO USERS**

| User Type | Username | Password | Purpose |
|-----------|----------|----------|---------|
| **Teenager** | `teen_demo` | `Demo2025!` | Mental health, anxiety scenarios |
| **Elderly** | `elder_demo` | `Demo2025!` | Chronic disease management |
| **Administrator** | `admin_demo` | `Admin2025!` | System administration |

*Full user details in `DEMO_USERS.md`*

---

## 🧹 **CLEANED UP FILES**

### **✅ Files Removed:**
- `test-auth-debug.html` - Temporary auth testing
- `test-profile-flow.html` - Profile testing tool
- `clear-auth-state.html` - Auth state clearing tool
- `quick-login.html` - Development login shortcut
- `start_live2d_system.sh` - Duplicate startup script
- `start_unified_system.sh` - Old startup script
- `start.py` - Legacy startup file
- `test-pgadmin-setup.sh` - pgAdmin testing script
- `tools/` - Redundant chat tools (replaced by main interface)
- `backups/` - Empty backup directory
- `uploads/` - Empty uploads directory
- All `.tmp`, `.bak`, `.old`, `~` temporary files
- Python `__pycache__` directories and `.pyc` files

### **✅ Files Kept:**
- **Essential configuration** (docker-compose, env files)
- **Documentation** (README, demo guides)
- **Source code** (complete application)
- **Database files** (migrations, schema)
- **Startup scripts** (main ones only)
- **Live2D models** (Haru and Hiyori)

---

## 🎬 **DEMO PREPARATION**

### **System Status:**
- ✅ **Live2D Interface:** Working with Hiyori and Haru models
- ✅ **AI Agents:** Personalized responses based on user profiles
- ✅ **Database:** PostgreSQL with demo users and health profiles
- ✅ **Authentication:** User login/registration with role-based access
- ✅ **Admin Dashboard:** Complete system management interface
- ✅ **Project Structure:** Clean and organized for demonstration

### **Demo Flow Ready:**
1. **System Startup** → `./start-all.sh`
2. **User Demos** → Login as teen/elder users, show personalized AI
3. **Admin Demo** → Login as admin, show system management
4. **Database Demo** → Show pgAdmin with user data
5. **Technical Demo** → Clean project structure and documentation

---

## 🔧 **MAINTENANCE**

### **Log Management:**
- Logs are in `logs/` directory
- Main log: `healthcare_ai.log`
- Security events: `security.log`
- Agent interactions: `agents.log`

### **Database Management:**
- Access via pgAdmin at `http://localhost:5050`
- Direct PostgreSQL access: `docker-compose exec postgres psql -U admin -d healthcare_ai_v2`
- Backup/restore scripts in `scripts/` directory

### **Updates:**
- Modify code in `src/` directory
- Restart with `./quick-setup.sh` for code changes
- Use `./start-all.sh` for configuration changes

---

## 📊 **SYSTEM ARCHITECTURE**

```
Healthcare AI Live2D System
├── 🌐 Web Interface (Live2D + Chat)
├── 🧠 AI Agent System (Multi-agent routing)
├── 💾 PostgreSQL Database (User data + conversations)
├── 🔄 Redis Cache (Session management)
├── 🛠️ pgAdmin (Database management)
└── 🔐 Authentication System (JWT + role-based)
```

---

**🎯 The project is now clean, organized, and ready for professional demonstration!**

**📧 For questions or issues, refer to the detailed documentation in the `docs/` directory.**
