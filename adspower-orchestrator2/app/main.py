from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
import asyncio

from app.config import settings
from app.database import init_db
from app.api.v1 import router as api_v1_router

from fastapi.staticfiles import StaticFiles
import os


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

# ✅ Tareas en background
background_tasks = set()

async def auto_health_check_loop():
    """
    ✅ Loop automático de health check cada 60 segundos
    
    Verifica:
    - Qué computadoras están conectadas vía WebSocket
    - Actualiza status en DB: ONLINE si conectada, OFFLINE si no
    """
    from app.database import AsyncSessionLocal
    from app.services.computer_service import ComputerService
    from app.websocket.manager import connection_manager
    from app.models.computer import ComputerStatus
    
    logger.info("🏥 Auto health check loop started")
    
    while True:
        try:
            await asyncio.sleep(60)  # Cada 60 segundos
            
            async with AsyncSessionLocal() as db:
                computer_service = ComputerService(db)
                
                # Obtener todas las computadoras
                computers, _ = await computer_service.list_computers(limit=1000)
                
                connected_agents = connection_manager.get_connected_agents()
                
                for computer in computers:
                    is_connected = computer.id in connected_agents
                    
                    # ✅ Actualizar status según conexión
                    new_status = ComputerStatus.ONLINE if is_connected else ComputerStatus.OFFLINE
                    
                    if computer.status != new_status:
                        from app.schemas.computer import ComputerUpdate
                        
                        await computer_service.update_computer(
                            computer.id,
                            ComputerUpdate(status=new_status)
                        )
                        
                        status_emoji = "🟢" if is_connected else "🔴"
                        logger.info(
                            f"{status_emoji} Computer {computer.id} ({computer.name}): "
                            f"{computer.status} -> {new_status}"
                        )
                
                online_count = len(connected_agents)
                total_count = len(computers)
                logger.debug(
                    f"Health check: {online_count}/{total_count} computers online"
                )
        
        except asyncio.CancelledError:
            logger.info("Auto health check stopped")
            break
        
        except Exception as e:
            logger.error(f"Auto health check error: {e}")
            await asyncio.sleep(10)

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
    
    # ✅ Iniciar warming sync manager
    from app.services.warming_sync import WarmingSyncManager
    warming_sync_manager = WarmingSyncManager()
    await warming_sync_manager.start()
    logger.info("✓ Warming sync manager started")
    
    # Iniciar heartbeat monitor para WebSocket
    from app.websocket.manager import connection_manager
    heartbeat_task = asyncio.create_task(connection_manager.heartbeat_monitor())
    background_tasks.add(heartbeat_task)
    logger.info("✓ WebSocket heartbeat monitor started")
    
    # ✅ Iniciar auto health check
    health_check_task = asyncio.create_task(auto_health_check_loop())
    background_tasks.add(health_check_task)
    logger.info("✓ Auto health check started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AdsPower Orchestrator API...")
    
    # ✅ Cancelar todas las tareas
    for task in background_tasks:
        task.cancel()
    
    await asyncio.gather(*background_tasks, return_exceptions=True)
    
    await warming_sync_manager.stop()
    logger.info("✓ Shutdown complete")

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
    * **Auto Health Check**: Detección automática de agentes online/offline
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

templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")

@app.get("/monitor", response_class=HTMLResponse, tags=["Dashboard"])
async def event_monitor():
    """Dashboard de monitoreo de eventos en tiempo real"""
    
    html_path = os.path.join(templates_dir, "event_monitor.html")
    
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return "<h1>Event Monitor not found</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )