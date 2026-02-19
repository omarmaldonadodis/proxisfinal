# app/main.py - SIMPLIFICADO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

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
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "AdsPower Profile Manager API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)