# app/tasks/backup_tasks.py - VERSIÓN MEJORADA
from app.tasks import celery_app
from app.config import settings
from loguru import logger
import subprocess
from datetime import datetime
import os
from urllib.parse import urlparse
import shutil

@celery_app.task(name='tasks.backup_database')
def backup_database_task():
    """
    Backup automático de PostgreSQL con validación de espacio
    
    ✅ Mejoras:
    - Parsing robusto de DATABASE_URL
    - Validación de espacio en disco
    - Logging estructurado
    - Manejo de errores mejorado
    """
    
    if not settings.BACKUP_ENABLED:
        logger.info("Backup disabled in settings")
        return {'success': False, 'message': 'Backup disabled'}
    
    try:
        # ========================================
        # 1. VALIDAR ESPACIO EN DISCO
        # ========================================
        backup_dir = settings.BACKUP_PATH
        os.makedirs(backup_dir, exist_ok=True)
        
        stat = shutil.disk_usage(backup_dir)
        free_gb = stat.free / (1024**3)
        
        if free_gb < 1:  # Menos de 1GB libre
            logger.error(f"Insufficient disk space: {free_gb:.2f}GB free")
            return {
                'success': False,
                'error': f'Insufficient disk space: {free_gb:.2f}GB free'
            }
        
        # ========================================
        # 2. PARSEAR DATABASE_URL (ROBUSTO)
        # ========================================
        db_url = settings.DATABASE_SYNC_URL
        parsed = urlparse(db_url)
        
        # Extraer componentes
        user = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 5432
        dbname = parsed.path.lstrip('/')
        
        logger.info(f"Starting backup for database: {dbname}@{host}")
        
        # ========================================
        # 3. GENERAR NOMBRE DE ARCHIVO
        # ========================================
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
        
        # ========================================
        # 4. EJECUTAR PG_DUMP
        # ========================================
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        command = [
            'pg_dump',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', dbname,
            '-f', backup_file,
            '--format=plain',
            '--no-owner',
            '--no-acl',
            '--verbose'
        ]
        
        logger.info(f"Executing pg_dump to: {backup_file}")
        
        result = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos timeout
        )
        
        # ========================================
        # 5. VERIFICAR RESULTADO
        # ========================================
        if result.returncode == 0:
            file_size = os.path.getsize(backup_file)
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(
                f"✓ Backup created successfully: {backup_file} "
                f"({file_size_mb:.2f} MB)"
            )
            
            # Limpiar backups antiguos
            cleanup_old_backups(backup_dir, keep=7)
            
            return {
                'success': True,
                'backup_file': backup_file,
                'size_bytes': file_size,
                'size_mb': round(file_size_mb, 2),
                'timestamp': timestamp
            }
        else:
            logger.error(f"Backup failed: {result.stderr}")
            
            # Eliminar archivo fallido
            if os.path.exists(backup_file):
                os.remove(backup_file)
            
            return {
                'success': False,
                'error': result.stderr
            }
    
    except subprocess.TimeoutExpired:
        logger.error("Backup timeout (>5 minutes)")
        return {
            'success': False,
            'error': 'Backup timeout after 5 minutes'
        }
    
    except Exception as e:
        logger.error(f"Backup error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def cleanup_old_backups(backup_dir: str, keep: int = 7):
    """
    Limpia backups antiguos (retención configurable)
    
    Args:
        backup_dir: Directorio de backups
        keep: Número de backups a mantener
    """
    try:
        files = [
            os.path.join(backup_dir, f)
            for f in os.listdir(backup_dir)
            if f.startswith('backup_') and f.endswith('.sql')
        ]
        
        # Ordenar por fecha de modificación (más recientes primero)
        files.sort(key=os.path.getmtime, reverse=True)
        
        # Eliminar los más antiguos
        deleted_count = 0
        for old_file in files[keep:]:
            try:
                file_size = os.path.getsize(old_file)
                os.remove(old_file)
                logger.info(
                    f"Removed old backup: {os.path.basename(old_file)} "
                    f"({file_size / (1024**2):.2f} MB)"
                )
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to remove {old_file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleanup completed: {deleted_count} old backups removed")
    
    except Exception as e:
        logger.error(f"Error cleaning old backups: {e}")


# ========================================
# TASK ADICIONAL: RESTORE
# ========================================

@celery_app.task(name='tasks.restore_database')
def restore_database_task(backup_file: str):
    """
    Restaura base de datos desde backup
    
    ⚠️ PELIGROSO: Sobrescribe DB actual
    """
    
    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        return {
            'success': False,
            'error': f'Backup file not found: {backup_file}'
        }
    
    try:
        # Parsear DATABASE_URL
        db_url = settings.DATABASE_SYNC_URL
        parsed = urlparse(db_url)
        
        user = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 5432
        dbname = parsed.path.lstrip('/')
        
        logger.warning(f"⚠️ Restoring database: {dbname}@{host}")
        
        # Ejecutar psql
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        command = [
            'psql',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', dbname,
            '-f', backup_file,
            '--quiet'
        ]
        
        result = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✓ Database restored from: {backup_file}")
            return {
                'success': True,
                'backup_file': backup_file
            }
        else:
            logger.error(f"Restore failed: {result.stderr}")
            return {
                'success': False,
                'error': result.stderr
            }
    
    except Exception as e:
        logger.error(f"Restore error: {e}")
        return {
            'success': False,
            'error': str(e)
        }