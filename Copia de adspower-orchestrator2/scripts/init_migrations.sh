#!/bin/bash
# scripts/init_migrations.sh

echo "🗄️  Initializing database migrations..."

# Create alembic directory structure
alembic init alembic

# Generate initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head

echo "✅ Migrations initialized successfully!"