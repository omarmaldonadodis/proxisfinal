# app/api/v1/warming.py - VERSIÓN MEJORADA
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.services.warming_script_service import WarmingScriptService
from app.schemas.warming_script import (
    WarmingScriptCreate,
    WarmingScriptUpdate,
    WarmingScriptResponse,
    BatchWarmingRequest,
    BatchWarmingResponse
)
from app.websocket.manager import connection_manager
from loguru import logger
import json

router = APIRouter(prefix="/warming", tags=["🔥 Warming Scripts"])

# =====================================================
# SCRIPTS ENDPOINTS (sin cambios)
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
# ✅ EXECUTION ENDPOINT MEJORADO
# =====================================================

@router.post("/execute/batch", response_model=BatchWarmingResponse, status_code=202)
async def execute_batch_warming(
    request: BatchWarmingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ VERSIÓN MEJORADA - Distribución inteligente entre computadoras
    
    ## Flujo:
    
    1. Obtiene script
    2. Verifica profiles y sus computadoras asignadas
    3. Agrupa profiles por computadora
    4. Verifica qué computadoras están online (conectadas vía WebSocket)
    5. Distribuye ejecuciones solo a computadoras online
    6. Si una computadora no está online, muestra advertencia
    7. Envía comandos simultáneos a todos los agentes
    """
    
    service = WarmingScriptService(db)
    
    # 1. Obtener script
    script = await service.get_script(request.script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # 2. Obtener profiles y agrupar por computadora
    from app.services.profile_service import ProfileService
    
    profile_service = ProfileService(db)
    
    profiles_by_computer = {}  # {computer_id: [profiles]}
    profile_map = {}  # {profile_id: profile_obj}
    
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
        raise HTTPException(
            status_code=400,
            detail="No valid profiles found"
        )
    
    # 3. ✅ Verificar computadoras ONLINE
    connected_agents = connection_manager.get_connected_agents()
    
    logger.info(f"Connected agents: {connected_agents}")
    logger.info(f"Profiles distribution: {[(cid, len(ps)) for cid, ps in profiles_by_computer.items()]}")
    
    # 4. Crear ejecuciones y distribuir
    executions = []
    warnings = []
    profiles_executed = 0
    profiles_skipped = 0
    
    for computer_id, profiles in profiles_by_computer.items():
        
        # ✅ Verificar si la computadora está online
        if computer_id not in connected_agents:
            warning_msg = f"⚠️ Computer {computer_id} is OFFLINE - {len(profiles)} profiles skipped"
            warnings.append(warning_msg)
            logger.warning(warning_msg)
            profiles_skipped += len(profiles)
            continue
        
        # ✅ Computadora ONLINE - Crear ejecuciones
        for profile in profiles:
            # Crear ejecución en DB
            execution = await service.create_execution(
                script_id=request.script_id,
                profile_id=profile.id,
                computer_id=profile.computer_id
            )
            
            executions.append(execution.id)
            profiles_executed += 1
            
            # ✅ Enviar comando al agente
            success = await connection_manager.execute_warming(
                computer_id=profile.computer_id,
                execution_id=execution.id,
                profile_id=profile.adspower_id,  # Usar adspower_id
                script_actions=script.actions
            )
            
            if success:
                logger.info(f"✓ Warming command sent: Computer {profile.computer_id}, Profile {profile.id}")
            else:
                logger.error(f"✗ Failed to send warming command: Computer {profile.computer_id}")
    
    # 5. Incrementar uso del script
    await service.increment_script_usage(request.script_id)
    
    # 6. ✅ Construir respuesta con información detallada
    message = f"Warming started for {profiles_executed}/{len(request.profile_ids)} profiles"
    
    if warnings:
        message += f" | {profiles_skipped} profiles skipped (computers offline)"
    
    return BatchWarmingResponse(
        task_id=f"batch_{request.script_id}_{len(executions)}",
        total_profiles=len(request.profile_ids),
        message=message,
        executions=executions
    )

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
# ✅ AGENTS STATUS - MEJORADO
# =====================================================

@router.get("/agents/status")
async def get_agents_status():
    """
    ✅ Obtiene estado de TODOS los agentes (online y offline)
    """
    from app.database import AsyncSessionLocal
    from app.services.computer_service import ComputerService
    
    async with AsyncSessionLocal() as db:
        computer_service = ComputerService(db)
        
        # Obtener TODAS las computadoras
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
# WEBSOCKET ENDPOINT (sin cambios mayores)
# =====================================================

@router.websocket("/ws/{computer_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    computer_id: int
):
    """WebSocket endpoint para agentes."""
    
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
                
                async with AsyncSessionLocal() as db:
                    service = WarmingScriptService(db)
                    await service.update_execution_status(
                        execution_id=execution_id,
                        status="failed",
                        log_entry={"error": error}
                    )
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        connection_manager.disconnect(computer_id)
        logger.info(f"Agent disconnected: Computer {computer_id}")
    except Exception as e:
        logger.error(f"WebSocket error for computer {computer_id}: {e}")
        connection_manager.disconnect(computer_id)
