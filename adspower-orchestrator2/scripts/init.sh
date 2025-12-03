#!/bin/bash
# scripts/init_project.sh

echo "🚀 Inicializando proyecto AdsPower Orchestrator..."

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Crear directorios necesarios
echo -e "${YELLOW}📁 Creando estructura de directorios...${NC}"
mkdir -p logs
mkdir -p backups
mkdir -p profiles/profile_data
mkdir -p profiles/warmup_reports
mkdir -p alembic/versions

# 2. Verificar Python
echo -e "${YELLOW}🐍 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instala Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} encontrado${NC}"

# 3. Crear virtual environment
echo -e "${YELLOW}📦 Creando virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# 4. Actualizar pip
echo -e "${YELLOW}⬆️  Actualizando pip...${NC}"
pip install --upgrade pip

# 5. Instalar dependencias
echo -e "${YELLOW}📚 Instalando dependencias...${NC}"
pip install -r requirements.txt

# 6. Verificar .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚙️  Creando .env desde .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  IMPORTANTE: Edita .env con tus credenciales${NC}"
else
    echo -e "${GREEN}✓ .env ya existe${NC}"
fi

# 7. Verificar PostgreSQL
echo -e "${YELLOW}🗄️  Verificando PostgreSQL...${NC}"
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL client no encontrado. Instálalo para continuar."
else
    echo -e "${GREEN}✓ PostgreSQL client encontrado${NC}"
fi

# 8. Verificar Redis
echo -e "${YELLOW}📮 Verificando Redis...${NC}"
if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  Redis no encontrado. Instálalo para continuar."
else
    echo -e "${GREEN}✓ Redis encontrado${NC}"
fi

echo ""
echo -e "${GREEN}✅ Inicialización completada!${NC}"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Editar .env con tus credenciales"
echo "   2. Crear base de datos: createdb adspower_db"
echo "   3. Ejecutar migraciones: alembic upgrade head"
echo "   4. Iniciar Redis: redis-server"
echo "   5. Iniciar API: uvicorn app.main:app --reload"
echo "   6. Iniciar Celery Worker: celery -A app.tasks worker --loglevel=info"
echo ""
echo "🐳 O usar Docker:"
echo "   cd docker && docker-compose up -d"