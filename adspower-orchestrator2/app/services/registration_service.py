# app/services/registration_service.py - VERSIÓN CON JWT
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.computer import Computer, ComputerStatus
from app.models.computer_token import ComputerToken
from app.repositories.computer_repository import ComputerRepository
from app.core.jwt_manager import JWTManager  # ✅ NUEVO
from loguru import logger
from datetime import datetime

class RegistrationService:
    """Servicio de registro automático con JWT"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.computer_repo = ComputerRepository(db)
    
    async def register_or_update_computer(
        self,
        hardware_info: Dict
    ) -> Dict[str, any]:
        """
        Registra o actualiza computadora y genera JWT
        
        Returns:
            {
                "computer_id": 1,
                "token": "eyJ...",  # JWT token
                "is_new": True/False,
                "message": "..."
            }
        """
        
        # Buscar por nombre de computadora
        computer = await self.computer_repo.get_by_name(hardware_info["name"])
        
        is_new = False
        
        if not computer:
            # Nueva computadora - CREAR
            is_new = True
            
            computer_data = {
                "name": hardware_info["name"],
                "hostname": hardware_info["hostname"],
                "ip_address": hardware_info["ip_address"],
                "adspower_api_url": hardware_info["adspower_api_url"],
                "adspower_api_key": hardware_info["adspower_api_key"],
                "cpu_cores": hardware_info.get("cpu_cores"),
                "ram_gb": hardware_info.get("ram_gb"),
                "os_info": hardware_info.get("os_info"),
                "status": ComputerStatus.ONLINE,
                "is_active": True,
                "last_seen_at": datetime.utcnow()
            }
            
            computer = await self.computer_repo.create(computer_data)
            await self.db.flush()
            
            # ✅ Crear JWT token (sin expiración)
            jwt_token = JWTManager.create_agent_token(
                computer_id=computer.id,
                computer_name=computer.name
            )
            
            # Guardar token en DB (para poder revocarlo)
            token_obj = ComputerToken(
                computer_id=computer.id,
                token=jwt_token,
                is_active=True
            )
            
            self.db.add(token_obj)
            await self.db.commit()
            await self.db.refresh(computer)
            
            logger.info(f"✅ New computer registered with JWT: {computer.name} (ID: {computer.id})")
            
            return {
                "computer_id": computer.id,
                "token": jwt_token,
                "is_new": True,
                "message": f"Computer '{computer.name}' registered successfully"
            }
        
        else:
            # Computadora EXISTENTE - ACTUALIZAR INFO
            update_data = {
                "hostname": hardware_info["hostname"],
                "ip_address": hardware_info["ip_address"],
                "adspower_api_url": hardware_info["adspower_api_url"],
                "adspower_api_key": hardware_info.get("adspower_api_key", computer.adspower_api_key),
                "cpu_cores": hardware_info.get("cpu_cores", computer.cpu_cores),
                "ram_gb": hardware_info.get("ram_gb", computer.ram_gb),
                "os_info": hardware_info.get("os_info", computer.os_info),
                "status": ComputerStatus.ONLINE,
                "is_active": True,
                "last_seen_at": datetime.utcnow()
            }
            
            await self.computer_repo.update(computer.id, update_data)
            
            # ✅ Obtener JWT existente
            result = await self.db.execute(
                select(ComputerToken).where(
                    ComputerToken.computer_id == computer.id,
                    ComputerToken.is_active == True
                )
            )
            token_obj = result.scalar_one_or_none()
            
            if not token_obj:
                # ✅ Crear nuevo JWT si no existe
                jwt_token = JWTManager.create_agent_token(
                    computer_id=computer.id,
                    computer_name=computer.name
                )
                
                token_obj = ComputerToken(
                    computer_id=computer.id,
                    token=jwt_token,
                    is_active=True
                )
                self.db.add(token_obj)
            
            # Actualizar last_used_at del token
            token_obj.last_used_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"✅ Computer reconnected with JWT: {computer.name} (IP: {hardware_info['ip_address']})")
            
            return {
                "computer_id": computer.id,
                "token": token_obj.token,
                "is_new": False,
                "message": f"Computer '{computer.name}' reconnected"
            }
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """
        Valida JWT token
        
        Returns:
            {
                "valid": True,
                "computer_id": 1,
                "computer_name": "..."
            }
            None si inválido
        """
        
        # ✅ Verificar JWT
        payload = JWTManager.verify_agent_token(token)
        
        if not payload:
            return None
        
        computer_id = payload.get("computer_id")
        
        # Verificar que el token sigue activo en DB
        result = await self.db.execute(
            select(ComputerToken).where(
                ComputerToken.computer_id == computer_id,
                ComputerToken.token == token,
                ComputerToken.is_active == True
            )
        )
        token_obj = result.scalar_one_or_none()
        
        if not token_obj:
            return None
        
        # Actualizar last_used_at
        token_obj.last_used_at = datetime.utcnow()
        await self.db.commit()
        
        # Retornar info de computadora
        result = await self.db.execute(
            select(Computer).where(Computer.id == computer_id)
        )
        computer = result.scalar_one_or_none()
        
        if not computer:
            return None
        
        return {
            "valid": True,
            "computer_id": computer.id,
            "computer_name": computer.name
        }
    
    async def revoke_token(self, computer_id: int) -> bool:
        """
        Revoca JWT token de una computadora
        """
        
        result = await self.db.execute(
            select(ComputerToken).where(ComputerToken.computer_id == computer_id)
        )
        token_obj = result.scalar_one_or_none()
        
        if token_obj:
            token_obj.is_active = False
            await self.db.commit()
            logger.info(f"JWT token revoked for computer {computer_id}")
            return True
        
        return False