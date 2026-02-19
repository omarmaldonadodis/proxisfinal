# app/repositories/__init__.py
from app.repositories.base import BaseRepository
from app.repositories.computer_repository import ComputerRepository
from app.repositories.proxy_repository import ProxyRepository
from app.repositories.profile_repository import ProfileRepository

__all__ = [
    "BaseRepository",
    "ComputerRepository",
    "ProxyRepository",
    "ProfileRepository",
]