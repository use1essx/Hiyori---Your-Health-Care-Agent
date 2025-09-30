# 🗄️ pgAdmin Setup Guide for Healthcare AI V2

## 🎯 **SIMPLE 2-STEP SETUP**

Since pgAdmin's auto-import requires the user to log in first, here's the guaranteed method:

### **Step 1: First Login**
1. Go to **http://localhost:5050/**
2. Login with:
   - **Email:** `admin@healthcare-ai.com`
   - **Password:** `healthcare_ai_2025`

### **Step 2: Add Database Server**
1. **Right-click** on "**Servers**" in the left panel
2. Select "**Register**" → "**Server...**"
3. Fill in the details:

#### **General Tab:**
- **Name:** `Healthcare AI V2 - Primary Database`

#### **Connection Tab:**
- **Host name/address:** `postgres`
- **Port:** `5432`
- **Maintenance database:** `healthcare_ai_v2`
- **Username:** `admin`
- **Password:** `healthcare_ai_2025`
- ✅ **Check "Save password"**

4. Click "**Save**"

---

## 🎉 **What You'll See After Setup:**

- **Healthcare AI V2 - Primary Database** under "Servers"
- **Expand it** to access:
  - **Databases** → **healthcare_ai_v2**
  - **Schemas** → **public**
  - **Tables** with your data:
    - `users` (teen_demo, elder_demo, admin_demo)
    - `conversations`
    - `conversation_sessions`
    - `user_permissions`
    - `hk_healthcare_facilities`
    - And many more!

---

## 🚀 **For Future Deployments:**

This setup process only needs to be done once per deployment. After that, the server configuration is saved in pgAdmin.

### **Complete Deployment Script:**
```bash
# Deploy everything
./deploy-with-auto-setup.sh

# Then manually add the server in pgAdmin (one-time setup)
# Follow the steps above
```

---

## 🔧 **Alternative: Multiple Database Views**

You can also add additional server connections for different purposes:

### **Analytics Server (Same Database, Different Name):**
- **Name:** `Healthcare AI V2 - Analytics`
- **Same connection details as above**
- **Purpose:** Separate view for reporting and analytics

### **Read-Only User (Future Enhancement):**
- Create a read-only database user
- Add separate server connection for read-only access

---

## 📊 **Database Structure Overview:**

Once connected, you'll have access to:

### **Core Tables:**
- `users` - User accounts and profiles
- `conversations` - AI chat conversations  
- `conversation_sessions` - Chat sessions
- `conversation_messages` - Individual messages

### **Healthcare Data:**
- `hk_healthcare_facilities` - Hong Kong healthcare facilities
- `hk_healthcare_updates` - Healthcare news and updates

### **System Tables:**
- `user_permissions` - User access control
- `audit_logs` - System audit trail
- `agent_performance` - AI agent metrics

---

## ✅ **Verification:**

After setup, verify by:
1. **Expanding the server** in pgAdmin
2. **Browsing to Tables** under public schema
3. **Running a test query:** `SELECT COUNT(*) FROM users;`
4. **Should see your demo users** (teen_demo, elder_demo, admin_demo)

---

**Your Healthcare AI database is now fully accessible through pgAdmin!** 🌟
