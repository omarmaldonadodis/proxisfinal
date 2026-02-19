# app/services/error_recovery_service.py
"""
Sistema de recuperación automática ante errores
Maneja: reCAPTCHA, IP bloqueada, capacidad excedida, etc.
"""
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger
from datetime import datetime, timedelta

from app.models.warming_script import WarmingExecution, ExecutionStatus
from app.models.profile import Profile, ProfileStatus
from app.models.computer import Computer, ComputerStatus
from app.models.proxy import Proxy, ProxyStatus

class ErrorType:
    """Tipos de errores detectables"""
    RECAPTCHA = "recaptcha"
    IP_BLOCKED = "ip_blocked"
    PROXY_ERROR = "proxy_error"
    BROWSER_CRASH = "browser_crash"
    ADSPOWER_LIMIT = "adspower_limit"
    PROFILE_BLOCKED = "profile_blocked"
    TIMEOUT = "timeout"
    MANUAL_INTERVENTION = "manual_intervention"
    UNKNOWN = "unknown"

class RecoveryStrategy:
    """Estrategias de recuperación"""
    CHANGE_PROXY = "change_proxy"
    CHANGE_PROFILE = "change_profile"
    CHANGE_COMPUTER = "change_computer"
    RETRY_LATER = "retry_later"
    MANUAL_REQUIRED = "manual_required"
    ABORT = "abort"

class ErrorRecoveryService:
    """Servicio de recuperación automática"""
    
    # Computadora principal de emergencia
    FALLBACK_COMPUTER_ID = 1
    
    # Máximo de reintentos por tipo de error
    MAX_RETRIES = {
        ErrorType.RECAPTCHA: 0,  # No reintentar (requiere manual)
        ErrorType.IP_BLOCKED: 3,  # Cambiar IP 3 veces
        ErrorType.PROXY_ERROR: 2,
        ErrorType.BROWSER_CRASH: 2,
        ErrorType.ADSPOWER_LIMIT: 1,
        ErrorType.PROFILE_BLOCKED: 0,
        ErrorType.TIMEOUT: 2,
        ErrorType.MANUAL_INTERVENTION: 0,
        ErrorType.UNKNOWN: 1
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def handle_execution_error(
        self,
        execution_id: int,
        error_type: str,
        error_details: Dict
    ) -> Dict:
        """
        Maneja error de ejecución
        
        Returns:
            {
                "recovered": True/False,
                "strategy": "change_proxy" | "change_profile" | ...,
                "new_execution_id": 123,  # Si se creó nueva ejecución
                "message": "..."
            }
        """
        
        # Obtener ejecución
        result = await self.db.execute(
            select(WarmingExecution).where(WarmingExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            return {
                "recovered": False,
                "strategy": RecoveryStrategy.ABORT,
                "message": "Execution not found"
            }
        
        # Verificar reintentos
        retry_count = error_details.get("retry_count", 0)
        max_retries = self.MAX_RETRIES.get(error_type, 1)
        
        if retry_count >= max_retries:
            logger.warning(
                f"Max retries reached for execution {execution_id} "
                f"(error: {error_type}, retries: {retry_count})"
            )
            return {
                "recovered": False,
                "strategy": RecoveryStrategy.ABORT,
                "message": f"Max retries ({max_retries}) reached"
            }
        
        # Determinar estrategia según tipo de error
        if error_type == ErrorType.RECAPTCHA:
            return await self._handle_recaptcha(execution, error_details)
        
        elif error_type == ErrorType.IP_BLOCKED:
            return await self._handle_ip_blocked(execution, error_details)
        
        elif error_type == ErrorType.PROXY_ERROR:
            return await self._handle_proxy_error(execution, error_details)
        
        elif error_type == ErrorType.BROWSER_CRASH:
            return await self._handle_browser_crash(execution, error_details)
        
        elif error_type == ErrorType.ADSPOWER_LIMIT:
            return await self._handle_adspower_limit(execution, error_details)
        
        elif error_type == ErrorType.PROFILE_BLOCKED:
            return await self._handle_profile_blocked(execution, error_details)
        
        elif error_type == ErrorType.TIMEOUT:
            return await self._handle_timeout(execution, error_details)
        
        else:
            return await self._handle_unknown_error(execution, error_details)
    
    async def _handle_recaptcha(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """
        reCAPTCHA detectado
        
        Estrategia:
        1. Cambiar proxy (nueva IP)
        2. Si persiste, cambiar profile
        3. Si persiste, enviar a computadora principal con flag de intervención manual
        """
        
        retry_count = error_details.get("retry_count", 0)
        
        if retry_count == 0:
            # Primer intento: cambiar proxy
            return await self._retry_with_new_proxy(execution, error_details)
        
        elif retry_count == 1:
            # Segundo intento: cambiar profile
            return await self._retry_with_new_profile(execution, error_details)
        
        else:
            # Requiere intervención manual
            await self._flag_for_manual_intervention(execution)
            
            return {
                "recovered": False,
                "strategy": RecoveryStrategy.MANUAL_REQUIRED,
                "message": "reCAPTCHA persists - manual intervention required"
            }
    
    async def _handle_ip_blocked(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """
        IP bloqueada
        
        Estrategia:
        1. Cambiar proxy inmediatamente
        2. Si no hay proxies, cambiar profile
        3. Si no hay profiles, ir a computadora principal
        """
        
        # Marcar proxy como problemático
        profile = await self._get_profile(execution.profile_id)
        if profile and profile.proxy_id:
            await self._mark_proxy_as_failed(profile.proxy_id)
        
        # Intentar con nuevo proxy
        return await self._retry_with_new_proxy(execution, error_details)
    
    async def _handle_proxy_error(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """Error de proxy (timeout, conexión fallida)"""
        
        profile = await self._get_profile(execution.profile_id)
        if profile and profile.proxy_id:
            await self._mark_proxy_as_failed(profile.proxy_id)
        
        return await self._retry_with_new_proxy(execution, error_details)
    
    async def _handle_browser_crash(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """Navegador cerrado inesperadamente"""
        
        retry_count = error_details.get("retry_count", 0)
        
        if retry_count == 0:
            # Reintentar en mismo profile
            return await self._retry_same_profile(execution, error_details)
        else:
            # Cambiar profile
            return await self._retry_with_new_profile(execution, error_details)
    
    async def _handle_adspower_limit(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """
        AdsPower alcanzó límite de profiles
        
        Estrategia:
        1. Buscar otra computadora con capacidad
        2. Si no hay, ir a computadora principal
        3. Si tampoco, marcar para retry más tarde
        """
        
        # Buscar computadora con capacidad
        result = await self.db.execute(
            select(Computer).where(
                and_(
                    Computer.is_active == True,
                    Computer.status == ComputerStatus.ONLINE,
                    Computer.current_profiles < Computer.max_profiles,
                    Computer.id != execution.computer_id
                )
            ).order_by(Computer.current_profiles.asc())
        )
        
        available_computer = result.scalar_one_or_none()
        
        if available_computer:
            # Mover ejecución a otra computadora
            return await self._retry_on_computer(
                execution,
                available_computer.id,
                error_details
            )
        else:
            # Programar para más tarde
            return {
                "recovered": False,
                "strategy": RecoveryStrategy.RETRY_LATER,
                "message": "No computers with capacity - retry in 30 minutes",
                "retry_after": datetime.utcnow() + timedelta(minutes=30)
            }
    
    async def _handle_profile_blocked(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """Profile bloqueado por el sitio web"""
        
        # Marcar profile como bloqueado
        profile = await self._get_profile(execution.profile_id)
        if profile:
            profile.status = ProfileStatus.ERROR
            profile.notes = f"Blocked at {datetime.utcnow()}: {error_details.get('reason', 'Unknown')}"
            await self.db.commit()
        
        # Cambiar a nuevo profile
        return await self._retry_with_new_profile(execution, error_details)
    
    async def _handle_timeout(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """Timeout en acción"""
        
        retry_count = error_details.get("retry_count", 0)
        
        if retry_count == 0:
            # Reintentar mismo profile
            return await self._retry_same_profile(execution, error_details)
        else:
            # Cambiar profile
            return await self._retry_with_new_profile(execution, error_details)
    
    async def _handle_unknown_error(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """Error desconocido - estrategia conservadora"""
        
        return await self._retry_same_profile(execution, error_details)
    
    # ============================================
    # ESTRATEGIAS DE RETRY
    # ============================================
    
    async def _retry_with_new_proxy(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """Reintentar con nuevo proxy"""
        
        profile = await self._get_profile(execution.profile_id)
        if not profile:
            return {"recovered": False, "message": "Profile not found"}
        
        # Buscar nuevo proxy disponible
        result = await self.db.execute(
            select(Proxy).where(
                and_(
                    Proxy.is_available == True,
                    Proxy.status == ProxyStatus.ACTIVE,
                    Proxy.id != profile.proxy_id,
                    Proxy.country == profile.country  # Mismo país
                )
            ).order_by(Proxy.success_rate.desc()).limit(1)
        )
        
        new_proxy = result.scalar_one_or_none()
        
        if not new_proxy:
            # No hay proxies, cambiar profile
            return await self._retry_with_new_profile(execution, error_details)
        
        # Actualizar profile con nuevo proxy
        profile.proxy_id = new_proxy.id
        await self.db.commit()
        
        # Crear nueva ejecución
        new_execution = await self._clone_execution(
            execution,
            retry_count=error_details.get("retry_count", 0) + 1
        )
        
        return {
            "recovered": True,
            "strategy": RecoveryStrategy.CHANGE_PROXY,
            "new_execution_id": new_execution.id,
            "message": f"Retrying with new proxy: {new_proxy.id}"
        }
    
    async def _retry_with_new_profile(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """Reintentar con nuevo profile"""
        
        # Buscar profile disponible en misma computadora
        result = await self.db.execute(
            select(Profile).where(
                and_(
                    Profile.computer_id == execution.computer_id,
                    Profile.status.in_([ProfileStatus.READY, ProfileStatus.ACTIVE]),
                    Profile.id != execution.profile_id
                )
            ).limit(1)
        )
        
        new_profile = result.scalar_one_or_none()
        
        if not new_profile:
            # No hay profiles, ir a computadora principal
            return await self._retry_on_computer(
                execution,
                self.FALLBACK_COMPUTER_ID,
                error_details
            )
        
        # Crear nueva ejecución con nuevo profile
        new_execution = await self._clone_execution(
            execution,
            profile_id=new_profile.id,
            retry_count=error_details.get("retry_count", 0) + 1
        )
        
        return {
            "recovered": True,
            "strategy": RecoveryStrategy.CHANGE_PROFILE,
            "new_execution_id": new_execution.id,
            "message": f"Retrying with new profile: {new_profile.id}"
        }
    
    async def _retry_on_computer(
        self,
        execution: WarmingExecution,
        computer_id: int,
        error_details: Dict
    ) -> Dict:
        """Reintentar en otra computadora"""
        
        # Buscar profile disponible en computadora destino
        result = await self.db.execute(
            select(Profile).where(
                and_(
                    Profile.computer_id == computer_id,
                    Profile.status.in_([ProfileStatus.READY, ProfileStatus.ACTIVE])
                )
            ).limit(1)
        )
        
        new_profile = result.scalar_one_or_none()
        
        if not new_profile:
            return {
                "recovered": False,
                "strategy": RecoveryStrategy.ABORT,
                "message": f"No available profiles on computer {computer_id}"
            }
        
        # Crear nueva ejecución
        new_execution = await self._clone_execution(
            execution,
            profile_id=new_profile.id,
            computer_id=computer_id,
            retry_count=error_details.get("retry_count", 0) + 1
        )
        
        return {
            "recovered": True,
            "strategy": RecoveryStrategy.CHANGE_COMPUTER,
            "new_execution_id": new_execution.id,
            "message": f"Retrying on computer {computer_id}"
        }
    
    async def _retry_same_profile(
        self,
        execution: WarmingExecution,
        error_details: Dict
    ) -> Dict:
        """Reintentar en mismo profile"""
        
        new_execution = await self._clone_execution(
            execution,
            retry_count=error_details.get("retry_count", 0) + 1
        )
        
        return {
            "recovered": True,
            "strategy": "retry",
            "new_execution_id": new_execution.id,
            "message": "Retrying on same profile"
        }
    
    # ============================================
    # HELPERS
    # ============================================
    
    async def _clone_execution(
        self,
        execution: WarmingExecution,
        profile_id: Optional[int] = None,
        computer_id: Optional[int] = None,
        retry_count: int = 0
    ) -> WarmingExecution:
        """Clona ejecución para retry"""
        
        new_execution = WarmingExecution(
            script_id=execution.script_id,
            profile_id=profile_id or execution.profile_id,
            computer_id=computer_id or execution.computer_id,
            status=ExecutionStatus.QUEUED,
            progress=0,
            actions_completed=0,
            actions_failed=0,
            execution_log=[{
                "type": "retry",
                "original_execution_id": execution.id,
                "retry_count": retry_count,
                "timestamp": datetime.utcnow().isoformat()
            }]
        )
        
        self.db.add(new_execution)
        await self.db.commit()
        await self.db.refresh(new_execution)
        
        return new_execution
    
    async def _get_profile(self, profile_id: int) -> Optional[Profile]:
        """Obtiene profile"""
        result = await self.db.execute(
            select(Profile).where(Profile.id == profile_id)
        )
        return result.scalar_one_or_none()
    
    async def _mark_proxy_as_failed(self, proxy_id: int):
        """Marca proxy como fallido"""
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        if proxy:
            proxy.failed_checks += 1
            proxy.total_checks += 1
            proxy.success_rate = ((proxy.total_checks - proxy.failed_checks) / proxy.total_checks) * 100
            
            if proxy.failed_checks >= 3:
                proxy.status = ProxyStatus.FAILED
                proxy.is_available = False
            
            await self.db.commit()
    
    async def _flag_for_manual_intervention(self, execution: WarmingExecution):
        """Marca ejecución para intervención manual"""
        execution.status = ExecutionStatus.FAILED
        execution.error_message = "MANUAL INTERVENTION REQUIRED"
        
        if not execution.execution_log:
            execution.execution_log = []
        
        execution.execution_log.append({
            "type": "manual_intervention_required",
            "timestamp": datetime.utcnow().isoformat(),
            "reason": "reCAPTCHA or other blocking mechanism detected"
        })
        
        await self.db.commit()
        
        logger.warning(f"Execution {execution.id} flagged for manual intervention")