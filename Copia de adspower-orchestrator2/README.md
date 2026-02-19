# 🚀 AdsPower Orchestrator - Sistema de Orquestación Distribuida

Sistema backend completo para gestión distribuida de perfiles AdsPower con automatización paralela, gestión de proxies y monitoreo de salud.

## 🎯 Características

- **Gestión de Computadoras**: Control de múltiples instancias de AdsPower en diferentes máquinas
- **Pool de Proxies**: Gestión inteligente de proxies SOAX (Mobile + Residential) con health checks
- **Perfiles Distribuidos**: Creación y gestión de perfiles con asignación automática de recursos
- **Automatización Paralela**: 
  - Búsquedas sincronizadas en Google
  - Navegación paralela a múltiples URLs
  - Sistema de barreras para sincronización perfecta
- **Health Monitoring**: Monitoreo automático de computers y proxies
- **Backup Automático**: Sistema de backup programado de base de datos
- **API REST**: Endpoints documentados con Swagger/OpenAPI
- **CLI Tools**: Scripts de línea de comandos para operaciones comunes
- **Arquitectura SOLID**: Código limpio y mantenible

## 📋 Requisitos

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (opcional)

## 🛠️ Instalación

### Opción 1: Docker (Recomendado)
```bash
# Clonar repositorio
git clone <repo-url>
cd adspower-orchestrator

# Copiar y configurar .env
cp .env.example .env
# Editar .env con tus credenciales

# Iniciar con Docker Compose
cd docker
docker-compose up -d

# Ver logs
docker-compose logs -f api
```

La API estará disponible en: http://localhost:8000
Documentación Swagger: http://localhost:8000/docs

### Opción 2: Manual
```bash
# Crear virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editar .env con tus credenciales

# Crear base de datos PostgreSQL
createdb adspower_db

# Inicializar migraciones
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Iniciar Redis
redis-server

# Iniciar API
uvicorn app.main:app --reload

# En otra terminal: Iniciar Celery Worker
celery -A app.tasks worker --loglevel=info

# En otra terminal: Iniciar Celery Beat
celery -A app.tasks beat --loglevel=info
```

## 🔧 Configuración

### Variables de Entorno (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/adspower_db
DATABASE_SYNC_URL=postgresql://user:pass@localhost:5432/adspower_db

# Redis
REDIS_URL=redis://localhost:6379/0

# API
SECRET_KEY=your-secret-key-here
API_HOST=0.0.0.0
API_PORT=8000

# AdsPower (default values)
ADSPOWER_DEFAULT_API_URL=http://local.adspower.net:50325
ADSPOWER_DEFAULT_API_KEY=your-api-key

# SOAX Proxies
SOAX_USERNAME=package-XXXXX
SOAX_PASSWORD=your-password
SOAX_HOST=proxy.soax.com
SOAX_PORT=5000

# Monitoring
HEALTH_CHECK_INTERVAL=300

# Backup
BACKUP_ENABLED=true
BACKUP_INTERVAL=86400
BACKUP_PATH=/backups
```

## 📚 Uso

### API REST

#### 1. Registrar Computer
```bash
curl -X POST "http://localhost:8000/api/v1/computers/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop-Omar",
    "hostname": "laptop-omar",
    "ip_address": "192.168.1.100",
    "adspower_api_url": "http://local.adspower.net:50325",
    "adspower_api_key": "your-api-key",
    "max_profiles": 50
  }'
```

#### 2. Crear Proxy
```bash
curl -X POST "http://localhost:8000/api/v1/proxies/" \
  -H "Content-Type: application/json" \
  -d '{
    "proxy_type": "mobile",
    "host": "proxy.soax.com",
    "port": 5000,
    "country": "ec",
    "city": "quito"
  }'
```

#### 3. Crear Profile
```bash
curl -X POST "http://localhost:8000/api/v1/profiles/" \
  -H "Content-Type: application/json" \
  -d '{
    "computer_id": 1,
    "name": "Profile Test",
    "proxy_type": "mobile",
    "proxy_country": "ec",
    "proxy_city": "quito",
    "auto_warmup": true,
    "warmup_duration_minutes": 20
  }'
```

#### 4. Búsqueda Paralela
```bash
curl -X POST "http://localhost:8000/api/v1/automation/parallel-search" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_ids": [1, 2, 3, 4, 5],
    "search_query": "mejores smartphones 2025",
    "max_parallel": 5
  }'
```

#### 5. Navegación Paralela
```bash
curl -X POST "http://localhost:8000/api/v1/automation/parallel-navigation" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_ids": [1, 2, 3],
    "urls": ["facebook.com", "youtube.com", "twitter.com"],
    "stay_duration_min": 10,
    "stay_duration_max": 30,
    "max_parallel": 3
  }'
```

### CLI Tools
```bash
# Crear profile
python cli/create_profile.py create --computer-id 1 --auto-warmup

# Listar profiles
python cli/create_profile.py list --limit 20

# Health check computers
python cli/health_check.py computers

# Health check proxies
python cli/health_check.py proxies --limit 50

# Creación masiva
python cli/bulk_operations.py create-profiles 10 --computer-id 1 --auto-warmup
```

## 📊 Endpoints API

### Computers
- `POST /api/v1/computers/` - Crear computer
- `GET /api/v1/computers/` - Listar computers
- `GET /api/v1/computers/{id}` - Obtener computer
- `PATCH /api/v1/computers/{id}` - Actualizar computer
- `DELETE /api/v1/computers/{id}` - Eliminar computer
- `POST /api/v1/computers/{id}/health-check` - Health check
- `GET /api/v1/computers/stats/summary` - Estadísticas

### Proxies
- `POST /api/v1/proxies/` - Crear proxy
- `GET /api/v1/proxies/` - Listar proxies
- `GET /api/v1/proxies/{id}` - Obtener proxy
- `PATCH /api/v1/proxies/{id}` - Actualizar proxy
- `DELETE /api/v1/proxies/{id}` - Eliminar proxy
- `POST /api/v1/proxies/{id}/test` - Probar proxy
- `POST /api/v1/proxies/health-check/batch` - Health check batch
- `GET /api/v1/proxies/stats/summary` - Estadísticas

### Profiles
- `POST /api/v1/profiles/` - Crear profile
- `POST /api/v1/profiles/bulk` - Crear múltiples profiles
- `GET /api/v1/profiles/` - Listar profiles
- `GET /api/v1/profiles/{id}` - Obtener profile
- `PATCH /api/v1/profiles/{id}` - Actualizar profile
- `DELETE /api/v1/profiles/{id}` - Eliminar profile
- `POST /api/v1/profiles/{id}/warmup` - Iniciar warmup
- `GET /api/v1/profiles/stats/summary` - Estadísticas

### Automation
- `POST /api/v1/automation/parallel-search` - Búsqueda paralela
- `POST /api/v1/automation/parallel-navigation` - Navegación paralela
- `GET /api/v1/automation/task/{task_id}` - Estado de tarea

## 🏗️ Arquitectura
```
┌─────────────────┐
│   FastAPI API   │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Service │ (Business Logic)
    └────┬────┘
         │
  ┌──────┴──────┐
  │ Repository  │ (Data Access)
  └──────┬──────┘
         │
   ┌─────┴─────┐
   │ Database  │ (PostgreSQL)
   └───────────┘

┌──────────────┐     ┌─────────────┐
│ Celery Tasks │────▶│    Redis    │
└──────────────┘     └─────────────┘

┌─────────────────────────────────┐
│  External Integrations          │
│  • AdsPower API (multi-computer)│
│  • SOAX Proxies                 │
│  • Selenium WebDriver           │
└─────────────────────────────────┘
```

## 🧪 Testing
```bash
# Ejecutar tests
pytest

# Con coverage
pytest --cov=app tests/

# Tests específicos
pytest tests/test_services/test_profile_service.py
```

## 📝 Notas de Desarrollo

### Principios SOLID Aplicados

1. **Single Responsibility**: Cada clase tiene una única responsabilidad
2. **Open/Closed**: Extensible sin modificar código existente
3. **Liskov Substitution**: Repositories intercambiables
4. **Interface Segregation**: Interfaces específicas por dominio
5. **Dependency Inversion**: Inyección de dependencias

### Estructura de Capas

- **API Layer**: FastAPI endpoints
- **Service Layer**: Lógica de negocio
- **Repository Layer**: Acceso a datos
- **Model Layer**: SQLAlchemy models
- **Integration Layer**: Clientes externos

## 🔐 Seguridad

- JWT Authentication (preparado para implementar)
- API Key validation para AdsPower
- Encriptación de credenciales sensibles
- Rate limiting (preparado)
- CORS configurado

## 📈 Monitoreo

- Health checks automáticos cada 5 minutos
- Logs estructurados con Loguru
- Métricas de Prometheus (preparado)
- Alertas por Slack/Discord (preparado)

## 🤝 Contribución

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial.

## 👥 Contacto

Omar - omar@conectastudio.com

---

**Nota**: Este es un sistema backend profesional diseñado para producción. Asegúrate de configurar correctamente todas las variables de entorno y credenciales antes de desplegar.
