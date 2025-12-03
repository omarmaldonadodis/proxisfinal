#!/bin/bash
# scripts/run_migrations.sh

echo "🔄 Running database migrations..."

# Activate virtual environment
source venv/bin/activate

# Run migrations
alembic upgrade head

echo "✅ Migrations complete!"