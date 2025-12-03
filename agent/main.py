# app/api/v1/warming.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
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

router = APIRouter(prefix="/warming", tags=["Warming"])

# =====================================================
# SCRIPTS ENDPOINTS
# =====================================================

@router.post("/scripts/", response_model=WarmingScriptResponse, status_code=201)
async def create_script(
    script_in: WarmingScriptCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo script de warming"""
    service = WarmingScriptService(db)
    script = await service.create_script(script_in)
    return script

@router.get("/scripts/", response_model=dict)
async def list_scripts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    status: Optional[str] = None,
    is_template: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista scripts de warming"""
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
    """Obtiene plantillas de scripts"""
    service = WarmingScriptService(db)
    templates = await service.get_script_templates()
    return templates

@router.get("/scripts/{script_id}", response_model=WarmingScriptResponse)
async def get_script(
    script_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene script por ID"""
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
    """Actualiza script"""
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
    """Elimina script"""
    service = WarmingScriptService(db)
    success = await service.delete_script(script_id)
    if not success:
        raise HTTPException(status_code=404, detail="Script not found")

# =====================================================
# EXECUTION ENDPOINTS
# =====================================================

@router.post("/execute/batch", response_model=BatchWarmingResponse, status_code=202)
async def execute_batch_warming(
    request: BatchWarmingRequest,
    db: AsyncSession = Depends(get_db)
):
    """Ejecuta warming en batch para múltiples profiles"""
    
    service = WarmingScriptService(db)
    
    # Obtener script
    script = await service.get_script(request.script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # Verificar profiles y crear ejecuciones
    from app.services.profile_service import ProfileService
    from app.services.computer_service import ComputerService
    
    profile_service = ProfileService(db)
    computer_service = ComputerService(db)
    
    executions = []
    
    for profile_id in request.profile_ids:
        # Obtener profile
        profile = await profile_service.get_profile(profile_id)
        if not profile:
            logger.warning(f"Profile {profile_id} not found, skipping")
            continue
        
        # Crear ejecución
        execution = await service.create_execution(
            script_id=request.script_id,
            profile_id=profile_id,
            computer_id=profile.computer_id
        )
        
        executions.append(execution.id)
        
        # Enviar comando al agente si está conectado
        if connection_manager.is_connected(profile.computer_id):
            await connection_manager.execute_warming(
                computer_id=profile.computer_id,
                execution_id=execution.id,
                profile_id=profile_id,
                script_actions=script.actions
            )
        else:
            logger.warning(f"Computer {profile.computer_id} not connected")
    
    # Incrementar uso del script
    await service.increment_script_usage(request.script_id)
    
    return BatchWarmingResponse(
        task_id=f"batch_{request.script_id}_{len(executions)}",
        total_profiles=len(request.profile_ids),
        message=f"Warming started for {len(executions)} profiles",
        executions=executions
    )

@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estado de ejecución"""
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
    """Detiene ejecución de warming"""
    service = WarmingScriptService(db)
    execution = await service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Enviar comando de stop al agente
    if connection_manager.is_connected(execution.computer_id):
        await connection_manager.stop_warming(
            computer_id=execution.computer_id,
            execution_id=execution_id
        )
    
    # Actualizar estado
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
    """Obtiene estado de todos los agentes conectados"""
    connected = connection_manager.get_connected_agents()
    
    agents_status = []
    for computer_id in connected:
        state = connection_manager.get_agent_state(computer_id)
        agents_status.append({
            "computer_id": computer_id,
            "connected": True,
            "state": state
        })
    
    return {
        "total_connected": len(connected),
        "agents": agents_status
    }

@router.post("/agents/{computer_id}/status")
async def request_agent_status(computer_id: int):
    """Solicita estado de un agente específico"""
    if not connection_manager.is_connected(computer_id):
        raise HTTPException(status_code=404, detail="Agent not connected")
    
    await connection_manager.request_status(computer_id)
    return {"message": "Status request sent"}

# =====================================================
# WEBSOCKET ENDPOINT
# =====================================================

@router.websocket("/ws/{computer_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint para agentes"""
    
    # Conectar agente
    await connection_manager.connect(websocket, computer_id)
    
    try:
        while True:
            # Recibir mensaje del agente
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            # Procesar según tipo de mensaje
            if message_type == "heartbeat":
                # Actualizar heartbeat
                connection_manager.last_activity[computer_id] = datetime.utcnow()
                await websocket.send_json({"type": "heartbeat_ack"})
            
            elif message_type == "status_update":
                # Actualizar estado del agente
                connection_manager.update_agent_state(computer_id, message.get("state", {}))
            
            elif message_type == "execution_progress":
                # Actualizar progreso de ejecución
                execution_id = message.get("execution_id")
                progress = message.get("progress")
                log_entry = message.get("log_entry")
                
                service = WarmingScriptService(db)
                await service.update_execution_status(
                    execution_id=execution_id,
                    status="running",
                    progress=progress,
                    log_entry=log_entry
                )
            
            elif message_type == "execution_completed":
                # Ejecución completada
                execution_id = message.get("execution_id")
                result = message.get("result", {})
                
                service = WarmingScriptService(db)
                await service.update_execution_status(
                    execution_id=execution_id,
                    status="completed",
                    progress=100,
                    log_entry=result
                )
            
            elif message_type == "execution_failed":
                # Ejecución fallida
                execution_id = message.get("execution_id")
                error = message.get("error")
                
                service = WarmingScriptService(db)
                await service.update_execution_status(
                    execution_id=execution_id,
                    status="failed",
                    log_entry={"error": error}
                )
            
            else:
                logger.warning(f"Unknown message type from agent {computer_id}: {message_type}")
    
    except WebSocketDisconnect:
        connection_manager.disconnect(computer_id)
        logger.info(f"Agent disconnected: Computer {computer_id}")
    except Exception as e:
        logger.error(f"WebSocket error for computer {computer_id}: {e}")
        connection_manager.disconnect(computer_id)