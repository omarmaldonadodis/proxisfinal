# ========================================
# agent/install.bat (Windows)
@echo off
echo Installing AdsPower Agent...

python -m venv venv
call venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

if not exist .env copy .env.example .env

if not exist logs\ mkdir logs
if not exist screenshots\ mkdir screenshots

echo Installation complete!
echo.
echo Next steps:
echo   1. Edit .env with your configuration
echo   2. Run: start.bat
pause