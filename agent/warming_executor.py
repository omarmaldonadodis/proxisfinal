# agent/warming_executor.py (CON VARIABLES DE SESIÓN)
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
        
        # ✅ Establecer credenciales por defecto
        # TODO: Estas deberían venir del profile o configuración
        self.action_executor.set_session_var("USERNAME", "omaritouv0209@gmail.com")
        self.action_executor.set_session_var("PASSWORD", "Eocm2003!")
        
        # Ejecuciones activas
        self.active_executions: Dict[int, asyncio.Task] = {}
        
        # Semáforo para limitar concurrencia
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_EXECUTIONS)
    
    async def execute(
        self,
        execution_id: int,
        profile_id: int,
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
    
   # agent/warming_executor.py (AGREGAR DETECCIÓN DE ERRORES)

    async def _execute_warming(
        self,
        execution_id: int,
        profile_id: int,
        actions: List[dict],
        progress_callback: Optional[Callable] = None
    ):
        """Ejecuta warming con detección de errores"""
        
        driver = None
        start_time = datetime.utcnow()
        retry_count = 0
        
        try:
            async with self.semaphore:
                logger.info(f"Starting warming: execution_id={execution_id}")
                
                # Abrir navegador
                driver = await self.browser_controller.open_browser(profile_id)
                
                if not driver:
                    raise Exception(f"Failed to open browser for profile {profile_id}")
                
                # Ejecutar acciones
                total_actions = len(actions)
                completed = 0
                failed = 0
                
                # ✅ VARIABLES PARA ERROR DETECTION
                detected_error_type = None
                
                for i, action in enumerate(actions):
                    try:
                        success = await self.action_executor.execute_action(driver, action)
                        
                        if success:
                            completed += 1
                        else:
                            failed += 1
                            
                            # ✅ DETECTAR TIPO DE ERROR
                            detected_error_type = await self._detect_error_type(
                                driver,
                                action
                            )
                            
                            if detected_error_type:
                                logger.warning(f"Error detected: {detected_error_type}")
                        
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
                                    "error_type": detected_error_type,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                    
                    except Exception as e:
                        logger.error(f"Action {i+1} failed: {e}")
                        failed += 1
                        
                        # ✅ DETECTAR ERROR
                        detected_error_type = await self._detect_error_type(
                            driver,
                            action
                        )
                        
                        if progress_callback:
                            await progress_callback(
                                execution_id,
                                int((i + 1) / total_actions * 100),
                                {
                                    "action_index": i,
                                    "action_type": action.get("type"),
                                    "success": False,
                                    "error": str(e),
                                    "error_type": detected_error_type,
                                    "retry_count": retry_count,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                
                # Duración
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # ✅ REPORTAR COMPLETADO (con o sin errores)
                if progress_callback:
                    await progress_callback(
                        execution_id,
                        100,
                        {
                            "completed": True,
                            "total_actions": total_actions,
                            "actions_completed": completed,
                            "actions_failed": failed,
                            "error_type": detected_error_type,
                            "duration_seconds": duration,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                logger.info(f"Warming completed: execution_id={execution_id}")
        
        except Exception as e:
            logger.error(f"Warming failed: execution_id={execution_id}, error={e}")
            
            # ✅ REPORTAR FALLO CON TIPO DE ERROR
            if progress_callback:
                error_type = await self._detect_error_type(driver, None) if driver else "unknown"
                
                await progress_callback(
                    execution_id,
                    0,
                    {
                        "completed": False,
                        "error": str(e),
                        "error_type": error_type,
                        "retry_count": retry_count,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        finally:
            if driver:
                await self.browser_controller.close_browser(profile_id)


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