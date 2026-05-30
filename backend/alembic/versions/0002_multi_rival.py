"""multi-rival: name/avatar/personality on max_rival + seed Aisha & Tom

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Add columns (nullable initially so we can backfill)
    op.add_column("max_rival", sa.Column("name", sa.String(40), nullable=True))
    op.add_column("max_rival", sa.Column("avatar", sa.String(8), nullable=True))
    op.add_column("max_rival", sa.Column("personality", sa.String(20), nullable=True))

    # Backfill the existing single row as Max
    bind.execute(sa.text(
        "UPDATE max_rival SET name = 'Max', avatar = '🤖', personality = 'balanced' "
        "WHERE name IS NULL"
    ))

    # Tighten constraints
    op.alter_column("max_rival", "name", nullable=False)
    op.alter_column("max_rival", "avatar", nullable=False)
    op.alter_column("max_rival", "personality", nullable=False)
    op.create_unique_constraint("uq_max_rival_name", "max_rival", ["name"])

    # Seed two extra rivals if not already present
    bind.execute(sa.text("""
        INSERT INTO max_rival (current_xp, daily_rate, cycle_day, surge_active,
                               surge_days_remaining, base_difficulty, days_child_ahead,
                               xp_history, name, avatar, personality)
        SELECT 0, 50, 1, false, 0, 'standard', 0, '[]'::json, 'Aisha', '📐', 'mathlete'
        WHERE NOT EXISTS (SELECT 1 FROM max_rival WHERE name = 'Aisha')
    """))
    bind.execute(sa.text("""
        INSERT INTO max_rival (current_xp, daily_rate, cycle_day, surge_active,
                               surge_days_remaining, base_difficulty, days_child_ahead,
                               xp_history, name, avatar, personality)
        SELECT 0, 30, 1, false, 0, 'standard', 0, '[]'::json, 'Tom', '🧠', 'strategist'
        WHERE NOT EXISTS (SELECT 1 FROM max_rival WHERE name = 'Tom')
    """))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM max_rival WHERE name IN ('Aisha', 'Tom')"))
    op.drop_constraint("uq_max_rival_name", "max_rival", type_="unique")
    op.drop_column("max_rival", "personality")
    op.drop_column("max_rival", "avatar")
    op.drop_column("max_rival", "name")
