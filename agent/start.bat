
# ========================================
# agent/start.bat (Windows)
@echo off
echo Starting AdsPower Agent...

if not exist venv\ (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

if not exist .env (
    echo .env file not found!
    echo Copy .env.example to .env and configure it
    pause
    exit
)

if not exist logs\ mkdir logs

python -m agent.main
