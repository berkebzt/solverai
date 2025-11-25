# SolverAI Setup Guide

Complete guide to get SolverAI up and running with LLM integration.

## Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ (for local development)
- At least 8GB RAM (16GB recommended)
- 10GB free disk space (for Llama 3.1 model)

## Quick Start (Docker)

### 1. Start Services

```bash
# Option 1: Using the start script
./start.sh

# Option 2: Using Make
make up

# Option 3: Manual Docker Compose
docker-compose up -d
```

### 2. Download Llama 3.1 Model

This will download ~4.7GB model file:

```bash
make install-model

# Or manually:
docker exec -it solverai-ollama ollama pull llama3.1:8b
```

### 3. Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "services": {
#     "api": "running",
#     "ollama": "available",
#     "fallback": "none"
#   }
# }
```

### 4. Test the Chat API

```bash
# Simple test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Who are you?",
    "stream": false
  }'

# Or run the comprehensive test suite
python test_api.py
```

## Local Development (Without Docker)

### 1. Install PostgreSQL

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt install postgresql-16
sudo systemctl start postgresql

# Create database
createdb solverai
```

### 2. Install Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
```

### 3. Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama
ollama serve

# Pull model
ollama pull llama3.1:8b
```

### 4. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend/app
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy example env
cp .env .env.local

# Edit .env.local with your local settings:
POSTGRES_HOST=localhost
REDIS_HOST=localhost
OLLAMA_BASE_URL=http://localhost:11434
```

### 6. Run the API

```bash
cd backend/app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration Options

### LLM Configuration

#### Using Local Ollama Only

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OPENAI_API_KEY=  # Leave empty
```

#### Hybrid Mode (Local + Cloud Fallback)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OPENAI_API_KEY=sk-your-openai-key-here
```

The API will:
1. Try Ollama first (local)
2. Fall back to OpenAI if Ollama is unavailable

#### Cloud Only

```env
OLLAMA_BASE_URL=http://unreachable
OPENAI_API_KEY=sk-your-openai-key-here
```

### Other Models

You can use different Ollama models:

```bash
# Smaller, faster models
ollama pull llama3.1:3b      # 3B parameters
ollama pull phi3:mini        # Microsoft Phi-3

# Larger, more capable models
ollama pull llama3.1:70b     # 70B parameters (requires 40GB+ RAM)
ollama pull mixtral:8x7b     # Mixtral MoE

# Update .env
OLLAMA_MODEL=phi3:mini
```

## Testing

### API Testing

```bash
# Run test suite
python test_api.py

# Test specific endpoint
curl http://localhost:8000/health
curl http://localhost:8000/
```

### Database Testing

```bash
# Check database connection
docker exec -it solverai-postgres psql -U solverai -d solverai

# List tables
\dt

# View conversations
SELECT * FROM conversations;

# View messages
SELECT * FROM messages;
```

### View Logs

```bash
# All services
make logs

# Specific service
make logs-api
make logs-ollama

# Or with docker-compose
docker-compose logs -f api
docker-compose logs -f ollama
docker-compose logs -f postgres
```

## API Endpoints

### Chat Endpoints

**POST /chat** - Send a message
```json
{
  "message": "Your message here",
  "conversation_id": "optional-uuid",
  "stream": false
}
```

**GET /conversations** - List all conversations

**GET /conversations/{id}** - Get specific conversation

**DELETE /conversations/{id}** - Delete conversation

### System Endpoints

**GET /** - API information

**GET /health** - Health check

**GET /docs** - Interactive API documentation (Swagger)

**GET /redoc** - Alternative API documentation

## Troubleshooting

### Ollama Not Available

```bash
# Check if Ollama is running
docker exec solverai-ollama ollama list

# Restart Ollama
docker restart solverai-ollama

# Pull model again
docker exec -it solverai-ollama ollama pull llama3.1:8b
```

### Database Connection Issues

```bash
# Check PostgreSQL
docker exec solverai-postgres pg_isready -U solverai

# View PostgreSQL logs
docker logs solverai-postgres

# Recreate database
docker-compose down -v
docker-compose up -d
```

### API Not Responding

```bash
# Check API logs
docker logs solverai-api

# Restart API
docker restart solverai-api

# Rebuild if needed
docker-compose build api
docker-compose up -d
```

### Import Errors

```bash
# Rebuild with fresh dependencies
docker-compose build --no-cache api
docker-compose up -d

# Or for local development
pip install -r backend/app/requirements.txt --force-reinstall
```

## Performance Tuning

### For Better Performance

```yaml
# docker-compose.yml - Uncomment GPU support for Ollama
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### For Lower Memory Usage

Use smaller models:
```bash
ollama pull llama3.1:3b
# Update OLLAMA_MODEL=llama3.1:3b in .env
```

### For Production

```bash
# Update .env
DEBUG=False
POSTGRES_PASSWORD=<strong-password-here>

# Use production-grade ASGI server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Next Steps

Now that LLM integration is working:

1. ✅ **LLM Integration** - Complete!
2. 🔄 **RAG System** - Add document chat capability
3. 🔄 **Voice I/O** - Add Whisper and TTS
4. 🔄 **Agent System** - Add LangGraph agents
5. 🔄 **Frontend** - Build web interface

See [README.md](README.md) for the full roadmap.
