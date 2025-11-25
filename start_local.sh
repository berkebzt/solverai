#!/bin/bash

# Kill running processes
echo "Stopping existing services..."
pkill -f uvicorn
pkill -f "vite"

# Start Backend
echo "Starting Backend..."
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
export LLM_MOCK_MODE="false"
# Use venv python explicitly
./venv/bin/python run.py > backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > backend.pid
echo "Backend started (PID: $BACKEND_PID)"

# Start Frontend
echo "Starting Frontend..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "🚀 SolverAI is running locally!"
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:5173"
echo ""
echo "Logs are being written to backend.log and frontend.log"
