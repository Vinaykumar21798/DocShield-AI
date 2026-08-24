"""add auditable LLM usage details to documents

Revision ID: 0011_add_llm_usage_audit
Revises: b264116667a1
Create Date: 2026-08-24 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_add_llm_usage_audit"
down_revision: Union[str, None] = "b264116667a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("cached_prompt_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("llm_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("llm_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("llm_cost_basis", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("llm_usage_complete", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "llm_usage_complete")
    op.drop_column("documents", "llm_cost_basis")
    op.drop_column("documents", "llm_duration_seconds")
    op.drop_column("documents", "llm_model")
    op.drop_column("documents", "cached_prompt_tokens")
