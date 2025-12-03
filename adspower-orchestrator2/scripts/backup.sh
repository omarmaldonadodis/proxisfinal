#!/bin/bash
# scripts/backup.sh

echo "🗄️  Creating database backup..."

# Activate virtual environment
source venv/bin/activate

# Run backup CLI
python cli/backup.py create

echo "✅ Backup complete!"