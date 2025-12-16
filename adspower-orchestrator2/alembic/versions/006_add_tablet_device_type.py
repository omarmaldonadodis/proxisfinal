
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006
down_revision = '005'  # ← Cambiar por última revisión
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