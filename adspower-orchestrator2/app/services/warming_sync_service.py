# adspower-orchestrator2/app/services/warming_sync_service.py
"""
Sistema de sincronización distribuida para ejecución paralela de warming scripts
Permite que múltiples agentes ejecuten acciones simultáneamente
"""
from typing import Dict, Set, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio
import uuid


class SyncBarrier:
    """Barrera de sincronización para coordinar múltiples agentes"""
    
    def __init__(self, barrier_id: str, total_agents: int, timeout_seconds: int = 60):
        self.barrier_id = barrier_id
        self.total_agents = total_agents
        self.timeout = timeout_seconds
        
        # Agentes que han llegado a la barrera
        self.arrived: Set[int] = set()
        
        # Evento para liberar a todos
        self.release_event = asyncio.Event()
        
        # Control de tiempo
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=timeout_seconds)
        
        # Estado
        self.is_released = False
        self.is_cancelled = False
        self.timed_out = False
        
        logger.info(
            f"SyncBarrier created: {barrier_id} "
            f"(agents: {total_agents}, timeout: {timeout_seconds}s)"
        )
    
    async def wait(self, agent_id: int) -> bool:
        """
        Espera en la barrera hasta que todos lleguen
        
        Returns:
            True si se liberó correctamente, False si timeout/cancelado
        """
        
        # Marcar como llegado
        self.arrived.add(agent_id)
        
        logger.debug(
            f"Barrier {self.barrier_id}: Agent {agent_id} arrived "
            f"({len(self.arrived)}/{self.total_agents})"
        )
        
        # Si todos llegaron, liberar inmediatamente
        if len(self.arrived) >= self.total_agents:
            self.is_released = True
            self.release_event.set()
            logger.info(f"✅ Barrier {self.barrier_id} released (all agents arrived)")
            return True
        
        # Calcular tiempo restante
        now = datetime.utcnow()
        remaining = (self.expires_at - now).total_seconds()
        
        if remaining <= 0:
            self.timed_out = True
            self.release_event.set()
            logger.warning(f"⚠️ Barrier {self.barrier_id} timeout")
            return False
        
        # Esperar con timeout
        try:
            await asyncio.wait_for(
                self.release_event.wait(),
                timeout=remaining
            )
            return not (self.is_cancelled or self.timed_out)
        
        except asyncio.TimeoutError:
            self.timed_out = True
            self.release_event.set()
            logger.warning(f"⚠️ Barrier {self.barrier_id} timeout")
            return False
    
    def cancel(self):
        """Cancela la barrera"""
        self.is_cancelled = True
        self.release_event.set()
        logger.info(f"Barrier {self.barrier_id} cancelled")
    
    def is_expired(self) -> bool:
        """Verifica si la barrera ha expirado"""
        return datetime.utcnow() > self.expires_at
    
    def get_status(self) -> Dict:
        """Retorna estado de la barrera"""
        return {
            "barrier_id": self.barrier_id,
            "total_agents": self.total_agents,
            "arrived_count": len(self.arrived),
            "is_released": self.is_released,
            "is_cancelled": self.is_cancelled,
            "timed_out": self.timed_out,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat()
        }


class WarmingSyncService:
    """
    Servicio de sincronización para warming distribuido
    
    Gestiona barreras para coordinar ejecución paralela entre múltiples agentes
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
        
        # Barreras activas: {batch_id-action_index: SyncBarrier}
        self.barriers: Dict[str, SyncBarrier] = {}
        
        # Lock para operaciones thread-safe
        self.lock = asyncio.Lock()
        
        # Tarea de limpieza
        self.cleanup_task: Optional[asyncio.Task] = None
        
        self._initialized = True
        
        logger.info("WarmingSyncService initialized")
    
    async def start(self):
        """Inicia el servicio de sincronización"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("WarmingSyncService started")
    
    async def stop(self):
        """Detiene el servicio"""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("WarmingSyncService stopped")
    
    async def create_barrier(
        self,
        batch_id: str,
        action_index: int,
        total_agents: int,
        timeout_seconds: int = 60
    ) -> str:
        """
        Crea una barrera de sincronización
        
        Returns:
            barrier_id
        """
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        async with self.lock:
            # Si ya existe, retornar el existente
            if barrier_id in self.barriers:
                logger.debug(f"Barrier {barrier_id} already exists")
                return barrier_id
            
            # Crear nueva barrera
            barrier = SyncBarrier(
                barrier_id=barrier_id,
                total_agents=total_agents,
                timeout_seconds=timeout_seconds
            )
            
            self.barriers[barrier_id] = barrier
            
            return barrier_id
    
    async def wait_at_barrier(
        self,
        batch_id: str,
        action_index: int,
        agent_id: int
    ) -> bool:
        """
        Espera en una barrera de sincronización
        
        Returns:
            True si sincronización exitosa, False si fallo
        """
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        # Obtener barrera (sin lock para permitir espera concurrente)
        barrier = self.barriers.get(barrier_id)
        
        if not barrier:
            logger.error(f"Barrier {barrier_id} not found!")
            return False
        
        # Esperar en la barrera
        success = await barrier.wait(agent_id)
        
        return success
    
    async def cancel_barrier(self, batch_id: str, action_index: int):
        """Cancela una barrera específica"""
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        async with self.lock:
            if barrier_id in self.barriers:
                self.barriers[barrier_id].cancel()
    
    async def cancel_batch(self, batch_id: str):
        """Cancela todas las barreras de un batch"""
        
        async with self.lock:
            cancelled = []
            
            for barrier_id, barrier in list(self.barriers.items()):
                if barrier_id.startswith(f"{batch_id}_"):
                    barrier.cancel()
                    cancelled.append(barrier_id)
            
            if cancelled:
                logger.info(f"Cancelled {len(cancelled)} barriers for batch {batch_id}")
    
    async def remove_barrier(self, batch_id: str, action_index: int):
        """Elimina una barrera"""
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        async with self.lock:
            if barrier_id in self.barriers:
                del self.barriers[barrier_id]
                logger.debug(f"Removed barrier: {barrier_id}")
    
    async def remove_batch(self, batch_id: str):
        """Elimina todas las barreras de un batch"""
        
        async with self.lock:
            removed = []
            
            for barrier_id in list(self.barriers.keys()):
                if barrier_id.startswith(f"{batch_id}_"):
                    del self.barriers[barrier_id]
                    removed.append(barrier_id)
            
            if removed:
                logger.debug(f"Removed {len(removed)} barriers for batch {batch_id}")
    
    async def get_barrier_status(
        self,
        batch_id: str,
        action_index: int
    ) -> Optional[Dict]:
        """Obtiene estado de una barrera"""
        
        barrier_id = f"{batch_id}_action_{action_index}"
        
        barrier = self.barriers.get(barrier_id)
        
        if not barrier:
            return None
        
        return barrier.get_status()
    
    async def get_batch_status(self, batch_id: str) -> List[Dict]:
        """Obtiene estado de todas las barreras de un batch"""
        
        statuses = []
        
        for barrier_id, barrier in self.barriers.items():
            if barrier_id.startswith(f"{batch_id}_"):
                statuses.append(barrier.get_status())
        
        return statuses
    
    async def _cleanup_loop(self):
        """Loop de limpieza de barreras expiradas"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Cada minuto
                
                async with self.lock:
                    expired = [
                        barrier_id
                        for barrier_id, barrier in self.barriers.items()
                        if barrier.is_expired() or barrier.is_released
                    ]
                    
                    for barrier_id in expired:
                        del self.barriers[barrier_id]
                    
                    if expired:
                        logger.info(f"Cleaned {len(expired)} expired/released barriers")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas del servicio"""
        return {
            "total_barriers": len(self.barriers),
            "active_batches": len(set(
                barrier_id.split("_action_")[0]
                for barrier_id in self.barriers.keys()
            ))
        }


# Instancia global singleton
warming_sync_service = WarmingSyncService()