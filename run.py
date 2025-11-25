import uvicorn
import os
import sys

if __name__ == "__main__":
    # Set default environment variables for local development
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("LLM_MOCK_MODE", "true")
    
    # Add backend/app to python path
    sys.path.append(os.path.join(os.path.dirname(__file__), "backend", "app"))
    
    print("Starting SolverAI Server...")
    print(f"Database: {os.environ['DATABASE_URL']}")
    print(f"Mock Mode: {os.environ['LLM_MOCK_MODE']}")
    print("URL: http://127.0.0.1:8000")
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir="backend/app"
    )
