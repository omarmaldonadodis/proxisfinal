#!/bin/bash
# scripts/init_complete.sh - Inicialización completa del sistema

echo "🚀 AdsPower Orchestrator - Inicialización Completa"
echo "=================================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Verificar Python
echo -e "${YELLOW}🐍 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no encontrado. Instala Python 3.11+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python encontrado${NC}"

# 2. Crear virtual environment
echo -e "${YELLOW}📦 Creando virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment creado${NC}"

# 3. Instalar dependencias
echo -e "${YELLOW}📚 Instalando dependencias...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# 4. Crear .env si no existe
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚙️  Creando .env desde .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  IMPORTANTE: Edita .env con tus credenciales${NC}"
else
    echo -e "${GREEN}✓ .env ya existe${NC}"
fi

# 5. Crear directorios
echo -e "${YELLOW}📁 Creando estructura de directorios...${NC}"
mkdir -p logs
mkdir -p backups
mkdir -p profiles/profile_data
mkdir -p profiles/warmup_reports
mkdir -p alembic/versions
mkdir -p app/websocket
echo -e "${GREEN}✓ Directorios creados${NC}"

# 6. Crear __init__.py faltantes
echo -e "${YELLOW}📝 Creando archivos __init__.py...${NC}"
touch app/__init__.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch app/repositories/__init__.py
touch app/integrations/__init__.py
touch app/core/__init__.py
touch app/tasks/__init__.py
touch app/websocket/__init__.py
touch app/utils/__init__.py
touch cli/__init__.py
touch tests/__init__.py
echo -e "${GREEN}✓ Archivos __init__.py creados${NC}"

# 7. Verificar PostgreSQL
echo -e "${YELLOW}🗄️  Verificando PostgreSQL...${NC}"
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL client encontrado${NC}"
else
    echo -e "${RED}⚠️  PostgreSQL client no encontrado${NC}"
fi

# 8. Verificar Redis
echo -e "${YELLOW}📮 Verificando Redis...${NC}"
if command -v redis-cli &> /dev/null; then
    echo -e "${GREEN}✓ Redis encontrado${NC}"
else
    echo -e "${RED}⚠️  Redis no encontrado${NC}"
fi

# 9. Inicializar base de datos
echo -e "${YELLOW}🗄️  Inicializando base de datos...${NC}"
read -p "¿Deseas crear la base de datos ahora? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Crear base de datos
    psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'adspower_db'" | grep -q 1 || \
        psql -U postgres -c "CREATE DATABASE adspower_db"
    
    psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname = 'adspower'" | grep -q 1 || \
        psql -U postgres -c "CREATE USER adspower WITH PASSWORD 'password'"
    
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE adspower_db TO adspower"
    
    echo -e "${GREEN}✓ Base de datos creada${NC}"
    
    # Ejecutar migraciones
    echo -e "${YELLOW}🔄 Ejecutando migraciones...${NC}"
    alembic upgrade head
    echo -e "${GREEN}✓ Migraciones completadas${NC}"
else
    echo -e "${YELLOW}⚠️  Recuerda crear la base de datos manualmente${NC}"
fi

echo ""
echo -e "${GREEN}✅ Inicialización completada!${NC}"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Editar .env con tus credenciales"
echo "   2. Iniciar Redis: redis-server"
echo "   3. Iniciar API: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "   4. Iniciar Celery Worker: celery -A app.tasks worker --loglevel=info"
echo "   5. Abrir docs: http://localhost:8000/docs"
echo ""
echo "🌐 URLs importantes:"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo "   - Health: http://localhost:8000/health"
echo ""