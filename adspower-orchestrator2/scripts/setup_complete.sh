#!/bin/bash
# scripts/setup_complete.sh

echo "🚀 Setup completo de AdsPower Orchestrator"

# Source environment
set -a
source .env
set +a

# 1. Crear base de datos
echo "📊 Creando base de datos..."
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'adspower_db'" | grep -q 1 || \
    psql -U postgres -c "CREATE DATABASE adspower_db"

# 2. Crear usuario
echo "👤 Creando usuario..."
psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname = 'adspower'" | grep -q 1 || \
    psql -U postgres -c "CREATE USER adspower WITH PASSWORD 'password'"

# 3. Otorgar permisos
echo "🔐 Otorgando permisos..."
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE adspower_db TO adspower"

# 4. Ejecutar migraciones
echo "🔄 Ejecutando migraciones..."
source venv/bin/activate
alembic upgrade head

# 5. Crear base de datos de test
echo "🧪 Creando base de datos de test..."
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'adspower_test_db'" | grep -q 1 || \
    psql -U postgres -c "CREATE DATABASE adspower_test_db"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE adspower_test_db TO adspower"

echo "✅ Setup completo!"