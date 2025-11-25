# SolverAI - Open-Source AI Companion

A privacy-focused AI companion that you can run locally or in the cloud. Built with modern AI tools and designed for maximum flexibility.

## Features

- 🤖 **Local LLM Support** - Run Llama 3.1 (8B) locally via Ollama
- 📚 **Document Chat (RAG)** - Chat with your documents using FAISS vector database
- 🧠 **Persistent Memory** - Conversation history stored in PostgreSQL
- 🎤 **Voice Input** - Speech-to-text with OpenAI Whisper
- 🔊 **Voice Output** - Text-to-speech capabilities
- 🛠️ **AI Agents** - Modular agents for search, code execution, and calendar
- 🔒 **Privacy First** - Run completely offline if desired
- 🐳 **Docker Ready** - Easy deployment with Docker Compose

## Tech Stack

- **Backend**: FastAPI
- **LLM**: Llama 3.1 (8B) via Ollama / OpenAI compatible
- **Agent Framework**: LangGraph
- **Vector Database**: FAISS
- **Speech-to-Text**: OpenAI Whisper
- **Database**: PostgreSQL
- **Cache**: Redis
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 8GB RAM (16GB recommended for local LLM)
- GPU optional but recommended for faster inference

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd solverai
   ```

2. **Configure environment variables**
   ```bash
   cp .env .env.local
   # Edit .env with your preferences
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Pull Llama 3.1 model**
   ```bash
   docker exec -it solverai-ollama ollama pull llama3.1:8b
   ```

5. **Verify installation**
   ```bash
   curl http://localhost:8000/health
   ```

## Usage

### API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /chat` - Send a chat message
- `GET /conversations/{id}` - Retrieve conversation history
- `POST /upload` - Upload documents for RAG
- `POST /voice/transcribe` - Transcribe audio to text
- `POST /voice/speak` - Convert text to speech

### Chat API Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "conversation_id": "optional-id"
  }'
```

### Upload Document Example

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf"
```

## Configuration

### Environment Variables

Key environment variables in [.env](.env):

- `DEBUG` - Enable debug mode
- `OLLAMA_MODEL` - LLM model to use (default: llama3.1:8b)
- `POSTGRES_PASSWORD` - Database password (change in production!)
- `OPENAI_API_KEY` - Optional: for cloud fallback
- `ENABLE_*_AGENT` - Enable/disable specific agents

### Local vs Cloud

**Run completely local:**
```bash
# Use Ollama for LLM, local Whisper for voice
# No external API calls required
```

**Hybrid mode:**
```bash
# Set OPENAI_API_KEY for cloud fallback
# Falls back to OpenAI if local model unavailable
```

## Project Structure

```
solverai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration management
│   │   ├── models/              # Database models
│   │   ├── services/            # Business logic
│   │   │   ├── llm.py          # LLM integration
│   │   │   ├── rag.py          # RAG pipeline
│   │   │   ├── voice.py        # Voice I/O
│   │   │   └── agents/         # AI agents
│   │   └── requirements.txt    # Python dependencies
│   └── documents/               # Document storage
├── data/
│   ├── conversations/           # Conversation logs
│   └── vector_db/              # FAISS vector store
├── docker-compose.yml          # Docker services
└── .env                        # Environment configuration
```

## Development

### Local Development (without Docker)

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   cd backend/app
   pip install -r requirements.txt
   ```

3. **Run services separately**
   ```bash
   # Terminal 1: PostgreSQL
   docker run -p 5432:5432 -e POSTGRES_PASSWORD=solverai postgres:16-alpine

   # Terminal 2: Redis
   docker run -p 6379:6379 redis:7-alpine

   # Terminal 3: Ollama
   docker run -p 11434:11434 ollama/ollama

   # Terminal 4: FastAPI
   cd backend/app
   uvicorn main:app --reload
   ```

### Running Tests

```bash
cd backend/app
pytest
```

## Roadmap

- [x] Basic FastAPI setup
- [x] Docker configuration
- [ ] LLM integration (Ollama + OpenAI)
- [ ] RAG pipeline with FAISS
- [ ] Document processing
- [ ] Voice input (Whisper)
- [ ] Voice output (TTS)
- [ ] LangGraph agent system
- [ ] Search agent
- [ ] Code execution agent
- [ ] Calendar agent
- [ ] Web frontend
- [ ] Mobile app

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - See LICENSE file for details

## Acknowledgments

- [Ollama](https://ollama.ai/) for local LLM runtime
- [LangChain](https://www.langchain.com/) & [LangGraph](https://github.com/langchain-ai/langgraph) for agent framework
- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [FAISS](https://github.com/facebookresearch/faiss) for vector similarity search
