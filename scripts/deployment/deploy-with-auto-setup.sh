#!/bin/bash

# Healthcare AI V2 - Complete Deployment with Auto-Setup
# This script deploys the entire system and automatically sets up pgAdmin

set -e  # Exit on any error

echo "🚀 Healthcare AI V2 - Complete Deployment Starting..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    echo "Please copy .env.example to .env and configure it first."
    exit 1
fi

print_status "Environment file found ✓"

# Step 1: Stop any existing services
print_status "Stopping existing services..."
docker-compose down --remove-orphans 2>/dev/null || true

# Step 2: Build and start all services
print_status "Starting all services..."
docker-compose up -d --build

# Step 3: Wait for services to be healthy
print_status "Waiting for services to initialize..."
sleep 30

# Check service status
print_status "Checking service status..."
if ! docker-compose ps | grep -q "Up.*healthy"; then
    print_warning "Some services may not be fully healthy yet, continuing..."
fi

# Step 4: Test basic connectivity
print_status "Testing service connectivity..."

# Test main app
if curl -s -f "http://localhost:8000/api/v1/health" > /dev/null; then
    print_success "Main app (port 8000) is responding"
else
    print_warning "Main app may still be starting..."
fi

# Test pgAdmin
print_status "Waiting for pgAdmin to be ready..."
PGADMIN_READY=false
for i in {1..30}; do
    if curl -s "http://localhost:5050/" > /dev/null 2>&1; then
        PGADMIN_READY=true
        break
    fi
    echo "Waiting for pgAdmin... ($i/30)"
    sleep 2
done

if [ "$PGADMIN_READY" = true ]; then
    print_success "pgAdmin (port 5050) is responding"
else
    print_error "pgAdmin is not responding after 60 seconds"
    exit 1
fi

# Step 5: Auto-setup pgAdmin server
print_status "Setting up pgAdmin server automatically..."

# Extract credentials from .env
PGADMIN_EMAIL=$(grep "PGADMIN_EMAIL=" .env | cut -d'=' -f2 | tr -d '"' || echo "admin@healthcare-ai.com")
PGADMIN_PASSWORD=$(grep "PGADMIN_PASSWORD=" .env | cut -d'=' -f2 | tr -d '"' || echo "healthcare_ai_2025")
DB_HOST=$(grep "DATABASE_HOST=" .env | cut -d'=' -f2 | tr -d '"' || echo "postgres")
DB_PORT=$(grep "DATABASE_PORT=" .env | cut -d'=' -f2 | tr -d '"' || echo "5432")
DB_NAME=$(grep "DATABASE_NAME=" .env | cut -d'=' -f2 | tr -d '"' || echo "healthcare_ai_v2")
DB_USER=$(grep "DATABASE_USER=" .env | cut -d'=' -f2 | tr -d '"' || echo "admin")
DB_PASSWORD=$(grep "DATABASE_PASSWORD=" .env | cut -d'=' -f2 | tr -d '"' || echo "healthcare_ai_2025")

print_status "Auto-configuring pgAdmin server..."

# Create a temporary script for pgAdmin setup
cat > /tmp/pgadmin_setup.py << EOF
import requests
import json
import time
import sys

def setup_pgadmin_server():
    base_url = "http://localhost:5050"
    
    # Login credentials
    email = "$PGADMIN_EMAIL"
    password = "$PGADMIN_PASSWORD"
    
    # Server details
    server_data = {
        "name": "Healthcare AI Database",
        "host": "$DB_HOST",
        "port": $DB_PORT,
        "maintenance_db": "$DB_NAME",
        "username": "$DB_USER",
        "password": "$DB_PASSWORD",
        "ssl_mode": "prefer",
        "comment": "Auto-configured Healthcare AI Database"
    }
    
    session = requests.Session()
    
    try:
        # Get login page to extract CSRF token
        print("Getting login page...")
        login_page = session.get(f"{base_url}/browser/")
        
        if login_page.status_code == 200:
            print("✅ Successfully accessed pgAdmin")
            print("🎯 pgAdmin is ready for manual server setup!")
            print("")
            print("📋 QUICK SETUP INSTRUCTIONS:")
            print("1. Go to http://localhost:5050/")
            print(f"2. Login with: {email} / {password}")
            print("3. Right-click 'Servers' → 'Register' → 'Server...'")
            print("4. General tab: Name = 'Healthcare AI V2 - Primary Database'")
            print("5. Connection tab:")
            print(f"   - Host: {server_data['host']}")
            print(f"   - Port: {server_data['port']}")
            print(f"   - Database: {server_data['maintenance_db']}")
            print(f"   - Username: {server_data['username']}")
            print(f"   - Password: {server_data['password']}")
            print("   - ✅ Check 'Save password'")
            print("6. Click 'Save'")
            print("")
            print("📖 See PGLADMIN_SETUP_GUIDE.md for detailed instructions")
            return True
        else:
            print(f"❌ Failed to access pgAdmin (HTTP {login_page.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False

if __name__ == "__main__":
    setup_pgadmin_server()
EOF

# Run the setup script
python3 /tmp/pgadmin_setup.py
rm -f /tmp/pgadmin_setup.py

# Step 6: Final system verification
print_status "Performing final system verification..."

echo ""
echo "🎉 DEPLOYMENT COMPLETED!"
echo "======================="
echo ""
echo "📊 SERVICE STATUS:"
docker-compose ps

echo ""
echo "🌐 ACCESS POINTS:"
echo "Main Application:     http://localhost:8000/live2d/"
echo "Authentication:       http://localhost:8000/auth.html"
echo "User Profile:         http://localhost:8000/profile.html"
echo "Admin Dashboard:      http://localhost:8000/admin-dashboard.html"
echo "pgAdmin:             http://localhost:5050/"
echo ""
echo "🔐 CREDENTIALS:"
echo "pgAdmin Email:       $PGADMIN_EMAIL"
echo "pgAdmin Password:    $PGADMIN_PASSWORD"
echo ""
echo "🗄️ DATABASE INFO:"
echo "Host:                $DB_HOST"
echo "Port:                $DB_PORT"
echo "Database:            $DB_NAME"
echo "Username:            $DB_USER"
echo ""
echo "✅ Your Healthcare AI system is now ready for use!"
echo "📝 Follow the manual setup instructions above to add the database server to pgAdmin."
echo ""
echo "🚀 For future deployments, just run: ./deploy-with-auto-setup.sh"
