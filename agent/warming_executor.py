# agent/warming_executor.py
import asyncio
from typing import Dict, List, Callable, Optional
from loguru import logger
from datetime import datetime
from action_executor import ActionExecutor

class WarmingExecutor:
    """Ejecutor de warming scripts"""
    
    def __init__(self, config, browser_controller):
        self.config = config
        self.browser_controller = browser_controller
        self.action_executor = ActionExecutor(config)
        
        # Ejecuciones activas: execution_id -> task
        self.active_executions: Dict[int, asyncio.Task] = {}
        
        # Semáforo para limitar ejecuciones concurrentes
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_EXECUTIONS)
    
    async def execute(
        self,
        execution_id: int,
        profile_id: int,
        actions: List[dict],
        progress_callback: Optional[Callable] = None
    ):
        """Ejecuta warming script"""
        
        # Crear tarea
        task = asyncio.create_task(
            self._execute_warming(
                execution_id,
                profile_id,
                actions,
                progress_callback
            )
        )
        
        self.active_executions[execution_id] = task
        
        # Esperar a que termine
        try:
            await task
        finally:
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _execute_warming(
        self,
        execution_id: int,
        profile_id: int,
        actions: List[dict],
        progress_callback: Optional[Callable] = None
    ):
        """Ejecuta warming (interno)"""
        
        driver = None
        start_time = datetime.utcnow()
        
        try:
            # Adquirir semáforo
            async with self.semaphore:
                logger.info(f"Starting warming: execution_id={execution_id}, profile_id={profile_id}")
                
                # Abrir navegador
                driver = await self.browser_controller.open_browser(profile_id)
                
                if not driver:
                    raise Exception(f"Failed to open browser for profile {profile_id}")
                
                # Ejecutar acciones
                total_actions = len(actions)
                completed = 0
                failed = 0
                
                for i, action in enumerate(actions):
                    try:
                        # Ejecutar acción
                        success = await self.action_executor.execute_action(driver, action)
                        
                        if success:
                            completed += 1
                        else:
                            failed += 1
                        
                        # Calcular progreso
                        progress = int((i + 1) / total_actions * 100)
                        
                        # Enviar progreso
                        if progress_callback:
                            await progress_callback(
                                execution_id,
                                progress,
                                {
                                    "action_index": i,
                                    "action_type": action.get("type"),
                                    "success": success,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                        
                        logger.debug(f"Action {i+1}/{total_actions} completed: {action.get('type')}")
                    
                    except Exception as e:
                        logger.error(f"Action {i+1} failed: {e}")
                        failed += 1
                        
                        # Enviar error
                        if progress_callback:
                            await progress_callback(
                                execution_id,
                                int((i + 1) / total_actions * 100),
                                {
                                    "action_index": i,
                                    "action_type": action.get("type"),
                                    "success": False,
                                    "error": str(e),
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                
                # Calcular duración
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Enviar completado
                if progress_callback:
                    await progress_callback(
                        execution_id,
                        100,
                        {
                            "completed": True,
                            "total_actions": total_actions,
                            "actions_completed": completed,
                            "actions_failed": failed,
                            "duration_seconds": duration,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                logger.info(f"Warming completed: execution_id={execution_id}, completed={completed}, failed={failed}")
        
        except Exception as e:
            logger.error(f"Warming failed: execution_id={execution_id}, error={e}")
            
            # Enviar error
            if progress_callback:
                await progress_callback(
                    execution_id,
                    0,
                    {
                        "completed": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        finally:
            # Cerrar navegador
            if driver:
                await self.browser_controller.close_browser(profile_id)
    
    async def stop(self, execution_id: int) -> bool:
        """Detiene una ejecución"""
        
        if execution_id not in self.active_executions:
            logger.warning(f"Execution {execution_id} not found")
            return False
        
        task = self.active_executions[execution_id]
        task.cancel()
        
        logger.info(f"Execution {execution_id} cancelled")
        return True
    
    def get_active_count(self) -> int:
        """Retorna cantidad de ejecuciones activas"""
        return len(self.active_executions)