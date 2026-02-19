# ========================================
# agent/install.sh
#!/bin/bash
# Install AdsPower Agent

echo "📦 Installing AdsPower Agent..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚙️  .env created from example. Please configure it!"
fi

# Create directories
mkdir -p logs
mkdir -p screenshots

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your configuration"
echo "  2. Run: ./start.sh"