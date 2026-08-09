"""add analysis enqueue tracking

Revision ID: 8b31d6a950f2
Revises: 636b2049e827
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b31d6a950f2"
down_revision: Union[str, Sequence[str], None] = "636b2049e827"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyses", sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "analyses",
        sa.Column("enqueue_claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_analyses_pending_unenqueued",
        "analyses",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'PENDING' AND enqueued_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_analyses_pending_unenqueued", table_name="analyses")
    op.drop_column("analyses", "enqueue_claimed_at")
    op.drop_column("analyses", "enqueued_at")
