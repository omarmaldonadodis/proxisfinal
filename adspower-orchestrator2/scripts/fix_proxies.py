import asyncio
import sys
import os

# Agregar el directorio raíz al path para poder importar la app
# Asumiendo que el script está en backend/scripts/fix_proxies.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Intentar cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.database import AsyncSessionLocal
from app.models.proxy import Proxy
from sqlalchemy import update
from loguru import logger

async def fix_passwords():
    # Esta es la que me confirmaste que va
    CORRECT_PASSWORD = "cUohoUq59MXWY6aT"
    
    logger.info("🚀 Iniciando corrección masiva de contraseñas de proxy...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Seleccionamos primero para ver cuántos hay
            async with db.begin():
                stmt = update(Proxy).values(password=CORRECT_PASSWORD)
                result = await db.execute(stmt)
                
                rows_updated = result.rowcount
                logger.success(f"✅ Se actualizaron {rows_updated} registros de proxy a la contraseña: {CORRECT_PASSWORD}")
                
        logger.info("✨ Proceso de DB completado.")
        logger.info("⚠️  RECUERDA: Reinicia tus contenedores de Docker (o el proceso del back) para asegurar que el .env actual sea el que manda.")
        
    except Exception as e:
        logger.error(f"❌ Error durante la actualización: {e}")
        logger.info("Asegurate de tener el entorno virtual activo y las dependencias instaladas.")

if __name__ == "__main__":
    asyncio.run(fix_passwords())
