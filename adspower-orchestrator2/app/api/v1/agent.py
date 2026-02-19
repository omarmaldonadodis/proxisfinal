# app/api/v1/agent.py
"""
Endpoints usados por:
1. El ejecutable instalado en cada computadora (registro, WebSocket, eventos)
2. La web del agente (ver asignaciones, abrir navegador)
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from loguru import logger

from app.database import get_db
from app.services.agent_service import AgentService
from app.schemas.agent import (
    OpenBrowserRequest,
    SessionCloseRequest,
    BrowserEventCreate,
    AgentRegisterRequest,
    SessionMetricsUpdate
)
from app.core.connection_manager import connection_manager

router = APIRouter(prefix="/agent", tags=["🤖 Agent"])


# ========================================
# AUTENTICACIÓN DEL AGENTE (helper)
# ========================================

async def get_current_agent(
    x_agent_token: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """Dependency: valida el token del agente en el header"""
    service = AgentService(db)
    agent = await service.get_agent_by_token(x_agent_token)
    if not agent:
        raise HTTPException(status_code=401, detail="Token de agente inválido")
    return agent


# ========================================
# REGISTRO DEL EJECUTABLE
# ========================================

@router.post("/register")
async def register_computer(
    data: AgentRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    El ejecutable llama esto al iniciar.
    Registra o actualiza la computadora y devuelve el JWT token.
    """
    service = AgentService(db)
    result = await service.register_agent_computer(data)
    return result


# ========================================
# WEBSOCKET PERSISTENTE DEL EJECUTABLE
# ========================================

@router.websocket("/ws/{computer_id}")
async def websocket_agent(
    websocket: WebSocket,
    computer_id: int
):
    """
    Conexión WebSocket persistente entre el ejecutable y el servidor.
    Usado para:
    - Recibir comandos del admin (open_browser, close_browser)
    - Enviar métricas en tiempo real
    - Reportar eventos del navegador
    """
    await connection_manager.connect_agent(websocket, computer_id)

    try:
        while True:
            data = await websocket.receive_json()
            await connection_manager.handle_agent_message(computer_id, data)

    except WebSocketDisconnect:
        connection_manager.disconnect_agent(computer_id)
        logger.info(f"Agente {computer_id} desconectado del WebSocket")

    except Exception as e:
        logger.error(f"Error en WebSocket del agente {computer_id}: {e}")
        connection_manager.disconnect_agent(computer_id)


# ========================================
# WEB DEL AGENTE
# ========================================

@router.get("/my-assignments")
async def get_my_assignments(
    agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    El agente ve sus asignaciones activas.
    Incluye si ya hay una sesión abierta.
    """
    service = AgentService(db)
    assignments = await service.get_assignments_for_agent(agent.id)
    return {
        "agent_name": agent.agent_name,
        "assignments": assignments
    }


@router.post("/open-browser")
async def open_browser(
    request: OpenBrowserRequest,
    agent=Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    El agente hace click en 'Abrir Navegador'.
    Crea la sesión y envía el comando al ejecutable.
    """
    service = AgentService(db)
    try:
        result = await service.request_open_browser(
            assignment_id=request.assignment_id,
            computer_id=request.computer_id,
            agent=agent
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# EVENTOS Y MÉTRICAS (llamados por el ejecutable)
# ========================================

@router.post("/session/{session_id}/active")
async def mark_session_active(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """El ejecutable confirma que el navegador se abrió correctamente"""
    service = AgentService(db)
    try:
        return await service.mark_session_active(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/session/{session_id}/event")
async def report_event(
    session_id: int,
    event: BrowserEventCreate,
    db: AsyncSession = Depends(get_db)
):
    """El ejecutable reporta un evento del navegador (navegación, click, etc.)"""
    service = AgentService(db)
    try:
        return await service.record_browser_event(session_id, event)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/session/{session_id}/metrics")
async def update_metrics(
    session_id: int,
    metrics: SessionMetricsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """El ejecutable actualiza métricas en tiempo real cada N segundos"""
    metrics.session_id = session_id
    service = AgentService(db)
    try:
        return await service.update_session_metrics(metrics)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/session/{session_id}/close")
async def close_session(
    session_id: int,
    data: SessionCloseRequest,
    db: AsyncSession = Depends(get_db)
):
    """El ejecutable reporta que el navegador fue cerrado"""
    service = AgentService(db)
    try:
        return await service.close_session(session_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))