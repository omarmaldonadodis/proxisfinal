# app/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
import os

from app.config import settings
from app.database import init_db
from app.api.v1 import router as api_v1_router

logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("logs/app_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    logger.info("=" * 60)
    logger.info("Starting AdsPower Profile Manager")
    logger.info(f"Version: {settings.APP_VERSION}")
    logger.info("=" * 60)

    await init_db()
    logger.info("✓ Database initialized")

    from app.utils.soax_cities_manager import SOAXCitiesManager
    await SOAXCitiesManager.initialize()
    logger.info("✓ SOAX Cities Manager initialized")

    yield

    logger.info("Shutting down...")


app = FastAPI(
    title="AdsPower Profile Manager",
    version=settings.APP_VERSION,
    description="""
    ## 🚀 AdsPower Profile Manager with SOAX Integration

    Sistema simplificado para:
    * **Profiles**: Creación de perfiles AdsPower ultra-realistas
    * **Proxies**: Gestión y rotación automática de proxies SOAX
    * **Metrics**: Analytics y reportes de uso
    * **Health**: Monitoreo de componentes
    """,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,  # ← lista, no string
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para proteger rutas de documentación
@app.middleware("http")
async def check_docs_access(request: Request, call_next):
    # Rutas protegidas: docs, redoc, openapi.json
    protected_paths = ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"]
    
    if any(request.url.path.startswith(path) for path in protected_paths):
        # Si DEBUG no está activado, rechazar acceso a docs
        if not settings.DEBUG:
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        
        # Si DEBUG está activado, verificar IP permitida
        client_ip = request.client.host
        if client_ip not in settings.allowed_ips_list:
            return JSONResponse(status_code=403, content={"detail": "IP not allowed"})
    
    response = await call_next(request)
    return response

# Servir los assets estáticos locales si existen
if os.path.isdir("/app/static"):
    app.mount("/static", StaticFiles(directory="/app/static"), name="static")


app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "AdsPower Profile Manager API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
