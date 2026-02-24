#!/bin/bash

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check prerequisites


if ! command_exists npm; then
  echo "Error: Node.js/npm is not installed."
  exit 1
fi

if ! command_exists python; then
  echo "Error: Python is not installed."
  exit 1
fi

echo "🚀 Starting YTBrain Infrastructure (In-Memory Mode)..."

echo "⏳ Waiting for services to be ready..."
sleep 5

echo "🐍 Starting Backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
fi

# Activate venv based on OS (Windows git bash vs others)
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

pip install -r requirements.txt
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

echo "⚛️ Starting Frontend..."
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ YTBrain is running!"
echo "Frontend: http://localhost:5173"
echo "Backend: http://localhost:8000"
echo "Press Ctrl+C to stop both servers."

# Trap SIGINT to kill background processes
trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT

wait
