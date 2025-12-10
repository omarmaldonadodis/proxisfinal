# app/core/jwt_manager.py
"""
Sistema de gestión de JWT para autenticación de agentes
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from loguru import logger
from app.config import settings

class JWTManager:
    """Gestor de tokens JWT para agentes"""
    
    # Tipo de tokens
    TOKEN_TYPE_AGENT = "agent"
    TOKEN_TYPE_API = "api"
    
    @staticmethod
    def create_agent_token(
        computer_id: int,
        computer_name: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Crea token JWT para agente (sin expiración por defecto)
        
        Args:
            computer_id: ID de la computadora
            computer_name: Nombre de la computadora
            expires_delta: Tiempo de expiración (None = sin expiración)
        """
        
        to_encode = {
            "sub": str(computer_id),
            "type": JWTManager.TOKEN_TYPE_AGENT,
            "computer_id": computer_id,
            "computer_name": computer_name,
            "iat": datetime.utcnow()
        }
        
        # Si se especifica expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
            to_encode["exp"] = expire
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        logger.info(f"JWT created for agent: {computer_name} (ID: {computer_id})")
        return encoded_jwt
    
    @staticmethod
    def verify_agent_token(token: str) -> Optional[Dict]:
        """
        Verifica token de agente
        
        Returns:
            {
                "computer_id": 1,
                "computer_name": "Mac",
                "type": "agent"
            }
            None si token inválido
        """
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            # Verificar que sea token de agente
            if payload.get("type") != JWTManager.TOKEN_TYPE_AGENT:
                logger.warning("Invalid token type")
                return None
            
            return {
                "computer_id": payload.get("computer_id"),
                "computer_name": payload.get("computer_name"),
                "type": payload.get("type")
            }
        
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
    
    @staticmethod
    def create_api_token(
        user_id: str,
        permissions: list = None,
        expires_delta: timedelta = None
    ) -> str:
        """
        Crea token JWT para API (con expiración)
        
        Args:
            user_id: ID del usuario
            permissions: Lista de permisos
            expires_delta: Tiempo de expiración
        """
        
        if expires_delta is None:
            expires_delta = timedelta(hours=24)
        
        expire = datetime.utcnow() + expires_delta
        
        to_encode = {
            "sub": user_id,
            "type": JWTManager.TOKEN_TYPE_API,
            "permissions": permissions or [],
            "iat": datetime.utcnow(),
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def verify_api_token(token: str) -> Optional[Dict]:
        """Verifica token de API"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            if payload.get("type") != JWTManager.TOKEN_TYPE_API:
                return None
            
            return payload
        
        except JWTError:
            return None
    
    @staticmethod
    def revoke_token(token: str) -> bool:
        """
        Marca token como revocado (guardar en Redis/DB)
        
        TODO: Implementar blacklist en Redis
        """
        # Por ahora, retornar True
        # En producción, guardar en Redis con TTL
        return True