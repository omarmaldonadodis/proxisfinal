import asyncio
import sys
import os

sys.path.append("/app")

from app.database import AsyncSessionLocal
from sqlalchemy import text
from loguru import logger

async def clean_database():
    logger.warning("🚨 [DANGER ZONE] Iniciando limpieza profunda de la Base de Datos...")
    logger.info("ℹ️  Las tablas de 'Computer' y 'ComputerToken' (Tu Agente) SE MANTENDRÁN INTACTAS.")
    
    # Lista de las tablas que vamos a vaciar. 
    # El orden importa por las claves foráneas (Foreign Keys),
    # o mejor usamos TRUNCATE CASCADE que se encarga de todo.
    tables_to_truncate = [
        "browser_events",
        "agent_sessions",
        "profile_assignments",
        "profile_metrics",
        "proxy_usage_stats",
        "proxy_health_checks",
        "proxy_scores",
        "proxy_rotation_logs",
        "health_checks",
        "alerts",
        "profiles",  # Perfiles de AdsPower
        "proxies",   # Configuraciones de SOAX
    ]
    
    try:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                # En PostgreSQL, TRUNCATE ... CASCADE borra los datos de la tabla 
                # y automáticamente de todas las tablas que dependan de ellas, de un solo golpe.
                # También resetea los IDs autoincrementales a 1 (RESTART IDENTITY).
                tables_str = ", ".join(tables_to_truncate)
                query = text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;")
                
                logger.info(f"Ejecutando: {query}")
                await db.execute(query)
                
                logger.success("✅ Base de datos limpiada con éxito. ¡Todos los registros excepto el agente se han ido!")
                
    except Exception as e:
        logger.error(f"❌ Error durante la limpieza: {e}")

if __name__ == "__main__":
    asyncio.run(clean_database())
