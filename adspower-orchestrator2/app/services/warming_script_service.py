# app/services/warming_script_service.py
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.warming_script import WarmingScript, WarmingExecution, ExecutionStatus
from app.schemas.warming_script import WarmingScriptCreate, WarmingScriptUpdate
from loguru import logger

class WarmingScriptService:
    """Servicio para gestión de scripts de warming"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_script(self, script_in: WarmingScriptCreate) -> WarmingScript:
        """Crea un nuevo script de warming"""
        
        # Convertir actions a dict
        actions_dict = [action.model_dump() for action in script_in.actions]
        
        script = WarmingScript(
            name=script_in.name,
            description=script_in.description,
            category=script_in.category,
            actions=actions_dict,
            duration_minutes=script_in.duration_minutes,
            randomize_order=script_in.randomize_order,
            repeat_count=script_in.repeat_count,
            tags=script_in.tags,
            is_template=script_in.is_template,
            status="active"
        )
        
        self.db.add(script)
        await self.db.commit()
        await self.db.refresh(script)
        
        logger.info(f"Warming script created: {script.name} (ID: {script.id})")
        return script
    
    async def get_script(self, script_id: int) -> Optional[WarmingScript]:
        """Obtiene script por ID"""
        result = await self.db.execute(
            select(WarmingScript).where(WarmingScript.id == script_id)
        )
        return result.scalar_one_or_none()
    
    async def list_scripts(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        status: Optional[str] = None,
        is_template: Optional[bool] = None
    ) -> tuple[List[WarmingScript], int]:
        """Lista scripts con filtros"""
        
        query = select(WarmingScript)
        count_query = select(func.count()).select_from(WarmingScript)
        
        conditions = []
        if category:
            conditions.append(WarmingScript.category == category)
        if status:
            conditions.append(WarmingScript.status == status)
        if is_template is not None:
            conditions.append(WarmingScript.is_template == is_template)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get items
        query = query.offset(skip).limit(limit).order_by(WarmingScript.created_at.desc())
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        
        return items, total
    
    async def update_script(
        self,
        script_id: int,
        script_in: WarmingScriptUpdate
    ) -> Optional[WarmingScript]:
        """Actualiza script"""
        
        script = await self.get_script(script_id)
        if not script:
            raise ValueError(f"Script {script_id} not found")
        
        update_data = script_in.model_dump(exclude_unset=True)
        
        # Convertir actions si están presentes
        if "actions" in update_data and update_data["actions"]:
            update_data["actions"] = [
                action.model_dump() if hasattr(action, 'model_dump') else action
                for action in update_data["actions"]
            ]
        
        for field, value in update_data.items():
            setattr(script, field, value)
        
        await self.db.commit()
        await self.db.refresh(script)
        
        logger.info(f"Warming script updated: {script.name}")
        return script
    
    async def delete_script(self, script_id: int) -> bool:
        """Elimina script"""
        
        script = await self.get_script(script_id)
        if not script:
            return False
        
        await self.db.delete(script)
        await self.db.commit()
        
        logger.info(f"Warming script deleted: {script.name}")
        return True
    
    async def create_execution(
        self,
        script_id: int,
        profile_id: int,
        computer_id: int
    ) -> WarmingExecution:
        """Crea una ejecución de warming"""
        
        execution = WarmingExecution(
            script_id=script_id,
            profile_id=profile_id,
            computer_id=computer_id,
            status=ExecutionStatus.QUEUED
        )
        
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        
        logger.info(f"Warming execution created: Script {script_id}, Profile {profile_id}")
        return execution
    
    async def get_execution(self, execution_id: int) -> Optional[WarmingExecution]:
        """Obtiene ejecución por ID"""
        result = await self.db.execute(
            select(WarmingExecution).where(WarmingExecution.id == execution_id)
        )
        return result.scalar_one_or_none()
    
    async def update_execution_status(
        self,
        execution_id: int,
        status: ExecutionStatus,
        progress: Optional[int] = None,
        log_entry: Optional[Dict] = None
    ) -> bool:
        """Actualiza estado de ejecución"""
        
        execution = await self.get_execution(execution_id)
        if not execution:
            return False
        
        execution.status = status
        
        if progress is not None:
            execution.progress = progress
        
        if log_entry:
            if execution.execution_log is None:
                execution.execution_log = []
            execution.execution_log.append(log_entry)
        
        await self.db.commit()
        return True
    
    async def get_script_templates(self) -> List[WarmingScript]:
        """Obtiene plantillas de scripts"""
        result = await self.db.execute(
            select(WarmingScript).where(
                WarmingScript.is_template == True,
                WarmingScript.status == "active"
            )
        )
        return list(result.scalars().all())
    
    async def increment_script_usage(self, script_id: int) -> bool:
        """Incrementa contador de uso del script"""
        script = await self.get_script(script_id)
        if script:
            script.times_used += 1
            await self.db.commit()
            return True
        return False