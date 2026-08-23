"""Add ai_decision, ai_reasoning, is_accepted_by_ai to entities

Revision ID: b264116667a1
Revises: 0010_add_doc_token_tracking
Create Date: 2026-08-22 20:16:19.693744
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b264116667a1'
down_revision: Union[str, None] = '0010_add_doc_token_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "entities",
        sa.Column("ai_decision", sa.String(), nullable=True),
    )
    op.add_column(
        "entities",
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
    )
    op.add_column(
        "entities",
        sa.Column(
            "is_accepted_by_ai",
            sa.Boolean(),
            nullable=True,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("entities", "is_accepted_by_ai")
    op.drop_column("entities", "ai_reasoning")
    op.drop_column("entities", "ai_decision")
