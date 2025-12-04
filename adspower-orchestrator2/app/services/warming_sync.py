# app/services/warming_sync.py - NUEVO ARCHIVO
"""
Sistema de sincronización para ejecuciones paralelas distribuidas
"""
import asyncio
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
from loguru import logger

class WarmingBarrier:
    """
    Barrera de sincronización distribuida para warming paralelo
    
    Coordina múltiples agentes para que ejecuten acciones simultáneamente
    """
    
    def __init__(self, barrier_id: str, total_participants: int, timeout: int = 60):
        self.barrier_id = barrier_id
        self.total_participants = total_participants
        self.timeout = timeout
        
        # Participantes que han llegado a la barrera
        self.arrived: Set[int] = set()
        
        # Evento para liberar a todos cuando todos lleguen
        self.release_event = asyncio.Event()
        
        # Timestamp de creación
        self.created_at = datetime.utcnow()
        
        # Estado
        self.is_released = False
        self.is_cancelled = False
    
    async def wait(self, execution_id: int) -> bool:
        """
        Espera en la barrera hasta que todos lleguen o timeout
        
        Returns:
            True si se liberó correctamente, False si timeout o cancelado
        """
        
        # Marcar como llegado
        self.arrived.add(execution_id)
        
        logger.debug(
            f"Barrier {self.barrier_id}: {len(self.arrived)}/{self.total_participants} arrived"
        )
        
        # Si todos llegaron, liberar
        if len(self.arrived) >= self.total_participants:
            self.is_released = True
            self.release_event.set()
            logger.info(f"✓ Barrier {self.barrier_id} released (all arrived)")
            return True
        
        # Esperar con timeout
        try:
            await asyncio.wait_for(
                self.release_event.wait(),
                timeout=self.timeout
            )
            return not self.is_cancelled
        
        except asyncio.TimeoutError:
            logger.warning(f"⚠ Barrier {self.barrier_id} timeout")
            self.is_cancelled = True
            self.release_event.set()  # Liberar a los que esperan
            return False
    
    def cancel(self):
        """Cancela la barrera"""
        self.is_cancelled = True
        self.release_event.set()
        logger.info(f"Barrier {self.barrier_id} cancelled")
    
    def is_expired(self, expiry_minutes: int = 10) -> bool:
        """Verifica si la barrera ha expirado"""
        age = datetime.utcnow() - self.created_at
        return age > timedelta(minutes=expiry_minutes)


class WarmingSyncManager:
    """
    Gestor global de sincronización para warming distribuido
    
    Singleton que coordina barreras entre múltiples agentes
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Barreras activas: {batch_id-action_index: WarmingBarrier}
        self.barriers: Dict[str, WarmingBarrier] = {}
        
        # Lock para operaciones thread-safe
        self.lock = asyncio.Lock()
        
        # Tarea de limpieza
        self.cleanup_task = None
        
        self._initialized = True
        
        logger.info("WarmingSyncManager initialized")
    
    async def start(self):
        """Inicia el gestor de sincronización"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("WarmingSyncManager cleanup task started")
    
    async def stop(self):
        """Detiene el gestor"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def create_barrier(
        self,
        batch_id: str,
        action_index: int,
        total_participants: int,
        timeout: int = 60
    ) -> WarmingBarrier:
        """Crea una nueva barrera de sincronización"""
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        async with self.lock:
            if barrier_id in self.barriers:
                # Barrera ya existe, retornar existente
                return self.barriers[barrier_id]
            
            barrier = WarmingBarrier(
                barrier_id=barrier_id,
                total_participants=total_participants,
                timeout=timeout
            )
            
            self.barriers[barrier_id] = barrier
            
            logger.info(
                f"Created barrier: {barrier_id} "
                f"(participants: {total_participants}, timeout: {timeout}s)"
            )
            
            return barrier
    
    async def wait_at_barrier(
        self,
        batch_id: str,
        action_index: int,
        execution_id: int
    ) -> bool:
        """
        Espera en una barrera de sincronización
        
        Returns:
            True si sincronización exitosa, False si fallo
        """
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        async with self.lock:
            if barrier_id not in self.barriers:
                logger.error(f"Barrier {barrier_id} not found!")
                return False
            
            barrier = self.barriers[barrier_id]
        
        # Esperar en la barrera (fuera del lock)
        success = await barrier.wait(execution_id)
        
        return success
    
    async def cancel_barrier(self, batch_id: str, action_index: int):
        """Cancela una barrera"""
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        async with self.lock:
            if barrier_id in self.barriers:
                self.barriers[barrier_id].cancel()
    
    async def remove_barrier(self, batch_id: str, action_index: int):
        """Elimina una barrera"""
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        async with self.lock:
            if barrier_id in self.barriers:
                del self.barriers[barrier_id]
                logger.debug(f"Removed barrier: {barrier_id}")
    
    async def _cleanup_loop(self):
        """Loop de limpieza de barreras expiradas"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Cada minuto
                
                async with self.lock:
                    expired = [
                        barrier_id
                        for barrier_id, barrier in self.barriers.items()
                        if barrier.is_expired()
                    ]
                    
                    for barrier_id in expired:
                        logger.info(f"Cleaning expired barrier: {barrier_id}")
                        del self.barriers[barrier_id]
                    
                    if expired:
                        logger.info(f"Cleaned {len(expired)} expired barriers")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")


# Instancia global
warming_sync_manager = WarmingSyncManager()