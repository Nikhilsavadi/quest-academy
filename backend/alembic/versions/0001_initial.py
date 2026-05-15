"""initial schema — create all tables from metadata

Revision ID: 0001
Revises:
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Single-shot schema creation from SQLAlchemy metadata.
    # All model classes are imported by env.py at config time.
    from database import Base
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from database import Base
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
