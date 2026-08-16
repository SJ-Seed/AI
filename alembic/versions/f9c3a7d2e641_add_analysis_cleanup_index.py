"""add analysis cleanup index

Revision ID: f9c3a7d2e641
Revises: 8b31d6a950f2
Create Date: 2026-08-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9c3a7d2e641"
down_revision: Union[str, Sequence[str], None] = "8b31d6a950f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_analyses_terminal_completed_at",
            "analyses",
            ["completed_at"],
            unique=False,
            postgresql_where=sa.text("status IN ('COMPLETED', 'FAILED')"),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_analyses_terminal_completed_at",
            table_name="analyses",
            postgresql_concurrently=True,
        )
