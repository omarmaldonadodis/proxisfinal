# app/models/computer_token.py
from sqlalchemy import Text, Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import secrets

class ComputerToken(Base):
    """Tokens de autenticación para computadoras"""
    __tablename__ = "computer_tokens"
    
    id = Column(Integer, primary_key=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), unique=True, nullable=False)
    token = Column(Text, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    
    # Relationship
    computer = relationship("Computer", back_populates="token")
    
    @staticmethod
    def generate_token():
        """Genera token seguro de 64 caracteres"""
        return secrets.token_urlsafe(48)  # Genera ~64 caracteres
