#!/bin/bash
# scripts/setup_db.sh

echo "🗄️  Setting up database..."

# Load environment variables
set -a
source .env
set +a

# Create database if not exists
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'adspower_db'" | grep -q 1 || psql -U postgres -c "CREATE DATABASE adspower_db"

# Create user if not exists
psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname = 'adspower'" | grep -q 1 || psql -U postgres -c "CREATE USER adspower WITH PASSWORD 'password'"

# Grant privileges
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE adspower_db TO adspower"

echo "✅ Database setup complete!"