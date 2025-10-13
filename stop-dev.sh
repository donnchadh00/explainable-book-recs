#!/usr/bin/env bash
set -e

echo "Stopping development environment..."

if pgrep -f "uvicorn app.main:app" > /dev/null; then
  echo "Stopping FastAPI backend..."
  pkill -f "uvicorn app.main:app"
else
  echo "FastAPI backend not running."
fi

if pgrep -f "npm run dev" > /dev/null; then
  echo "Stopping Next.js frontend..."
  pkill -f "npm run dev"
else
  echo "Next.js frontend not running."
fi

if docker ps --format '{{.Names}}' | grep -q 'db'; then
  echo "Stopping Docker DB container..."
  docker compose down
else
  echo "No active Docker DB container found."
fi

read -p "Clear backend/frontend logs? (y/N): " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  rm -f backend/backend.log frontend/frontend.log
  echo "Logs cleared."
else
  echo "Logs kept."
fi

echo ""
echo "All services stopped cleanly."
