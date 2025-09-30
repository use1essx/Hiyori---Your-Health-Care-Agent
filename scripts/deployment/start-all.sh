#!/bin/bash
# Healthcare AI V2 - Complete System Startup Script

clear
echo "🚀 Healthcare AI V2 - Starting All Services"
echo "============================================="
echo ""

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Clean up any orphaned containers
echo "🧹 Cleaning up..."
docker-compose down --remove-orphans
docker system prune -f --volumes

echo ""
echo "📦 Building and starting all services..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for services to initialize..."

# Wait for PostgreSQL
echo "  📊 Starting PostgreSQL..."
sleep 5
until docker-compose exec -T postgres pg_isready -U admin -d healthcare_ai_v2 >/dev/null 2>&1; do
    echo "     Waiting for PostgreSQL..."
    sleep 2
done
echo "  ✅ PostgreSQL ready!"

# Wait for Redis
echo "  🔴 Starting Redis..."
until docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; do
    echo "     Waiting for Redis..."
    sleep 2
done
echo "  ✅ Redis ready!"

# Wait for Healthcare AI Backend
echo "  🤖 Starting Healthcare AI..."
sleep 10
until curl -s http://localhost:8000/health >/dev/null 2>&1; do
    echo "     Waiting for Healthcare AI backend..."
    sleep 3
done
echo "  ✅ Healthcare AI ready!"

# Wait for pgAdmin
echo "  📊 Starting pgAdmin..."
sleep 5
until curl -s http://localhost:5050 >/dev/null 2>&1; do
    echo "     Waiting for pgAdmin..."
    sleep 2
done
echo "  ✅ pgAdmin ready!"

echo ""
echo "🎯 Creating test user..."
curl -s "http://localhost:8000/api/v1/auth/register" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email": "test@demo.com", "username": "testuser", "password": "Demo1234", "full_name": "Test User"}' \
  >/dev/null 2>&1 && echo "  ✅ Test user created!" || echo "  ℹ️  Test user already exists"

echo ""
echo "🌟 ALL SERVICES READY!"
echo "============================================="
echo "🤖 Live2D Chat:          http://localhost:8000/live2d/"
echo "👤 User Login/Register:   http://localhost:8000/auth.html"
echo "📊 Database Admin:        http://localhost:5050"
echo "🔧 API Health Check:      http://localhost:8000/health"
echo ""
echo "📋 Login Credentials:"
echo "  pgAdmin: admin@healthcare-ai.com / healthcare_ai_2025"
echo "  Test User: test@demo.com / Demo1234"
echo ""
echo "🎉 Ready to go! Healthcare AI Database is auto-configured in pgAdmin!"
echo "============================================="

# Open URLs in browser (optional)
echo ""
read -p "🌐 Open services in browser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🌐 Opening services..."
    
    # Try different commands to open URLs
    if command -v xdg-open > /dev/null; then
        xdg-open "http://localhost:8000/live2d/" 2>/dev/null &
        xdg-open "http://localhost:5050" 2>/dev/null &
    elif command -v open > /dev/null; then
        open "http://localhost:8000/live2d/" 2>/dev/null &
        open "http://localhost:5050" 2>/dev/null &
    else
        echo "📋 Please manually open these URLs:"
        echo "   http://localhost:8000/live2d/"
        echo "   http://localhost:5050"
    fi
fi

echo ""
echo "✨ Enjoy your Healthcare AI system!"
