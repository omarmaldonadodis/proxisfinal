# app/tasks/profile_tasks.py
from app.tasks import celery_app
from app.database import AsyncSessionLocal
from app.services.profile_service import ProfileService
from app.repositories.profile_repository import ProfileRepository
from loguru import logger

@celery_app.task(name='tasks.warmup_profile')
def warmup_profile_task(profile_id: int, duration_minutes: int):
    """Tarea para warmup de profile"""
    import asyncio
    
    async def _warmup():
        async with AsyncSessionLocal() as db:
            repo = ProfileRepository(db)
            
            # Actualizar status
            await repo.update_status(profile_id, 'warming')
            await db.commit()
            
            try:
                # Aquí iría la lógica de warmup
                # Por simplicidad, simulamos el warmup
                import time
                time.sleep(duration_minutes * 60)
                
                # Marcar como warmed
                await repo.mark_as_warmed(profile_id)
                await db.commit()
                
                logger.info(f"Profile {profile_id} warmed successfully")
                return {'success': True, 'profile_id': profile_id}
                
            except Exception as e:
                logger.error(f"Warmup failed for profile {profile_id}: {e}")
                await repo.update_status(profile_id, 'error')
                await db.commit()
                raise
    
    return asyncio.run(_warmup())

@celery_app.task(name='tasks.bulk_create_profiles')
def bulk_create_profiles_task(bulk_data: dict):
    """Tarea para creación masiva de profiles"""
    import asyncio
    
    async def _bulk_create():
        from app.schemas.profile import ProfileCreate, ProfileBulkCreate
        
        bulk_in = ProfileBulkCreate(**bulk_data)
        results = {
            'total': bulk_in.count,
            'successful': 0,
            'failed': 0,
            'profiles': []
        }
        
        async with AsyncSessionLocal() as db:
            service = ProfileService(db)
            
            for i in range(bulk_in.count):
                try:
                    # Crear profile individual
                    profile_in = ProfileCreate(
                        name=f"Profile_{i+1}",
                        computer_id=bulk_in.computer_id,
                        proxy_type=bulk_in.proxy_type,
                        country=bulk_in.country,
                        city=bulk_in.city,
                        device_type=bulk_in.device_type,
                        auto_warmup=bulk_in.auto_warmup,
                        warmup_duration_minutes=bulk_in.warmup_duration_minutes,
                        tags=bulk_in.tags
                    )
                    
                    profile = await service.create_profile(profile_in)
                    
                    results['successful'] += 1
                    results['profiles'].append({
                        'id': profile.id,
                        'name': profile.name,
                        'adspower_id': profile.adspower_id
                    })
                    
                    logger.info(f"Bulk profile {i+1}/{bulk_in.count} created")
                    
                except Exception as e:
                    logger.error(f"Failed to create profile {i+1}: {e}")
                    results['failed'] += 1
        
        return results
    
    return asyncio.run(_bulk_create())