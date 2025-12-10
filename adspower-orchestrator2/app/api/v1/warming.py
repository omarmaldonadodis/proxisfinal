# adspower-orchestrator2/app/api/v1/warming.py - VERSIÓN COMPLETA INTEGRADA
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.services.warming_script_service import WarmingScriptService
from app.services.scheduler_service import SchedulerService
from app.schemas.warming_script import (
    WarmingScriptCreate,
    WarmingScriptUpdate,
    WarmingScriptResponse,
    BatchWarmingRequest,
    BatchWarmingResponse
)
from app.schemas.scheduled_warming import (
    ScheduledWarmingCreate,
    ScheduledWarmingResponse
)
from app.websocket.manager import connection_manager
from app.core.jwt_manager import JWTManager
from loguru import logger
import json

router = APIRouter(prefix="/warming", tags=["🔥 Warming Scripts"])

# =====================================================
# 🔐 JWT AUTHENTICATION HELPER
# =====================================================

async def verify_agent_token(authorization: Optional[str] = Header(None)) -> dict:
    """Verifica JWT token de agente para WebSocket"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        # Extraer token (formato: "Bearer <token>")
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization.replace("Bearer ", "")
        
        # Verificar token
        payload = JWTManager.verify_agent_token(token)
        
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return payload
    
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# =====================================================
# SCRIPTS ENDPOINTS
# =====================================================

@router.post("/scripts/", response_model=WarmingScriptResponse, status_code=201)
async def create_script(
    script_in: WarmingScriptCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo script de warming."""
    service = WarmingScriptService(db)
    script = await service.create_script(script_in)
    return script

@router.get("/scripts/", response_model=dict)
async def list_scripts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_template: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Lista scripts con filtros."""
    service = WarmingScriptService(db)
    scripts, total = await service.list_scripts(
        skip=skip,
        limit=limit,
        category=category,
        status=status,
        is_template=is_template
    )
    return {"total": total, "items": scripts}

@router.get("/scripts/templates/", response_model=List[WarmingScriptResponse])
async def get_templates(db: AsyncSession = Depends(get_db)):
    """Obtiene plantillas de scripts."""
    service = WarmingScriptService(db)
    templates = await service.get_script_templates()
    return templates

@router.get("/scripts/{script_id}", response_model=WarmingScriptResponse)
async def get_script(
    script_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene script por ID."""
    service = WarmingScriptService(db)
    script = await service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script

@router.patch("/scripts/{script_id}", response_model=WarmingScriptResponse)
async def update_script(
    script_id: int,
    script_in: WarmingScriptUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza script."""
    service = WarmingScriptService(db)
    try:
        script = await service.update_script(script_id, script_in)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        return script
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/scripts/{script_id}", status_code=204)
async def delete_script(
    script_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina script."""
    service = WarmingScriptService(db)
    success = await service.delete_script(script_id)
    if not success:
        raise HTTPException(status_code=404, detail="Script not found")

# =====================================================
# ✅ SCHEDULED WARMING ENDPOINTS (NUEVO)
# =====================================================

@router.post("/schedule/", response_model=ScheduledWarmingResponse, status_code=201)
async def schedule_warming(
    schedule_in: ScheduledWarmingCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    📅 Programa ejecución de warming
    
    Permite programar warming scripts para ejecutarse:
    - Una vez (frequency: once)
    - Diariamente (frequency: daily)
    - Semanalmente (frequency: weekly)
    - Mensualmente (frequency: monthly)
    - Cron personalizado (frequency: custom)
    """
    scheduler_service = SchedulerService(db)
    
    try:
        scheduled = await scheduler_service.create_scheduled_warming(schedule_in)
        return scheduled
    except Exception as e:
        logger.error(f"Error scheduling warming: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schedule/", response_model=dict)
async def list_scheduled_warmings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Lista warmings programados"""
    from sqlalchemy import select, func
    from app.models.scheduled_warming import ScheduledWarming
    
    query = select(ScheduledWarming)
    count_query = select(func.count()).select_from(ScheduledWarming)
    
    if is_active is not None:
        from sqlalchemy import and_
        query = query.where(ScheduledWarming.is_active == is_active)
        count_query = count_query.where(ScheduledWarming.is_active == is_active)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.offset(skip).limit(limit).order_by(ScheduledWarming.next_execution_at)
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    return {"total": total, "items": items}

@router.delete("/schedule/{scheduled_id}", status_code=204)
async def cancel_scheduled_warming(
    scheduled_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Cancela warming programado"""
    from sqlalchemy import select
    from app.models.scheduled_warming import ScheduledWarming
    
    result = await db.execute(
        select(ScheduledWarming).where(ScheduledWarming.id == scheduled_id)
    )
    scheduled = result.scalar_one_or_none()
    
    if not scheduled:
        raise HTTPException(status_code=404, detail="Scheduled warming not found")
    
    scheduled.is_active = False
    await db.commit()

# =====================================================
# EXECUTION ENDPOINT (con error recovery)
# =====================================================

@router.post("/execute/batch", response_model=BatchWarmingResponse, status_code=202)
async def execute_batch_warming(
    request: BatchWarmingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ VERSIÓN MEJORADA - Distribución inteligente con error recovery
    """
    
    service = WarmingScriptService(db)
    
    # 1. Obtener script
    script = await service.get_script(request.script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # 2. Obtener profiles y agrupar por computadora
    from app.services.profile_service import ProfileService
    
    profile_service = ProfileService(db)
    
    profiles_by_computer = {}
    profile_map = {}
    
    for profile_id in request.profile_ids:
        profile = await profile_service.get_profile(profile_id)
        if not profile:
            logger.warning(f"Profile {profile_id} not found, skipping")
            continue
        
        computer_id = profile.computer_id
        
        if computer_id not in profiles_by_computer:
            profiles_by_computer[computer_id] = []
        
        profiles_by_computer[computer_id].append(profile)
        profile_map[profile_id] = profile
    
    if not profiles_by_computer:
        raise HTTPException(status_code=400, detail="No valid profiles found")
    
    # 3. Verificar computadoras ONLINE
    connected_agents = connection_manager.get_connected_agents()
    
    # 4. Crear ejecuciones y distribuir
    executions = []
    warnings = []
    profiles_executed = 0
    profiles_skipped = 0
    
    for computer_id, profiles in profiles_by_computer.items():
        
        if computer_id not in connected_agents:
            warning_msg = f"⚠️ Computer {computer_id} is OFFLINE - {len(profiles)} profiles skipped"
            warnings.append(warning_msg)
            logger.warning(warning_msg)
            profiles_skipped += len(profiles)
            continue
        
        for profile in profiles:
            # Crear ejecución en DB
            execution = await service.create_execution(
                script_id=request.script_id,
                profile_id=profile.id,
                computer_id=profile.computer_id
            )
            
            executions.append(execution.id)
            profiles_executed += 1
            
            # Enviar comando al agente
            success = await connection_manager.execute_warming(
                computer_id=profile.computer_id,
                execution_id=execution.id,
                profile_id=profile.adspower_id,
                script_actions=script.actions
            )
            
            if success:
                logger.info(f"✓ Warming command sent: Computer {profile.computer_id}, Profile {profile.id}")
            else:
                logger.error(f"✗ Failed to send warming command: Computer {profile.computer_id}")
    
    # 5. Incrementar uso del script
    await service.increment_script_usage(request.script_id)
    
    # 6. Construir respuesta
    message = f"Warming started for {profiles_executed}/{len(request.profile_ids)} profiles"
    
    if warnings:
        message += f" | {profiles_skipped} profiles skipped (computers offline)"
    
    return BatchWarmingResponse(
        task_id=f"batch_{request.script_id}_{len(executions)}",
        total_profiles=len(request.profile_ids),
        message=message,
        executions=executions
    )

# =====================================================
# EXECUTION STATUS
# =====================================================

@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estado de ejecución."""
    service = WarmingScriptService(db)
    execution = await service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution

@router.post("/executions/{execution_id}/stop", status_code=200)
async def stop_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Detiene ejecución."""
    service = WarmingScriptService(db)
    execution = await service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if connection_manager.is_connected(execution.computer_id):
        await connection_manager.stop_warming(
            computer_id=execution.computer_id,
            execution_id=execution_id
        )
    
    await service.update_execution_status(
        execution_id=execution_id,
        status="cancelled"
    )
    
    return {"message": "Warming stopped"}

# =====================================================
# AGENTS STATUS
# =====================================================

@router.get("/agents/status")
async def get_agents_status():
    """Obtiene estado de TODOS los agentes"""
    from app.database import AsyncSessionLocal
    from app.services.computer_service import ComputerService
    
    async with AsyncSessionLocal() as db:
        computer_service = ComputerService(db)
        
        computers, _ = await computer_service.list_computers(limit=1000)
        
        connected_agents = connection_manager.get_connected_agents()
        
        agents_status = []
        
        for computer in computers:
            is_connected = computer.id in connected_agents
            
            state = None
            if is_connected:
                state = connection_manager.get_agent_state(computer.id)
            
            agents_status.append({
                "computer_id": computer.id,
                "computer_name": computer.name,
                "connected": is_connected,
                "status": "online" if is_connected else "offline",
                "state": state or {},
                "ip_address": computer.ip_address,
                "max_profiles": computer.max_profiles,
                "current_profiles": computer.current_profiles
            })
        
        return {
            "total_computers": len(computers),
            "online": len(connected_agents),
            "offline": len(computers) - len(connected_agents),
            "agents": agents_status
        }

@router.post("/agents/{computer_id}/status")
async def request_agent_status(computer_id: int):
    """Solicita estado de agente."""
    if not connection_manager.is_connected(computer_id):
        raise HTTPException(status_code=404, detail="Agent not connected")
    
    await connection_manager.request_status(computer_id)
    return {"message": "Status request sent"}

# =====================================================
# 🔐 WEBSOCKET ENDPOINT (CON JWT AUTH)
# =====================================================

@router.websocket("/ws/{computer_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    computer_id: int
):
    """
    WebSocket endpoint para agentes (CON AUTENTICACIÓN JWT)
    
    El agente debe enviar Authorization header con JWT token
    """
    
    # ✅ VERIFICAR JWT EN QUERY PARAMS (WebSocket no soporta headers custom)
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    
    # Verificar token
    payload = JWTManager.verify_agent_token(token)
    
    if not payload or payload.get("computer_id") != computer_id:
        await websocket.close(code=1008, reason="Invalid authentication token")
        return
    
    # Token válido - conectar
    await connection_manager.connect(websocket, computer_id)
    
    from app.database import AsyncSessionLocal
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "heartbeat":
                connection_manager.last_activity[computer_id] = datetime.utcnow()
                await websocket.send_json({"type": "heartbeat_ack"})
            
            elif message_type == "status_update":
                connection_manager.update_agent_state(computer_id, message.get("state", {}))
            
            elif message_type == "execution_progress":
                execution_id = message.get("execution_id")
                progress = message.get("progress")
                log_entry = message.get("log_entry")
                
                async with AsyncSessionLocal() as db:
                    service = WarmingScriptService(db)
                    await service.update_execution_status(
                        execution_id=execution_id,
                        status="running",
                        progress=progress,
                        log_entry=log_entry
                    )
            
            elif message_type == "execution_completed":
                execution_id = message.get("execution_id")
                result = message.get("result", {})
                
                async with AsyncSessionLocal() as db:
                    service = WarmingScriptService(db)
                    await service.update_execution_status(
                        execution_id=execution_id,
                        status="completed",
                        progress=100,
                        log_entry=result
                    )
            
            elif message_type == "execution_failed":
                execution_id = message.get("execution_id")
                error = message.get("error")
                error_type = message.get("error_type", "unknown")
                
                # ✅ ACTIVAR ERROR RECOVERY
                from app.services.error_recovery_service import ErrorRecoveryService
                
                async with AsyncSessionLocal() as db:
                    recovery_service = ErrorRecoveryService(db)
                    
                    recovery_result = await recovery_service.handle_execution_error(
                        execution_id=execution_id,
                        error_type=error_type,
                        error_details={
                            "error": error,
                            "retry_count": message.get("retry_count", 0)
                        }
                    )
                    
                    logger.info(f"Error recovery: {recovery_result}")
                    
                    # Si no se recuperó, marcar como failed
                    if not recovery_result.get("recovered"):
                        service = WarmingScriptService(db)
                        await service.update_execution_status(
                            execution_id=execution_id,
                            status="failed",
                            log_entry={"error": error, "error_type": error_type}
                        )
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        connection_manager.disconnect(computer_id)
        logger.info(f"Agent disconnected: Computer {computer_id}")
    except Exception as e:
        logger.error(f"WebSocket error for computer {computer_id}: {e}")
        connection_manager.disconnect(computer_id)