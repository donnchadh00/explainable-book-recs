#!/usr/bin/env bash
set -e

echo "Starting development environment..."

echo "Starting Docker DB container..."
docker compose up -d db

cd backend/

if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "Warning: backend/.env not found."
fi

if pgrep -f "uvicorn app.main:app" > /dev/null; then
  echo "FastAPI backend is already running."
else
  echo "Starting FastAPI backend..."
  nohup poetry run uvicorn app.main:app --reload > backend.log 2>&1 &
  echo "Backend running (logs: backend/backend.log)"
fi

cd ../frontend

if [ -f .env.local ]; then
  export $(grep -v '^#' .env.local | xargs)
else
  echo "Warning: frontend/.env.local not found."
fi

if pgrep -f "npm run dev" > /dev/null; then
  echo "Next.js frontend is already running."
else
  echo "Starting Next.js frontend..."
  nohup npm run dev > frontend.log 2>&1 &
  echo "Frontend running (logs: frontend/frontend.log)"
fi

cd ..

echo ""
echo "All services started."
echo "Backend → http://localhost:8000"
echo "Frontend → http://localhost:3000"
