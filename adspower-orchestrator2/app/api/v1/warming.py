# app/api/v1/warming.py
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
# SCRIPTS ENDPOINTS
# =====================================================

@router.post("/scripts/", response_model=WarmingScriptResponse, status_code=201)
async def create_script(
    script_in: WarmingScriptCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo script de warming.
    
    ## Tipos de Acciones Disponibles:
    
    - **navigate**: Navegar a URL
    - **click**: Hacer click en elemento
    - **type**: Escribir texto
    - **scroll**: Hacer scroll
    - **wait**: Esperar tiempo
    - **wait_element**: Esperar elemento
    - **hover**: Pasar mouse sobre elemento
    - **select**: Seleccionar dropdown
    - **press_key**: Presionar tecla
    - **screenshot**: Tomar captura
    - **switch_tab**: Cambiar pestaña
    - **close_tab**: Cerrar pestaña
    - **execute_script**: Ejecutar JavaScript
    - **random_mouse**: Movimiento aleatorio de mouse
    - **human_typing**: Tipeo humanizado con errores
    - **search_google**: Búsqueda en Google
    - **login**: Login genérico
    
    ## Ejemplo:
    
    ```json
    {
      "name": "Google Search Test",
      "description": "Script de prueba",
      "category": "search",
      "duration_minutes": 10,
      "actions": [
        {
          "type": "navigate",
          "params": {"url": "https://google.com"}
        },
        {
          "type": "wait",
          "params": {"duration": 2}
        },
        {
          "type": "search_google",
          "params": {"query": "test"}
        }
      ]
    }
    ```
    """
    service = WarmingScriptService(db)
    script = await service.create_script(script_in)
    return script

@router.get("/scripts/", response_model=dict)
async def list_scripts(
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(100, ge=1, le=1000, description="Limit"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    is_template: Optional[bool] = Query(None, description="Solo plantillas"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos los scripts de warming con filtros opcionales.
    
    ## Filtros:
    
    - **category**: search, social_media, ecommerce, news, etc.
    - **status**: draft, active, archived
    - **is_template**: true/false
    """
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
    """
    Obtiene solo las plantillas de scripts activas.
    
    Las plantillas son scripts marcados como reutilizables.
    """
    service = WarmingScriptService(db)
    templates = await service.get_script_templates()
    return templates

@router.get("/scripts/{script_id}", response_model=WarmingScriptResponse)
async def get_script(
    script_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un script específico por ID"""
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
    """Actualiza un script existente"""
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
    """Elimina un script"""
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
    """
    Ejecuta warming en batch para múltiples profiles.
    
    ## Flujo:
    
    1. Crea ejecuciones para cada profile
    2. Envía comandos a los agentes vía WebSocket
    3. Los agentes ejecutan las acciones
    4. Reportan progreso en tiempo real
    
    ## Ejemplo:
    
    ```json
    {
      "script_id": 1,
      "profile_ids": [1, 2, 3, 4, 5],
      "max_parallel": 5
    }
    ```
    """
    
    service = WarmingScriptService(db)
    
    # Obtener script
    script = await service.get_script(request.script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # Verificar profiles y crear ejecuciones
    from app.services.profile_service import ProfileService
    
    profile_service = ProfileService(db)
    
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
            logger.info(f"Warming command sent to agent: Computer {profile.computer_id}")
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
    """
    Obtiene estado y progreso de una ejecución.
    
    Incluye:
    - Estado actual
    - Progreso (0-100)
    - Acciones completadas/fallidas
    - Log detallado de cada acción
    - Errores si los hay
    """
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
    """
    Detiene una ejecución de warming en progreso.
    
    Envía comando de cancelación al agente.
    """
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
    """
    Obtiene estado de todos los agentes conectados.
    
    Muestra:
    - Computer ID
    - Estado de conexión
    - Navegadores activos
    - CPU y memoria
    """
    connected = connection_manager.get_connected_agents()
    
    agents_status = []
    for computer_id in connected:
        state = connection_manager.get_agent_state(computer_id)
        agents_status.append({
            "computer_id": computer_id,
            "connected": True,
            "state": state or {}
        })
    
    return {
        "total_connected": len(connected),
        "agents": agents_status
    }

@router.post("/agents/{computer_id}/status")
async def request_agent_status(computer_id: int):
    """
    Solicita actualización de estado de un agente específico.
    
    El agente responderá con su estado actual vía WebSocket.
    """
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
    computer_id: int
):
    """
    WebSocket endpoint para comunicación en tiempo real con agentes.
    
    ## Protocolo:
    
    ### Mensajes del Agente al Orquestador:
    
    - **heartbeat**: Mantiene conexión viva
    - **status_update**: Actualización de estado
    - **execution_progress**: Progreso de ejecución
    - **execution_completed**: Ejecución completada
    - **execution_failed**: Ejecución fallida
    
    ### Mensajes del Orquestador al Agente:
    
    - **connected**: Confirmación de conexión
    - **execute_warming**: Ejecutar warming
    - **stop_warming**: Detener warming
    - **status_request**: Solicitar estado
    
    ## URL:
    
    ```
    ws://localhost:8000/api/v1/warming/ws/{computer_id}
    ```
    """
    
    # Conectar agente
    await connection_manager.connect(websocket, computer_id)
    
    # Obtener session de DB
    from app.database import AsyncSessionLocal
    
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
                
                async with AsyncSessionLocal() as db:
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
                
                async with AsyncSessionLocal() as db:
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
                
                async with AsyncSessionLocal() as db:
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