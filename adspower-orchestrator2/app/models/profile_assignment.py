# app/models/profile_assignment.py
"""
ProfileAssignment: el admin asigna qué perfil usa qué agente y con qué URL
Un agente es un miembro del equipo identificado por nombre + token
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import secrets


class AgentToken(Base):
    """
    Token de acceso para cada agente (miembro del equipo)
    El admin los crea, el agente los usa para acceder a la web
    """
    __tablename__ = "agent_tokens"

    id = Column(Integer, primary_key=True)
    agent_name = Column(String(255), nullable=False, unique=True)
    token = Column(String(64), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))

    # Relationships
    assignments = relationship("ProfileAssignment", back_populates="agent", cascade="all, delete-orphan")

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)


class ProfileAssignment(Base):
    """
    Asignación de perfil AdsPower a un agente con una URL objetivo
    Un perfil puede tener múltiples asignaciones (a diferentes agentes o URLs)
    pero solo una sesión activa a la vez
    """
    __tablename__ = "profile_assignments"

    id = Column(Integer, primary_key=True)

    # Qué perfil
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)

    # Quién
    agent_id = Column(Integer, ForeignKey("agent_tokens.id"), nullable=False, index=True)

    # Qué abrir
    target_url = Column(String(1024), default="https://www.google.com")
    assignment_name = Column(String(255))  # nombre descriptivo ej: "Cuenta FB Ecuador"

    # Control
    is_active = Column(Boolean, default=True)
    requires_auth = Column(Boolean, default=False)  # si admin debe autorizar cada apertura
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    profile = relationship("Profile")
    agent = relationship("AgentToken", back_populates="assignments")
