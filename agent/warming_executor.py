# agent/warming_executor.py (CON VARIABLES DE SESIÓN)
import asyncio
from typing import Dict, List, Callable, Optional
from loguru import logger
from datetime import datetime
from action_executor import ActionExecutor

from event_detector import UniversalEventDetector
from event_model import ExecutionEvent
from event_types import EventType, EventSeverity
import uuid


class WarmingExecutor:
    """Ejecutor de warming scripts"""
    
    def __init__(self, config, browser_controller):
        self.config = config
        self.browser_controller = browser_controller
        self.action_executor = ActionExecutor(config)
        
        # ✅ Establecer credenciales por defecto
        # TODO: Estas deberían venir del profile o configuración
        self.action_executor.set_session_var("USERNAME", "omaritouv0209@gmail.com")
        self.action_executor.set_session_var("PASSWORD", "Eocm2003!")
        
        # Ejecuciones activas
        self.active_executions: Dict[int, asyncio.Task] = {}
        
        # Semáforo para limitar concurrencia
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_EXECUTIONS)

        self.event_detector = UniversalEventDetector(config.COMPUTER_ID)

    
    async def execute(
        self,
        execution_id: int,
        profile_id: str,
        actions: List[dict],
        progress_callback: Optional[Callable] = None
    ):
        """Ejecuta warming script"""
        
        task = asyncio.create_task(
            self._execute_warming(
                execution_id,
                profile_id,
                actions,
                progress_callback
            )
        )
        
        self.active_executions[execution_id] = task
        
        try:
            await task
        finally:
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    

    async def _execute_warming(
        self,
        execution_id: int,
        profile_id: str,
        actions: List[dict],
        progress_callback: Optional[Callable] = None
    ):
        """Ejecuta warming CON detección de eventos en tiempo real"""
        
        driver = None
        start_time = datetime.utcnow()
        
        try:
            async with self.semaphore:
                logger.info(f"Starting warming: execution_id={execution_id}")
                
                # Abrir navegador
                driver = await self.browser_controller.open_browser(profile_id)
                
                if not driver:
                    # ✅ EVENTO: Browser no abrió
                    await self._send_event(
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
                
                # ✅ EVENTO: Ejecución iniciada
                await self._send_event(
                    EventType.EXECUTION_STARTED,
                    EventSeverity.INFO,
                    execution_id,
                    profile_id,
                    "Warming execution started",
                    {"total_actions": len(actions)},
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
                        # ✅ DETECTAR EVENTOS ANTES de ejecutar acción
                        events_before = await self.event_detector.detect_all_events(
                            driver,
                            execution_id,
                            profile_id,
                            action_index=i,
                            action_type=action.get("type")
                        )
                        
                        # Enviar eventos detectados
                        for event in events_before:
                            await self._send_detected_event(event, progress_callback)
                            
                            # Si es CRÍTICO y no se puede reintentar, abortar
                            if event.severity == EventSeverity.CRITICAL and not event.can_retry:
                                logger.error(f"Critical event, aborting: {event.message}")
                                raise Exception(f"Critical event: {event.event_type}")
                        
                        # Ejecutar acción
                        success = await self.action_executor.execute_action(driver, action)
                        
                        if success:
                            completed += 1
                        else:
                            failed += 1
                        
                        # ✅ DETECTAR EVENTOS DESPUÉS de ejecutar acción
                        events_after = await self.event_detector.detect_all_events(
                            driver,
                            execution_id,
                            profile_id,
                            action_index=i,
                            action_type=action.get("type")
                        )
                        
                        for event in events_after:
                            await self._send_detected_event(event, progress_callback)
                            
                            # Manejar eventos críticos
                            if event.severity == EventSeverity.CRITICAL:
                                if event.can_retry:
                                    logger.warning(f"Critical event (retriable): {event.message}")
                                    # El orquestador decidirá si reintentar
                                else:
                                    logger.error(f"Critical event (non-retriable): {event.message}")
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
                                    "events_detected": len(events_after),
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                    
                    except Exception as e:
                        logger.error(f"Action {i+1} failed: {e}")
                        failed += 1
                        
                        # Detectar eventos de error
                        error_events = await self.event_detector.detect_all_events(
                            driver,
                            execution_id,
                            profile_id,
                            action_index=i,
                            action_type=action.get("type")
                        )
                        
                        for event in error_events:
                            await self._send_detected_event(event, progress_callback)
                
                # ✅ EVENTO: Completado exitosamente
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                await self._send_event(
                    EventType.EXECUTION_COMPLETED,
                    EventSeverity.INFO,
                    execution_id,
                    profile_id,
                    f"Warming completed: {completed}/{total_actions} actions successful",
                    {
                        "total_actions": total_actions,
                        "completed": completed,
                        "failed": failed,
                        "duration_seconds": duration
                    },
                    requires_manual=False,
                    can_retry=False,
                    progress_callback=progress_callback
                )
                
                logger.info(f"Warming completed: execution_id={execution_id}")
        
        except Exception as e:
            logger.error(f"Warming failed: execution_id={execution_id}, error={e}")
            
            # ✅ EVENTO: Fallo crítico
            await self._send_event(
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
    
    async def _send_event(
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
        """Envía evento simple al orquestador"""
        
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
    
    async def _send_detected_event(
        self,
        event: ExecutionEvent,
        progress_callback: Optional[Callable] = None
    ):
        """Envía evento detectado al orquestador"""
        
        if progress_callback:
            await progress_callback(
                event.execution_id,
                0,  # Progress no cambia por eventos
                {
                    "event": event.model_dump(),
                    "is_event": True  # Flag para identificar que es un evento
                }
            )


    async def _detect_error_type(
        self,
        driver,
        action: Optional[dict]
    ) -> Optional[str]:
        """
        ✅ DETECTA TIPO DE ERROR
        
        Returns:
            "recaptcha" | "ip_blocked" | "proxy_error" | 
            "browser_crash" | "timeout" | "unknown"
        """
        
        if not driver:
            return "browser_crash"
        
        try:
            # 1. Detectar reCAPTCHA
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            for iframe in iframes:
                if iframe.is_displayed() and iframe.size['width'] > 0:
                    return "recaptcha"
            
            # 2. Detectar IP bloqueada
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            blocked_indicators = [
                "access denied",
                "blocked",
                "banned",
                "ip address",
                "too many requests",
                "rate limit"
            ]
            
            for indicator in blocked_indicators:
                if indicator in page_text:
                    return "ip_blocked"
            
            # 3. Detectar error de proxy
            if action and action.get("type") == "navigate":
                current_url = driver.current_url
                if current_url == "about:blank" or "err_" in current_url.lower():
                    return "proxy_error"
            
            # 4. Timeout
            if action and action.get("params", {}).get("timeout"):
                return "timeout"
            
            return "unknown"
        
        except:
            return "browser_crash"
    
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