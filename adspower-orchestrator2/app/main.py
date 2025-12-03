# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
import asyncio

from app.config import settings
from app.database import init_db
from app.api.v1 import router as api_v1_router

# Configurar logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    # Startup
    logger.info("=" * 60)
    logger.info("Starting AdsPower Orchestrator API...")
    logger.info(f"Version: {settings.APP_VERSION}")
    logger.info("=" * 60)
    
    await init_db()
    logger.info("✓ Database initialized")
    
    # Iniciar heartbeat monitor para WebSocket
    from app.websocket.manager import connection_manager
    heartbeat_task = asyncio.create_task(connection_manager.heartbeat_monitor())
    logger.info("✓ WebSocket heartbeat monitor started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AdsPower Orchestrator API...")
    heartbeat_task.cancel()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## 🚀 AdsPower Orchestrator API
    
    Sistema de orquestación distribuida para gestión de perfiles AdsPower con automatización paralela.
    
    ### Características:
    
    * **Computers**: Gestión de múltiples instancias de AdsPower
    * **Proxies**: Pool de proxies con health checks
    * **Profiles**: Creación y gestión de perfiles distribuidos
    * **Warming Scripts**: Scripts reutilizables de warming
    * **Automation**: Búsquedas y navegación paralela sincronizada
    * **WebSocket**: Comunicación en tiempo real con agentes
    * **Health Monitoring**: Monitoreo automático de componentes
    
    ### Arquitectura:
    
    - **Computadora A (Orquestador)**: Control centralizado vía API
    - **Computadoras B (Agentes)**: Ejecución distribuida de warming
    - **WebSocket**: Comunicación bidireccional en tiempo real
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check básico
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Include API v1 router
app.include_router(api_v1_router, prefix="/api/v1")

# Root
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint con información de la API"""
    return {
        "message": "AdsPower Orchestrator API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api": {
            "computers": "/api/v1/computers/",
            "proxies": "/api/v1/proxies/",
            "profiles": "/api/v1/profiles/",
            "tasks": "/api/v1/tasks/",
            "automation": "/api/v1/automation/",
            "warming": "/api/v1/warming/",
            "health": "/api/v1/health/"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )