# alembic/versions/xxxx_add_tablet_device_type.py
"""Add tablet device type

Revision ID: add_tablet_type
Revises: previous_revision
Create Date: 2024-12-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_tablet_type'
down_revision = 'previous_revision'  # ← Cambiar por última revisión
branch_labels = None
depends_on = None


def upgrade():
    """
    Agrega 'tablet' al enum device_type
    """
    # PostgreSQL: Agregar valor al enum existente
    op.execute("ALTER TYPE devicetype ADD VALUE IF NOT EXISTS 'tablet'")
    
    # Nota: Si usas SQLite, no necesitas esta migración
    # SQLite no tiene enums nativos


def downgrade():
    """
    No se puede hacer downgrade de enums en PostgreSQL fácilmente
    """
    pass  # Dejar como está