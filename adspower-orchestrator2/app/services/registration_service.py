from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.computer import Computer, ComputerStatus
from app.models.computer_token import ComputerToken
from app.repositories.computer_repository import ComputerRepository
from loguru import logger
from datetime import datetime

class RegistrationService:
    """Servicio de registro automático de computadoras"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.computer_repo = ComputerRepository(db)
    
    async def register_or_update_computer(
        self,
        hardware_info: Dict
    ) -> Dict[str, any]:
        """
        Registra o actualiza computadora automáticamente
        
        Args:
            hardware_info: {
                "name": "Mac",
                "hostname": "omar-laptop",
                "ip_address": "192.168.1.10",
                "adspower_api_url": "http://192.168.1.10:50325",
                "adspower_api_key": "...",
                "cpu_cores": 8,
                "ram_gb": 16,
                "os_info": "macOS 14.0"
            }
        
        Returns:
            {
                "computer_id": 1,
                "token": "abc123...",
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
            
            # Crear token
            token_obj = ComputerToken(
                computer_id=computer.id,
                token=ComputerToken.generate_token(),
                is_active=True
            )
            
            self.db.add(token_obj)
            await self.db.commit()
            await self.db.refresh(computer)
            
            logger.info(f"✅ New computer registered: {computer.name} (ID: {computer.id})")
            
            return {
                "computer_id": computer.id,
                "token": token_obj.token,
                "is_new": True,
                "message": f"Computer '{computer.name}' registered successfully"
            }
        
        else:
            # Computadora EXISTENTE - ACTUALIZAR INFO
            update_data = {
                "hostname": hardware_info["hostname"],
                "ip_address": hardware_info["ip_address"],  # IP dinámica
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
            
            # Obtener token existente
            result = await self.db.execute(
                select(ComputerToken).where(ComputerToken.computer_id == computer.id)
            )
            token_obj = result.scalar_one_or_none()
            
            if not token_obj:
                # Crear token si no existe (caso raro)
                token_obj = ComputerToken(
                    computer_id=computer.id,
                    token=ComputerToken.generate_token(),
                    is_active=True
                )
                self.db.add(token_obj)
            
            # Actualizar last_used_at del token
            token_obj.last_used_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"✅ Computer updated: {computer.name} (IP: {hardware_info['ip_address']})")
            
            return {
                "computer_id": computer.id,
                "token": token_obj.token,
                "is_new": False,
                "message": f"Computer '{computer.name}' reconnected"
            }
    
    async def validate_token(self, token: str) -> Optional[Computer]:
        """Valida token y retorna computadora"""
        
        result = await self.db.execute(
            select(ComputerToken).where(
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
        
        # Retornar computadora
        result = await self.db.execute(
            select(Computer).where(Computer.id == token_obj.computer_id)
        )
        return result.scalar_one_or_none()
    
    async def revoke_token(self, computer_id: int) -> bool:
        """Revoca token de una computadora"""
        
        result = await self.db.execute(
            select(ComputerToken).where(ComputerToken.computer_id == computer_id)
        )
        token_obj = result.scalar_one_or_none()
        
        if token_obj:
            token_obj.is_active = False
            await self.db.commit()
            logger.info(f"Token revoked for computer {computer_id}")
            return True
        
        return False