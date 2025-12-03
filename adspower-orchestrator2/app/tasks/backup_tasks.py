# app/tasks/backup_tasks.py
from app.tasks import celery_app
from app.config import settings
from loguru import logger
import subprocess
from datetime import datetime
import os

@celery_app.task(name='tasks.backup_database')
def backup_database_task():
    """Backup de base de datos PostgreSQL"""
    
    if not settings.BACKUP_ENABLED:
        logger.info("Backup disabled in settings")
        return {'success': False, 'message': 'Backup disabled'}
    
    try:
        # Crear directorio de backup
        backup_dir = settings.BACKUP_PATH
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nombre del archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
        
        # Parsear DATABASE_SYNC_URL
        # postgresql://user:password@host:port/dbname
        db_url = settings.DATABASE_SYNC_URL
        parts = db_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        host_port = host_db[0].split(':')
        
        user = user_pass[0]
        password = user_pass[1]
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        dbname = host_db[1]
        
        # Ejecutar pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        command = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', dbname,
            '-f', backup_file,
            '--format=plain',
            '--no-owner',
            '--no-acl'
        ]
        
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            file_size = os.path.getsize(backup_file)
            logger.info(f"Backup created: {backup_file} ({file_size} bytes)")
            
            # Limpiar backups antiguos (mantener últimos 7)
            cleanup_old_backups(backup_dir, keep=7)
            
            return {
                'success': True,
                'backup_file': backup_file,
                'size_bytes': file_size
            }
        else:
            logger.error(f"Backup failed: {result.stderr}")
            return {
                'success': False,
                'error': result.stderr
            }
    
    except Exception as e:
        logger.error(f"Backup error: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def cleanup_old_backups(backup_dir: str, keep: int = 7):
    """Limpia backups antiguos"""
    try:
        files = [
            os.path.join(backup_dir, f)
            for f in os.listdir(backup_dir)
            if f.startswith('backup_') and f.endswith('.sql')
        ]
        
        files.sort(key=os.path.getmtime, reverse=True)
        
        for old_file in files[keep:]:
            os.remove(old_file)
            logger.info(f"Removed old backup: {old_file}")
    
    except Exception as e:
        logger.error(f"Error cleaning old backups: {e}")