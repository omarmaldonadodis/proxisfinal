# app/api/v1/registration.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.registration_service import RegistrationService
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/registration", tags=["Registration"])

class ComputerRegistrationRequest(BaseModel):
    """Datos de registro de computadora"""
    name: str
    hostname: str
    ip_address: str
    adspower_api_url: str
    adspower_api_key: str
    cpu_cores: Optional[int] = None
    ram_gb: Optional[int] = None
    os_info: Optional[str] = None

class TokenValidationRequest(BaseModel):
    token: str

@router.post("/register")
async def register_computer(
    request: ComputerRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    📝 Registro automático de computadora
    
    - Si es nueva: crea computadora y genera token
    - Si existe: actualiza IP y datos, retorna token existente
    """
    service = RegistrationService(db)
    
    result = await service.register_or_update_computer(
        request.model_dump()
    )
    
    return result

@router.post("/validate")
async def validate_token(
    request: TokenValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    service = RegistrationService(db)
    
    computer = await service.validate_token(request.token)
    
    if not computer:
        return {
            "valid": False,
            "message": "Invalid or inactive token"
        }
    
    return {
        "valid": True,
        "computer_id": computer["computer_id"],
        "computer_name": computer["computer_name"],
        "message": "Token valid"
    }


@router.post("/revoke/{computer_id}")
async def revoke_token(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Revoca token de computadora"""
    service = RegistrationService(db)
    
    success = await service.revoke_token(computer_id)
    
    if not success:
        return {
            "success": False,
            "message": "Token not found"
        }
    
    return {
        "success": True,
        "message": f"Token revoked for computer {computer_id}"
    }

