# agent/warming_executor.py (ACTUALIZACIÓN COMPLETA)
"""
Ejecutor de warming con soporte para sincronización paralela
Permite ejecución simultánea sin bloqueos
"""
import asyncio
from typing import Dict, List, Callable, Optional
from loguru import logger
from datetime import datetime
from action_executor import ActionExecutor

from event_detector import UniversalEventDetector
from event_model import ExecutionEvent
from event_types import EventType, EventSeverity
from event_deduplicator import EventDeduplicator, ExecutionEventCache
import uuid


class WarmingExecutor:
    """Ejecutor de warming con deduplicación y sincronización"""
    
    def __init__(self, config, browser_controller):
        self.config = config
        self.browser_controller = browser_controller
        self.action_executor = ActionExecutor(config)
        
        # Establecer credenciales por defecto
        self.action_executor.set_session_var("USERNAME", "omaritouv0209@gmail.com")
        self.action_executor.set_session_var("PASSWORD", "Eocm2003!")
        
        # ✅ CAMBIO: Ejecuciones activas SIN LÍMITE de concurrencia
        # Cada ejecución corre independientemente
        self.active_executions: Dict[int, asyncio.Task] = {}
        
        # Detector de eventos
        self.event_detector = UniversalEventDetector()
        
        # Sistema de deduplicación
        self.event_deduplicator = EventDeduplicator(dedup_window_seconds=30)
        self.execution_cache = ExecutionEventCache()
    
    async def execute(
        self,
        execution_id: int,
        profile_id: str,
        actions: List[dict],
        batch_id: Optional[str] = None,  # ✅ NUEVO
        progress_callback: Optional[Callable] = None
    ):
        """
        Ejecuta warming script
        
        ✅ NUEVO: batch_id permite sincronización paralela
        """
        
        # ✅ Crear tarea SIN esperar
        task = asyncio.create_task(
            self._execute_warming(
                execution_id,
                profile_id,
                actions,
                batch_id,
                progress_callback
            )
        )
        
        self.active_executions[execution_id] = task
        
        # ✅ NO BLOQUEAMOS: La tarea corre en background
        logger.info(
            f"Warming execution started in background: "
            f"execution_id={execution_id}, batch_id={batch_id}"
        )
    
    async def _execute_warming(
        self,
        execution_id: int,
        profile_id: str,
        actions: List[dict],
        batch_id: Optional[str],
        progress_callback: Optional[Callable] = None
    ):
        """Ejecuta warming CON sincronización si es batch"""
        
        driver = None
        start_time = datetime.utcnow()
        
        try:
            logger.info(
                f"Starting warming: execution_id={execution_id}, "
                f"batch_id={batch_id or 'none'}"
            )
            
            # Abrir navegador
            driver = await self.browser_controller.open_browser(profile_id)
            
            if not driver:
                await self._send_event_smart(
                    EventType.BROWSER_CRASH,
                    EventSeverity.CRITICAL,
                    execution_id,
                    profile_id,
                    "Failed to open browser",
                    {"reason": "Browser controller returned None"},
                    requires_manual=True,
                    can_retry=True,
                    progress_callback=progress_callback
                )
                raise Exception(f"Failed to open browser for profile {profile_id}")
            
            # Evento de inicio
            await self._send_event_smart(
                EventType.EXECUTION_STARTED,
                EventSeverity.INFO,
                execution_id,
                profile_id,
                "Warming execution started",
                {"total_actions": len(actions), "batch_id": batch_id},
                requires_manual=False,
                can_retry=False,
                progress_callback=progress_callback
            )
            
            # Ejecutar acciones
            total_actions = len(actions)
            completed = 0
            failed = 0
            
            for i, action in enumerate(actions):
                try:
                    # ✅ SINCRONIZACIÓN: Si es batch, esperar en barrera
                    if batch_id:
                        sync_success = await self._sync_wait_at_barrier(
                            batch_id=batch_id,
                            action_index=i,
                            execution_id=execution_id
                        )
                        
                        if not sync_success:
                            logger.warning(
                                f"Sync barrier timeout for action {i}, "
                                "continuing anyway..."
                            )
                    
                    # Detectar eventos ANTES
                    events_before = await self.event_detector.detect_all_events(
                        driver,
                        execution_id,
                        profile_id,
                        computer_id=self.config.COMPUTER_ID,
                        action_index=i,
                        action_type=action.get("type")
                    )
                    
                    for event in events_before:
                        await self._send_detected_event_smart(event, progress_callback)
                        
                        if event.severity == EventSeverity.CRITICAL and not event.can_retry:
                            logger.error(f"Critical event, aborting: {event.message}")
                            raise Exception(f"Critical event: {event.event_type}")
                    
                    # Ejecutar acción
                    success = await self.action_executor.execute_action(driver, action)
                    
                    if success:
                        completed += 1
                    else:
                        failed += 1
                    
                    # Detectar eventos DESPUÉS
                    events_after = await self.event_detector.detect_all_events(
                        driver,
                        execution_id,
                        profile_id,
                        computer_id=self.config.COMPUTER_ID,
                        action_index=i,
                        action_type=action.get("type")
                    )
                    
                    for event in events_after:
                        await self._send_detected_event_smart(event, progress_callback)
                        
                        if event.severity == EventSeverity.CRITICAL and not event.can_retry:
                            logger.error(f"Critical event: {event.message}")
                            raise Exception(f"Critical event: {event.event_type}")
                    
                    # Progreso
                    progress = int((i + 1) / total_actions * 100)
                    
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
                
                except Exception as e:
                    logger.error(f"Action {i+1} failed: {e}")
                    failed += 1
                    
                    error_events = await self.event_detector.detect_all_events(
                        driver,
                        execution_id,
                        profile_id,
                        computer_id=self.config.COMPUTER_ID,
                        action_index=i,
                        action_type=action.get("type")
                    )
                    
                    for event in error_events:
                        await self._send_detected_event_smart(event, progress_callback)
            
            # Completado
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            await self._send_event_smart(
                EventType.EXECUTION_COMPLETED,
                EventSeverity.INFO,
                execution_id,
                profile_id,
                f"Warming completed: {completed}/{total_actions} actions successful",
                {
                    "total_actions": total_actions,
                    "completed": completed,
                    "failed": failed,
                    "duration_seconds": duration,
                    "batch_id": batch_id
                },
                requires_manual=False,
                can_retry=False,
                progress_callback=progress_callback
            )
            
            logger.info(f"Warming completed: execution_id={execution_id}")
        
        except Exception as e:
            logger.error(f"Warming failed: execution_id={execution_id}, error={e}")
            
            await self._send_event_smart(
                EventType.EXECUTION_FAILED,
                EventSeverity.CRITICAL,
                execution_id,
                profile_id,
                f"Warming failed: {str(e)}",
                {"error": str(e), "error_type": type(e).__name__},
                requires_manual=True,
                can_retry=False,
                progress_callback=progress_callback
            )
        
        finally:
            if driver:
                await self.browser_controller.close_browser(profile_id)
            
            # Limpiar
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            self.event_deduplicator.mark_execution_completed(execution_id)
            self.execution_cache.clear_execution(execution_id)
    
    async def _sync_wait_at_barrier(
        self,
        batch_id: str,
        action_index: int,
        execution_id: int
    ) -> bool:
        """
        ✅ SINCRONIZACIÓN: Espera en barrera distribuida
        
        Comunica con el orquestrador para coordinar con otros agentes
        """
        
        logger.debug(
            f"Waiting at sync barrier: batch={batch_id}, "
            f"action={action_index}, execution={execution_id}"
        )
        
        # TODO: Implementar comunicación con orquestrador
        # Por ahora, solo log
        
        # En producción, esto debería:
        # 1. Enviar mensaje al orquestrador: "llegué a la barrera"
        # 2. Esperar respuesta del orquestrador: "todos llegaron, continúa"
        # 3. Timeout si no recibe respuesta en 60s
        
        return True
    
    async def _send_event_smart(
        self,
        event_type: EventType,
        severity: EventSeverity,
        execution_id: int,
        profile_id: str,
        message: str,
        details: Dict,
        requires_manual: bool,
        can_retry: bool,
        progress_callback: Optional[Callable] = None
    ):
        """Envía evento CON DEDUPLICACIÓN"""
        
        should_report = self.event_deduplicator.should_report(
            execution_id,
            event_type,
            current_url=details.get("current_url"),
            severity=severity
        )
        
        if not should_report:
            logger.debug(f"Event deduplicated: {event_type}")
            return
        
        should_report_once = self.execution_cache.should_report_once(
            execution_id,
            event_type
        )
        
        if not should_report_once:
            logger.debug(f"Event already reported once: {event_type}")
            return
        
        event = ExecutionEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            execution_id=execution_id,
            computer_id=self.config.COMPUTER_ID,
            profile_id=profile_id,
            message=message,
            details=details,
            timestamp=datetime.utcnow(),
            requires_manual_intervention=requires_manual,
            can_retry=can_retry
        )
        
        await self._send_detected_event(event, progress_callback)
    
    async def _send_detected_event_smart(
        self,
        event: ExecutionEvent,
        progress_callback: Optional[Callable] = None
    ):
        """Envía evento detectado CON DEDUPLICACIÓN"""
        
        should_report = self.event_deduplicator.should_report(
            event.execution_id,
            event.event_type,
            current_url=event.current_url,
            severity=event.severity
        )
        
        if not should_report:
            logger.debug(f"Event deduplicated: {event.event_type}")
            return
        
        should_report_once = self.execution_cache.should_report_once(
            event.execution_id,
            event.event_type
        )
        
        if not should_report_once:
            logger.debug(f"Event already reported once: {event.event_type}")
            return
        
        await self._send_detected_event(event, progress_callback)
    
    async def _send_detected_event(
        self,
        event: ExecutionEvent,
        progress_callback: Optional[Callable] = None
    ):
        """Envía evento al orquestrador"""
        
        if progress_callback:
            event_dict = event.model_dump(mode='json')
            
            await progress_callback(
                event.execution_id,
                0,
                {
                    "event": event_dict,
                    "is_event": True
                }
            )
    
    async def stop(self, execution_id: int) -> bool:
        """Detiene una ejecución"""
        
        if execution_id not in self.active_executions:
            logger.warning(f"Execution {execution_id} not found")
            return False
        
        task = self.active_executions[execution_id]
        task.cancel()
        
        self.event_deduplicator.mark_execution_completed(execution_id)
        self.execution_cache.clear_execution(execution_id)
        
        logger.info(f"Execution {execution_id} cancelled")
        return True
    
    def get_active_count(self) -> int:
        """Retorna cantidad de ejecuciones activas"""
        return len(self.active_executions)