#!/bin/bash

echo "🚀 Starting SolverAI - AI Companion"
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Using default configuration."
fi

# Build and start services
echo "📦 Building Docker images..."
docker-compose build

echo ""
echo "🔄 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check if services are healthy
echo ""
echo "🔍 Checking service health..."

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API service is running"
else
    echo "❌ API service is not responding"
fi

if docker exec solverai-ollama ollama list > /dev/null 2>&1; then
    echo "✅ Ollama service is running"
else
    echo "❌ Ollama service is not responding"
fi

if docker exec solverai-postgres pg_isready -U solverai > /dev/null 2>&1; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL is not responding"
fi

echo ""
echo "=================================="
echo "🎉 SolverAI is ready!"
echo ""
echo "📍 API: http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "Next steps:"
echo "1. Download LLM model: make install-model"
echo "2. View logs: make logs"
echo "3. Stop services: make down"
echo ""
echo "For more commands: make help"
