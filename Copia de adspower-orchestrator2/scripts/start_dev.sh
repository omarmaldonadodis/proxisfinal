#!/bin/bash
# scripts/start_dev.sh

echo "🚀 Starting development environment..."

# Activate virtual environment
source venv/bin/activate

# Start services in background
redis-server --daemonize yes

# Start Celery worker
celery -A app.tasks worker --loglevel=info &
CELERY_PID=$!

# Start Celery beat
celery -A app.tasks beat --loglevel=info &
BEAT_PID=$!

# Start API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Cleanup on exit
trap "kill $CELERY_PID $BEAT_PID; redis-cli shutdown" EXIT