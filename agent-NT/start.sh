# ========================================
# agent/start.sh
#!/bin/bash
# Start AdsPower Agent

echo "🤖 Starting AdsPower Agent..."

# Activate virtual environment
source venv/bin/activate

# Check .env
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Copy .env.example to .env and configure it"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Start agent
python -m agent.main

