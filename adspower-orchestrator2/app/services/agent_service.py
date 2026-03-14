# app/services/agent_service.py
from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from datetime import datetime, timezone
from loguru import logger

from app.models.agent_session import AgentSession, BrowserEvent, SessionStatus, BrowserEventType
from app.models.profile_assignment import ProfileAssignment, AgentToken
from app.models.profile import Profile
from app.models.computer import Computer
from app.schemas.agent import (
    OpenBrowserRequest,
    SessionCloseRequest,
    BrowserEventCreate,
    AgentRegisterRequest,
    SessionMetricsUpdate
)
from app.integrations.adspower_client import AdsPowerClient
from app.core.connection_manager import connection_manager
from app.config import settings


class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================
    # REGISTRO DE EJECUTABLE
    # ========================================

    async def register_agent_computer(self, data: AgentRegisterRequest) -> Dict:
        """
        El ejecutable se registra al iniciar.
        Reutiliza el registro de Computer existente.
        """
        from app.services.registration_service import RegistrationService
        reg_service = RegistrationService(self.db)

        result = await reg_service.register_or_update_computer({
            "name": data.name,
            "hostname": data.hostname,
            "ip_address": data.ip_address,
            "adspower_api_url": data.adspower_api_url,
            "adspower_api_key": data.adspower_api_key,
            "os_info": data.os_info,
            "cpu_cores": data.cpu_cores,
            "ram_gb": data.ram_gb
        })

        return result

    # ========================================
    # TOKENS DE AGENTE
    # ========================================

    async def create_agent_token(self, agent_name: str, notes: Optional[str] = None) -> AgentToken:
        """Admin crea un token para un nuevo agente"""
        # Verificar que no exista
        result = await self.db.execute(
            select(AgentToken).where(AgentToken.agent_name == agent_name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"Ya existe un agente con nombre '{agent_name}'")

        token = AgentToken(
            agent_name=agent_name,
            token=AgentToken.generate_token(),
            notes=notes,
            is_active=True
        )
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)

        logger.info(f"✅ Agente creado: {agent_name}")
        return token

    async def get_agent_by_token(self, token: str) -> Optional[AgentToken]:
        """Valida y retorna el agente por su token"""
        result = await self.db.execute(
            select(AgentToken).where(
                AgentToken.token == token,
                AgentToken.is_active == True
            )
        )
        agent = result.scalar_one_or_none()

        if agent:
            # Actualizar last_used_at
            agent.last_used_at = datetime.utcnow()
            await self.db.commit()

        return agent

    async def list_agent_tokens(self) -> List[AgentToken]:
        result = await self.db.execute(
            select(AgentToken).order_by(AgentToken.agent_name)
        )
        return list(result.scalars().all())

    # ========================================
    # ASSIGNMENTS
    # ========================================

    async def get_assignments_for_agent(self, agent_id: int) -> List[Dict]:
        """
        Retorna las asignaciones activas de un agente
        con información enriquecida (nombre del perfil, estado de sesión activa)
        """
        result = await self.db.execute(
            select(ProfileAssignment).where(
                ProfileAssignment.agent_id == agent_id,
                ProfileAssignment.is_active == True
            )
        )
        assignments = list(result.scalars().all())

        enriched = []
        for assignment in assignments:
            # Verificar si hay sesión activa para este assignment
            session_result = await self.db.execute(
                select(AgentSession).where(
                    AgentSession.assignment_id == assignment.id,
                    AgentSession.status.in_([SessionStatus.ACTIVE.value, SessionStatus.OPENING.value])

                )
            )
            active_session = session_result.scalar_one_or_none()

            # Obtener nombre del perfil
            profile_result = await self.db.execute(
                select(Profile).where(Profile.id == assignment.profile_id)
            )
            profile = profile_result.scalar_one_or_none()

            enriched.append({
                "id": assignment.id,
                "profile_id": assignment.profile_id,
                "profile_name": profile.name if profile else "Desconocido",
                "target_url": assignment.target_url,
                "assignment_name": assignment.assignment_name,
                "requires_auth": assignment.requires_auth,
                "active_session": {
                    "id": active_session.id,
                    "status": active_session.status,
                    "opened_at": active_session.opened_at,
                    "pages_visited": active_session.pages_visited,
                    "total_data_mb": active_session.total_data_mb
                } if active_session else None
            })

        return enriched

    # ========================================
    # ABRIR NAVEGADOR
    # ========================================

    async def request_open_browser(
        self,
        assignment_id: int,
        computer_id: int,
        agent: AgentToken
    ) -> Dict:
        """
        El agente hace click en 'Abrir navegador':
        1. Verifica que la asignación es válida
        2. Crea la sesión en estado OPENING o PENDING_AUTH
        3. Envía comando al ejecutable vía WebSocket
        """

        # 1. Verificar assignment
        result = await self.db.execute(
            select(ProfileAssignment).where(
                ProfileAssignment.id == assignment_id,
                ProfileAssignment.agent_id == agent.id,
                ProfileAssignment.is_active == True
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise ValueError("Asignación no encontrada o no tienes acceso")

        # 2. Verificar que no hay sesión activa para este assignment
        existing_result = await self.db.execute(
            select(AgentSession).where(
                AgentSession.assignment_id == assignment_id,
                AgentSession.status.in_([SessionStatus.ACTIVE.value, SessionStatus.OPENING.value])

            )
        )
        if existing_result.scalar_one_or_none():
            raise ValueError("Ya hay una sesión activa para esta asignación")

        # 3. Obtener perfil
        profile_result = await self.db.execute(
            select(Profile).where(Profile.id == assignment.profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            raise ValueError("Perfil no encontrado")

        # 4. Determinar estado inicial
        initial_status = (
            SessionStatus.PENDING_AUTH
            if assignment.requires_auth
            else SessionStatus.OPENING
        )

        # 5. Crear sesión
        session = AgentSession(
            assignment_id=assignment_id,
            profile_id=assignment.profile_id,
            computer_id=computer_id,
            agent_name=agent.agent_name,
            target_url=assignment.target_url,
            adspower_profile_id=profile.adspower_id,
            status=initial_status,
            requested_at=datetime.utcnow()
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info(
            f"📋 Sesión creada: ID={session.id}, "
            f"agente={agent.agent_name}, "
            f"perfil={profile.adspower_id}, "
            f"estado={initial_status}"
        )

        # 6. Si no requiere auth, enviar comando al agente ahora
        if initial_status == SessionStatus.OPENING:
            await self._send_open_command(session, profile)

        # 7. Notificar admins
        from app.core.connection_manager import connection_manager
        await connection_manager.broadcast_to_admins({
            "type": "session_created",
            "session": {
                "id": session.id,
                "agent_name": agent.agent_name,
                "profile_id": profile.id,
                "target_url": assignment.target_url,
                "status": initial_status,
                "computer_id": computer_id
            }
        })

        return {
            "session_id": session.id,
            "status": initial_status,
            "requires_auth": assignment.requires_auth,
            "message": (
                "Esperando autorización del administrador"
                if assignment.requires_auth
                else "Abriendo navegador..."
            )
        }

    async def _send_open_command(self, session: AgentSession, profile: Profile):
        """Envía el comando de apertura al ejecutable"""
        sent = await connection_manager.send_command_to_agent(
            computer_id=session.computer_id,
            command="open_browser",
            payload={
                "session_id": session.id,
                "profile_id": profile.adspower_id,
                "target_url": session.target_url
            }
        )

        if not sent:
            # El agente no está conectado vía WS, intentar directo vía HTTP
            logger.warning(
                f"⚠️ Agente {session.computer_id} no conectado por WS. "
                f"Intentando apertura directa..."
            )
            await self._open_browser_direct(session, profile)

    async def _open_browser_direct(self, session: AgentSession, profile: Profile):
        """
        Fallback: abre directamente vía AdsPower API local
        (cuando el ejecutable no está instalado o no está conectado)
        """
        try:
            # Usar la URL/key centralizada de settings
            client = AdsPowerClient(
                api_url=settings.ADSPOWER_DEFAULT_API_URL,
                api_key=settings.ADSPOWER_DEFAULT_API_KEY
            )

            result = await client.open_browser(
                profile_id=profile.adspower_id,
                new_first_tab=1
            )

            session.status = SessionStatus.ACTIVE
            session.opened_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"✅ Navegador abierto directamente: sesión {session.id}")

        except Exception as e:
            logger.error(f"❌ Error abriendo navegador directamente: {e}")
            session.status = SessionStatus.CRASHED
            await self.db.commit()

    # ========================================
    # AUTORIZACIÓN DE ADMIN
    # ========================================

    async def authorize_session(self, session_id: int, admin_name: str) -> Dict:
        """Admin autoriza una sesión PENDING_AUTH"""
        session = await self._get_session(session_id)

        if session.status != SessionStatus.PENDING_AUTH:
            raise ValueError(f"La sesión no está pendiente de autorización (estado: {session.status})")

        profile_result = await self.db.execute(
            select(Profile).where(Profile.id == session.profile_id)
        )
        profile = profile_result.scalar_one_or_none()

        session.status = SessionStatus.OPENING
        session.authorized_by = admin_name
        await self.db.commit()

        # Enviar comando al agente
        await self._send_open_command(session, profile)

        # Notificar al agente via WS de admin que fue autorizado
        await connection_manager.broadcast_to_admins({
            "type": "session_authorized",
            "session_id": session_id,
            "authorized_by": admin_name
        })

        return {"session_id": session_id, "status": "authorized"}

    async def deny_session(self, session_id: int, admin_name: str, reason: str) -> Dict:
        """Admin rechaza una sesión"""
        session = await self._get_session(session_id)

        session.status = SessionStatus.DENIED
        session.authorized_by = admin_name
        session.denial_reason = reason
        session.closed_at = datetime.utcnow()
        await self.db.commit()

        await connection_manager.broadcast_to_admins({
            "type": "session_denied",
            "session_id": session_id
        })

        return {"session_id": session_id, "status": "denied"}

    # ========================================
    # EVENTOS Y CIERRE
    # ========================================

    async def mark_session_active(self, session_id: int) -> Dict:
        """El ejecutable confirma que el navegador se abrió"""
        session = await self._get_session(session_id)
        session.status = SessionStatus.ACTIVE
        session.opened_at = datetime.utcnow()
        await self.db.commit()

        await connection_manager.broadcast_to_admins({
            "type": "session_active",
            "session_id": session_id,
            "opened_at": session.opened_at.isoformat()
        })

        return {"session_id": session_id, "status": "active"}

    async def record_browser_event(
        self,
        session_id: int,
        event_data: BrowserEventCreate
    ) -> Dict:
        """Registra un evento del navegador"""
        session = await self._get_session(session_id)

        event = BrowserEvent(
            session_id=session_id,
            event_type=event_data.event_type,
            url=event_data.url,
            page_title=event_data.page_title,
            extra_data=event_data.extra_data
        )
        self.db.add(event)

        # Actualizar contadores en sesión
        if event_data.event_type == BrowserEventType.NAVIGATION:
            session.pages_visited = (session.pages_visited or 0) + 1
            session.last_url = event_data.url
            session.last_url_at = datetime.utcnow()

        await self.db.commit()

        # Notificar admins en tiempo real
        await connection_manager.broadcast_to_admins({
            "type": "browser_event",
            "session_id": session_id,
            "agent_name": session.agent_name,
            "event": {
                "type": event_data.event_type,
                "url": event_data.url,
                "title": event_data.page_title
            }
        })

        return {"recorded": True}

    async def update_session_metrics(self, metrics: SessionMetricsUpdate) -> Dict:
        """El ejecutable actualiza métricas en tiempo real"""
        session = await self._get_session(metrics.session_id)

        session.data_sent_mb = metrics.data_sent_mb
        session.data_received_mb = metrics.data_received_mb
        session.total_data_mb = metrics.data_sent_mb + metrics.data_received_mb
        session.pages_visited = metrics.pages_visited
        session.browser_health = metrics.browser_health

        if metrics.current_url:
            session.last_url = metrics.current_url
            session.last_url_at = datetime.utcnow()

        if metrics.cpu_percent:
            session.local_cpu_percent = metrics.cpu_percent
        if metrics.ram_mb:
            session.local_ram_mb = metrics.ram_mb

        await self.db.commit()

        return {"updated": True}

    async def close_session(
        self,
        session_id: int,
        close_data: SessionCloseRequest
    ) -> Dict:
        """Cierra una sesión y guarda métricas finales"""
        session = await self._get_session(session_id)

        now = datetime.utcnow()
        session.status = (
            SessionStatus.CRASHED
            if close_data.crash_reason
            else SessionStatus.CLOSED
        )
        session.closed_at = now
        session.data_sent_mb = close_data.data_sent_mb
        session.data_received_mb = close_data.data_received_mb
        session.total_data_mb = close_data.data_sent_mb + close_data.data_received_mb
        session.pages_visited = close_data.pages_visited

        if session.opened_at:
            session.duration_seconds = int(
                (now - session.opened_at.replace(tzinfo=None)).total_seconds()
            )

        if close_data.browser_pid:
            session.browser_pid = close_data.browser_pid

        await self.db.commit()

        logger.info(
            f"✅ Sesión cerrada: ID={session_id}, "
            f"duración={session.duration_seconds}s, "
            f"datos={session.total_data_mb:.2f}MB"
        )

        await connection_manager.broadcast_to_admins({
            "type": "session_closed",
            "session_id": session_id,
            "agent_name": session.agent_name,
            "duration_seconds": session.duration_seconds,
            "total_data_mb": session.total_data_mb
        })

        return {
            "session_id": session_id,
            "duration_seconds": session.duration_seconds,
            "total_data_mb": session.total_data_mb
        }

    # ========================================
    # CONSULTAS ADMIN
    # ========================================

    async def get_active_sessions(self) -> List[AgentSession]:
        result = await self.db.execute(
            select(AgentSession).where(
                AgentSession.status.in_([SessionStatus.ACTIVE.value, SessionStatus.OPENING.value])

            ).order_by(AgentSession.requested_at.desc())
        )
        return list(result.scalars().all())

    async def get_session_history(
        self,
        skip: int = 0,
        limit: int = 50,
        agent_name: Optional[str] = None,
        computer_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Tuple[List[AgentSession], int]:

        query = select(AgentSession)
        count_query = select(func.count()).select_from(AgentSession)

        conditions = []
        if agent_name:
            conditions.append(AgentSession.agent_name == agent_name)
        if computer_id:
            conditions.append(AgentSession.computer_id == computer_id)
        if date_from:
            conditions.append(AgentSession.requested_at >= date_from)
        if date_to:
            conditions.append(AgentSession.requested_at <= date_to)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total = (await self.db.execute(count_query)).scalar()
        query = query.order_by(AgentSession.requested_at.desc()).offset(skip).limit(limit)
        items = list((await self.db.execute(query)).scalars().all())

        return items, total

    async def get_dashboard_summary(self) -> Dict:
        """Resumen para el panel del admin"""
        # Sesiones activas ahora
        active_count = (await self.db.execute(
            select(func.count(AgentSession.id)).where(
                AgentSession.status == SessionStatus.ACTIVE.value
            )
        )).scalar()

        # Sesiones pendientes de auth
        pending_count = (await self.db.execute(
            select(func.count(AgentSession.id)).where(
                AgentSession.status == SessionStatus.OPENING
            )
        )).scalar()

        # Total datos consumidos hoy
        from datetime import date
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_data = (await self.db.execute(
            select(func.sum(AgentSession.total_data_mb)).where(
                AgentSession.requested_at >= today_start
            )
        )).scalar()

        # Agentes online (conectados por WebSocket)
        online_agents = list(connection_manager.agent_connections.keys())

        return {
            "active_sessions": active_count or 0,
            "pending_auth": pending_count or 0,
            "total_data_today_mb": round(today_data or 0, 2),
            "online_agents": len(online_agents),
            "online_agent_ids": online_agents,
            "live_metrics": connection_manager.live_metrics
        }

    # ========================================
    # HELPERS
    # ========================================

    async def _get_session(self, session_id: int) -> AgentSession:
        result = await self.db.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Sesión {session_id} no encontrada")
        return session