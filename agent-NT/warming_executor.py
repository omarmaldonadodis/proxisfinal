# agent/warming_executor.py - VERSIÓN SIN BLOQUEOS
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
    """Ejecutor de warming optimizado sin bloqueos"""
    
    def __init__(self, config, browser_controller):
        self.config = config
        self.browser_controller = browser_controller
        self.action_executor = ActionExecutor(config)
        
        # Credenciales
        self.action_executor.set_session_var("USERNAME", "omaritouv0209@gmail.com")
        self.action_executor.set_session_var("PASSWORD", "Eocm2003!")
        
        # Ejecuciones activas (sin límite de concurrencia)
        self.active_executions: Dict[int, asyncio.Task] = {}
        
        # Detector de eventos
        self.event_detector = UniversalEventDetector(computer_id=config.COMPUTER_ID)
        
        # Sistema de deduplicación
        self.event_deduplicator = EventDeduplicator(dedup_window_seconds=30)
        self.execution_cache = ExecutionEventCache()
    
    async def execute(
        self,
        execution_id: int,
        profile_id: str,
        actions: List[dict],
        batch_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ):
        """Ejecuta warming SIN BLOQUEAR"""
        
        # ✅ Crear tarea en background
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
        
        logger.info(
            f"✅ Warming started (non-blocking): "
            f"execution_id={execution_id}, batch_id={batch_id}"
        )
        
        # ✅ NO ESPERAMOS - retorna inmediatamente
    
    async def _execute_warming(
        self,
        execution_id: int,
        profile_id: str,
        actions: List[dict],
        batch_id: Optional[str],
        progress_callback: Optional[Callable] = None
    ):
        """Ejecuta warming (corre en background)"""
        
        driver = None
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"🔥 Starting warming: execution={execution_id}")
            
            # ✅ 1. ABRIR NAVEGADOR (sin retry excesivo)
            driver = await asyncio.wait_for(
                self.browser_controller.open_browser(profile_id),
                timeout=45  # Timeout de 45s
            )
            
            if not driver:
                raise Exception(f"Failed to open browser for profile {profile_id}")
            
            # ✅ 2. ENVIAR EVENTO DE INICIO (sin esperar)
            asyncio.create_task(self._send_event_smart(
                EventType.EXECUTION_STARTED,
                EventSeverity.INFO,
                execution_id,
                profile_id,
                "Warming started",
                {"total_actions": len(actions), "batch_id": batch_id},
                requires_manual=False,
                can_retry=False,
                progress_callback=progress_callback
            ))
            
            # ✅ 3. EJECUTAR ACCIONES (con detección ligera de eventos)
            total_actions = len(actions)
            completed = 0
            failed = 0
            
            for i, action in enumerate(actions):
                try:
                    # ✅ SINCRONIZACIÓN (si es batch)
                    if batch_id:
                        try:
                            await asyncio.wait_for(
                                self._sync_wait_at_barrier(batch_id, i, execution_id),
                                timeout=90
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f"⏱️ Sync timeout action {i}, continuing...")
                    
                    # ✅ EJECUTAR ACCIÓN
                    action_timeout = action.get("params", {}).get("timeout", 60)
                    
                    try:
                        success = await asyncio.wait_for(
                            self.action_executor.execute_action(driver, action),
                            timeout=action_timeout + 10
                        )
                        
                        if success:
                            completed += 1
                        else:
                            failed += 1
                            
                            # ✅ DETECTAR EVENTOS Y ESPERAR SI ES LOGIN
                            action_type = action.get("type")
                            if action_type in ["advanced_login", "login"]:
                                logger.warning(f"🔴 Login failed - FORCING event detection")
                                # Esperar 2 segundos para estabilización
                                await asyncio.sleep(2)
                                
                                # ✅ ESPERAR la detección (NO background)
                                await self._detect_and_report_events(
                                    driver, execution_id, profile_id, i, action, progress_callback
                                )
                                
                                # Esperar confirmación de envío
                                await asyncio.sleep(1)
                            else:
                                # Para otros fallos, background está bien
                                asyncio.create_task(
                                    self._detect_and_report_events(
                                        driver, execution_id, profile_id, i, action, progress_callback
                                    )
                                )
                    
                    except asyncio.TimeoutError:
                        logger.error(f"⏱️ Action {i} timeout ({action_timeout}s)")
                        failed += 1
                    
                    # ✅ PROGRESO (sin esperar)
                    progress = int((i + 1) / total_actions * 100)
                    
                    if progress_callback:
                        asyncio.create_task(progress_callback(
                            execution_id,
                            progress,
                            {
                                "action_index": i,
                                "action_type": action.get("type"),
                                "success": success,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        ))
                

                except Exception as e:
                    logger.error(f"❌ Action {i+1} failed: {e}")
                    failed += 1
            
            # ✅ 4. COMPLETADO
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            asyncio.create_task(self._send_event_smart(
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
            ))
            
            logger.info(
                f"✅ Warming completed: execution={execution_id}, "
                f"success={completed}/{total_actions}, duration={duration:.1f}s"
            )
        
        except Exception as e:
            logger.error(f"❌ Warming failed: execution={execution_id}, error={e}")
            
            asyncio.create_task(self._send_event_smart(
                EventType.EXECUTION_FAILED,
                EventSeverity.CRITICAL,
                execution_id,
                profile_id,
                f"Warming failed: {str(e)}",
                {"error": str(e), "error_type": type(e).__name__},
                requires_manual=True,
                can_retry=False,
                progress_callback=progress_callback
            ))
        
        finally:
            # ✅ CERRAR NAVEGADOR (sin esperar demasiado)
            if driver:
                try:
                    await asyncio.wait_for(
                        self.browser_controller.close_browser(profile_id),
                        timeout=10
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ Browser close timeout for profile {profile_id}")
            
            # Limpiar
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            self.event_deduplicator.mark_execution_completed(execution_id)
            self.execution_cache.clear_execution(execution_id)
    
    async def _detect_and_report_events(
        self,
        driver,
        execution_id: int,
        profile_id: str,
        action_index: int,
        action: dict,
        progress_callback: Optional[Callable]
    ):
        """Detecta y reporta eventos (corre en background)"""
        
        try:
            events = await self.event_detector.detect_all_events(
                driver,
                execution_id,
                profile_id,
                computer_id=self.config.COMPUTER_ID,
                action_index=action_index,
                action_type=action.get("type")
            )
            
            for event in events:
                await self._send_detected_event_smart(event, progress_callback)
        
        except Exception as e:
            logger.error(f"Event detection error: {e}")
    
    async def _sync_wait_at_barrier(
        self,
        batch_id: str,
        action_index: int,
        execution_id: int
    ) -> bool:
        """Espera en barrera distribuida"""
        
        logger.debug(
            f"⏸️ Waiting at barrier: batch={batch_id}, action={action_index}"
        )
        
        # TODO: Implementar comunicación con orquestrador
        await asyncio.sleep(0.1)  # Placeholder
        
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
            return
        
        should_report_once = self.execution_cache.should_report_once(
            execution_id,
            event_type
        )
        
        if not should_report_once:
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
            return
        
        should_report_once = self.execution_cache.should_report_once(
            event.execution_id,
            event.event_type
        )
        
        if not should_report_once:
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
            return False
        
        task = self.active_executions[execution_id]
        task.cancel()
        
        self.event_deduplicator.mark_execution_completed(execution_id)
        self.execution_cache.clear_execution(execution_id)
        
        logger.info(f"🛑 Execution {execution_id} cancelled")
        return True
    
    def get_active_count(self) -> int:
        """Retorna cantidad de ejecuciones activas"""
        return len(self.active_executions)