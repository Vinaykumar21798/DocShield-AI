"""add token tracking to documents

Revision ID: 0010_add_doc_token_tracking
Revises: 0009_persist_llm_candidate_audit
Create Date: 2026-08-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_add_doc_token_tracking"
down_revision: Union[str, None] = "0009_persist_llm_candidate_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("prompt_tokens", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "documents",
        sa.Column("completion_tokens", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "documents",
        sa.Column("llm_cost_usd", sa.Float(), nullable=True, server_default="0.0"),
    )
    op.add_column(
        "documents",
        sa.Column("llm_provider", sa.String(length=50), nullable=True, server_default="azure"),
    )


def downgrade() -> None:
    op.drop_column("documents", "llm_provider")
    op.drop_column("documents", "llm_cost_usd")
    op.drop_column("documents", "completion_tokens")
    op.drop_column("documents", "prompt_tokens")
