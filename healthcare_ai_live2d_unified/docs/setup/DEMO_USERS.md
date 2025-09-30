# 🎭 **HEALTHCARE AI - DEMO USERS GUIDE**

> **Created:** September 28, 2025  
> **System:** Healthcare AI Live2D Unified Demo  
> **Purpose:** Complete demo user profiles for system demonstration

---

## 🔐 **AUTHENTICATION CREDENTIALS**

### **Quick Login URLs:**
- **Main Interface:** `http://localhost:8000/live2d/`
- **Authentication:** `http://localhost:8000/auth.html`
- **User Profiles:** `http://localhost:8000/profile.html`
- **Quick Login Tool:** `http://localhost:8000/quick-login.html`

---

## 👤 **DEMO USER #1: TEENAGER**

### **Account Information:**
- **Username:** `teen_demo`
- **Email:** `teen@demo.com`
- **Password:** `Demo2025!`
- **Full Name:** Alex Chen
- **Role:** User
- **Organization:** St. Mary High School
- **Department:** Student Health

### **Health Profile:**
- **Age:** 17 years old
- **Gender:** Male
- **Height:** 165 cm
- **Weight:** 58 kg
- **Blood Type:** A+
- **BMI:** 21.3 (Normal)

### **Medical Information:**
- **Chronic Conditions:** 
  - Anxiety
  - Social Anxiety Disorder (custom condition)
- **Current Medications:**
  - Sertraline 50mg (for anxiety)
- **Allergies:** 
  - Peanuts
  - Shellfish
- **Lifestyle:**
  - Smoking: Never
  - Alcohol: Never
  - Exercise: 2-3 times per week

### **Emergency Contact:**
- **Name:** Jennifer Chen
- **Phone:** +852 9876 5432
- **Relationship:** Mother

### **Health Goals:**
> "Managing anxiety and stress from school. Want to improve sleep quality and build confidence for university applications. Dealing with social situations better."

### **Demo Scenarios:**
- School stress and anxiety management
- Social situation concerns
- Sleep quality issues
- University preparation stress
- Teen mental health support

---

## 👵 **DEMO USER #2: ELDERLY PERSON**

### **Account Information:**
- **Username:** `elder_demo`
- **Email:** `elder@demo.com`
- **Password:** `Demo2025!`
- **Full Name:** Margaret Wong
- **Role:** User
- **Organization:** Golden Age Care Center
- **Department:** Senior Care

### **Health Profile:**
- **Age:** 72 years old
- **Gender:** Female
- **Height:** 158 cm
- **Weight:** 65 kg
- **Blood Type:** O+
- **BMI:** 26.0 (Slightly overweight)

### **Medical Information:**
- **Chronic Conditions:**
  - Diabetes (Type 2)
  - Hypertension (High Blood Pressure)
  - Arthritis
  - Osteoporosis
  - Mild Cognitive Impairment (custom condition)
  - Cataracts (custom condition)

- **Current Medications:**
  - Metformin 500mg twice daily (diabetes)
  - Lisinopril 10mg daily (blood pressure)
  - Calcium + Vitamin D daily (bone health)
  - Ibuprofen as needed (pain management)

- **Allergies:**
  - Penicillin
  - Codeine

- **Lifestyle:**
  - Smoking: Former smoker (quit 15 years ago)
  - Alcohol: Occasionally
  - Exercise: Daily walks

### **Emergency Contact:**
- **Name:** David Wong
- **Phone:** +852 9123 4567
- **Relationship:** Son

### **Health Goals:**
> "Maintaining independence and managing diabetes levels. Want to stay active and prevent falls. Managing joint pain from arthritis while staying mobile."

### **Demo Scenarios:**
- Diabetes management and monitoring
- Fall prevention and mobility
- Medication management
- Joint pain and arthritis care
- Senior independence support
- Memory concerns

---

## 👩‍⚕️ **DEMO USER #3: ADMINISTRATOR**

### **Account Information:**
- **Username:** `admin_demo`
- **Email:** `admin@demo.com`
- **Password:** `Admin2025!`
- **Full Name:** Dr. Sarah Li
- **Role:** Admin (Full system access)
- **Organization:** Healthcare AI Demo System
- **Department:** System Administration
- **License Number:** HK-MD-2024-001

### **Admin Features:**
- **Dashboard Access:** Dedicated admin dashboard at `/admin-dashboard.html`
- **System Management:** Full access to system testing and administration tools
- **User Management:** Can view and manage demo users
- **Testing Tools:** Built-in AI testing, database management, and system monitoring
- **No Health Profile:** Admin users don't have health profiles - they're purely administrative

### **Admin Dashboard Features:**
- 🔧 **System Status Monitoring**
- 👥 **Demo User Management** 
- 🧠 **AI Testing Tools**
- 🗄️ **Database Administration**
- 🎭 **Live2D System Management**
- 📋 **System Logs & Monitoring**

### **Demo Scenarios:**
- System administration and monitoring
- Testing AI responses across different user types
- Database management and user oversight
- Live2D system testing and resource management
- Comprehensive system health checks

---

## 🎯 **DEMO SCENARIOS BY USER TYPE**

### **Teenager (Alex Chen):**
1. **Anxiety Management:** "I have a big exam coming up and I'm feeling really anxious"
2. **Social Concerns:** "I'm worried about making friends at university"
3. **Sleep Issues:** "I can't sleep well because I keep thinking about school"
4. **Academic Stress:** "The pressure to get good grades is overwhelming"
5. **Identity Questions:** "I'm struggling with my identity and how others see me"

### **Elderly (Margaret Wong):**
1. **Diabetes Concerns:** "My blood sugar has been high lately, what should I do?"
2. **Fall Prevention:** "I'm worried about falling and want to stay safe at home"
3. **Medication Questions:** "I sometimes forget to take my medications"
4. **Memory Concerns:** "I've been more forgetful lately and it worries me"
5. **Joint Pain:** "My arthritis is acting up and it's hard to move around"

### **Administrator (Dr. Sarah Li):**
1. **Work Stress:** "I'm dealing with high stress at work as a healthcare administrator"
2. **Migraine Management:** "I need strategies to prevent stress-induced migraines"
3. **System Testing:** Full admin access to test all system features
4. **Professional Wellness:** "How can I maintain my health while managing others' care?"
5. **System Administration:** Access to admin panels and user management

---

## 🔧 **TECHNICAL INFORMATION**

### **Database Structure:**
- **Users Table:** All 3 users verified and active
- **Health Profiles:** Stored as JSONB in PostgreSQL
- **Roles:** teen_demo and elder_demo are 'user', admin_demo is 'admin'
- **Organization Data:** Realistic institutional affiliations

### **Authentication Status:**
- ✅ All users are verified (`is_verified = true`)
- ✅ Admin user has admin privileges (`is_admin = true`)
- ✅ All passwords follow security requirements
- ✅ All users can log in immediately

### **Health Profile Integration:**
- ✅ Comprehensive health data for AI context
- ✅ Age-appropriate conditions and medications
- ✅ Realistic emergency contacts
- ✅ Cultural context (Hong Kong phone numbers)

---

## 🎬 **DEMO FLOW SUGGESTIONS**

### **1. Teen Demo Flow:**
```
1. Login as teen_demo
2. Show profile page with anxiety and school stress
3. Chat: "I'm feeling anxious about my upcoming exams"
4. Demonstrate age-appropriate responses
5. Show emergency contact integration
```

### **2. Elder Demo Flow:**
```
1. Login as elder_demo  
2. Show comprehensive chronic conditions
3. Chat: "I forgot to take my diabetes medication this morning"
4. Demonstrate senior-focused care responses
5. Show medication management features
```

### **3. Admin Demo Flow:**
```
1. Login as admin_demo
2. Show admin access and system features
3. Demonstrate professional user interface
4. Show system administration capabilities
5. Test cross-user functionality
```

---

## 🚀 **QUICK START COMMANDS**

### **Reset Demo Users (if needed):**
```bash
# Clear all users
docker-compose exec postgres psql -U admin -d healthcare_ai_v2 -c "TRUNCATE TABLE users RESTART IDENTITY CASCADE;"

# Recreate users (run the registration commands from setup)
```

### **Verify Users:**
```bash
# Check all users
docker-compose exec postgres psql -U admin -d healthcare_ai_v2 -c "SELECT id, username, email, full_name, role, is_verified, is_admin FROM users;"

# Check health profiles
docker-compose exec postgres psql -U admin -d healthcare_ai_v2 -c "SELECT username, health_profile->'age' as age, health_profile->'chronic_conditions' as conditions FROM users;"
```

### **Login Testing:**
```bash
# Test teen login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email_or_username": "teen_demo", "password": "Demo2025!"}'

# Test elder login  
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email_or_username": "elder_demo", "password": "Demo2025!"}'

# Test admin login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email_or_username": "admin_demo", "password": "Admin2025!"}'
```

---

## 📊 **USER COMPARISON TABLE**

| Feature | Teen (Alex) | Elder (Margaret) | Admin (Dr. Sarah) |
|---------|-------------|------------------|-------------------|
| **Age** | 17 | 72 | 42 |
| **Primary Concerns** | Anxiety, School | Diabetes, Independence | Work Stress, Migraines |
| **Medications** | 1 (Anxiety) | 4 (Multiple chronic) | 2 (Migraine, Vitamin) |
| **Chronic Conditions** | 2 | 6 | 1 |
| **Exercise Level** | Moderate | Light | High |
| **Tech Comfort** | High | Low | High |
| **System Role** | Standard User | Standard User | Administrator |

---

## 🎨 **PERSONALIZATION FEATURES**

### **AI Context Awareness:**
- Each user's health profile is automatically included in AI conversations
- Age-appropriate language and recommendations
- Condition-specific health advice
- Cultural context (Hong Kong healthcare system)

### **Profile Integration:**
- Live2D avatar responds based on user profile
- Personalized health goal tracking
- Emergency contact information readily available
- Medication reminders and interactions

---

## 🔒 **SECURITY NOTES**

⚠️ **DEMO ONLY:** These are demonstration accounts with fictional health data  
🔐 **Passwords:** Use strong passwords in production environments  
📋 **Data:** All health information is simulated for demo purposes  
🏥 **Compliance:** Real deployments should follow healthcare data regulations  

---

## 📞 **SUPPORT INFORMATION**

**System URL:** `http://localhost:8000`  
**pgAdmin:** `http://localhost:5050`  
**Database:** PostgreSQL on port 5432  
**Created:** September 28, 2025  
**Status:** ✅ Ready for Demo

---

*This documentation provides everything needed to demonstrate the Healthcare AI system with realistic user scenarios and comprehensive health profiles.*
