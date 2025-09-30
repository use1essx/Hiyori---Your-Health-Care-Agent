#!/bin/bash
# Healthcare AI V2 - Complete Quick Setup Script

echo "🚀 Healthcare AI V2 - Quick Setup Starting..."
echo "================================================"

# Start all services
echo "📦 Starting all Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check service health
echo "🔍 Checking service health..."
echo "  PostgreSQL: $(docker-compose exec -T postgres pg_isready -U admin -d healthcare_ai_v2 || echo 'Not ready')"
echo "  Redis: $(docker-compose exec -T redis redis-cli ping || echo 'Not ready')"
echo "  Healthcare AI: $(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo 'Not ready')"
echo "  pgAdmin: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:5050 | grep -q '200\|302' && echo 'Ready' || echo 'Not ready')"

echo ""
echo "✅ Setup Complete! Access your services:"
echo "================================================"
echo "🤖 Live2D Chat:        http://localhost:8000/live2d/"
echo "👤 User Authentication: http://localhost:8000/auth.html"
echo "📊 Database Admin:      http://localhost:5050"
echo "   └─ Email: admin@healthcare-ai.com"
echo "   └─ Password: healthcare_ai_2025"
echo "🔧 API Health:          http://localhost:8000/health"
echo ""
echo "📋 Test Credentials:"
echo "   Email: demo@healthcare.com"
echo "   Username: demouser"
echo "   Password: Demo123#"
echo ""
echo "🎯 The Healthcare AI Database is auto-configured in pgAdmin!"
echo "================================================"
