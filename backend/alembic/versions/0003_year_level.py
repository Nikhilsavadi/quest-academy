"""add year_level to users; backfill Anvi → Year 4

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("year_level", sa.Integer(), nullable=False, server_default="3"),
    )
    # One-off backfill: Anvi is a year ahead of Samihan, so she needs the
    # higher difficulty floor on first deploy. Future kids pick up year_level
    # from the ALLOWED_CHILDREN env var (Name:year syntax) on /enter.
    op.execute("UPDATE users SET year_level = 4 WHERE LOWER(name) = 'anvi'")


def downgrade() -> None:
    op.drop_column("users", "year_level")
