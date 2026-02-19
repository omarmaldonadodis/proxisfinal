# adspower-orchestrator2/app/api/v1/events.py
from fastapi import APIRouter, Depends, Query, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional, Dict
from app.database import get_db
from app.models.execution_event import ExecutionEventDB, EventSeverityDB
from loguru import logger


import asyncio

router = APIRouter(prefix="/events", tags=["Execution Events"])

@router.get("/")
async def list_events(
    execution_id: Optional[int] = Query(None),
    computer_id: Optional[int] = Query(None),
    severity: Optional[EventSeverityDB] = Query(None),
    requires_manual: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Lista eventos de ejecución"""
    
    query = select(ExecutionEventDB)
    count_query = select(func.count()).select_from(ExecutionEventDB)
    
    conditions = []
    if execution_id:
        conditions.append(ExecutionEventDB.execution_id == execution_id)
    if computer_id:
        conditions.append(ExecutionEventDB.computer_id == computer_id)
    if severity:
        conditions.append(ExecutionEventDB.severity == severity)
    if requires_manual is not None:
        conditions.append(ExecutionEventDB.requires_manual_intervention == requires_manual)
    
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    # Count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get items
    query = query.offset(skip).limit(limit).order_by(ExecutionEventDB.created_at.desc())
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    return {
        "total": total,
        "items": items,
        "filters": {
            "execution_id": execution_id,
            "computer_id": computer_id,
            "severity": severity,
            "requires_manual": requires_manual
        }
    }

@router.get("/critical")
async def get_critical_events(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Eventos críticos que requieren atención"""
    
    query = select(ExecutionEventDB).where(
        and_(
            ExecutionEventDB.severity == EventSeverityDB.CRITICAL,
            ExecutionEventDB.requires_manual_intervention == True
        )
    ).order_by(ExecutionEventDB.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    return {
        "count": len(items),
        "events": items
    }

# Store de eventos en memoria para broadcast
event_subscribers: Dict[int, WebSocket] = {}

@router.websocket("/ws/events")
async def events_websocket(websocket: WebSocket):
    """
    WebSocket para eventos en tiempo real
    Cliente se suscribe para recibir eventos críticos
    """
    
    await websocket.accept()
    client_id = id(websocket)
    event_subscribers[client_id] = websocket
    
    logger.info(f"Event subscriber connected: {client_id}")
    
    try:
        while True:
            # Mantener conexión viva
            data = await websocket.receive_text()
            
            # Responder a ping
            if data == "ping":
                await websocket.send_text("pong")
    
    except Exception as e:
        logger.error(f"Event subscriber error: {e}")
    
    finally:
        if client_id in event_subscribers:
            del event_subscribers[client_id]
        logger.info(f"Event subscriber disconnected: {client_id}")


async def broadcast_event(event_data: dict):
    """Broadcast evento a todos los clientes conectados"""
    
    disconnected = []
    
    for client_id, websocket in event_subscribers.items():
        try:
            await websocket.send_json({
                "type": "event",
                "data": event_data
            })
        except:
            disconnected.append(client_id)
    
    # Limpiar desconectados
    for client_id in disconnected:
        if client_id in event_subscribers:
            del event_subscribers[client_id]