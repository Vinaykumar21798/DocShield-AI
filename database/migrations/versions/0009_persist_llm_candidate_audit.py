"""persist LLM candidate audit on reports

Revision ID: 0009_persist_llm_candidate_audit
Revises: 0008_add_users_and_auth_sessions
Create Date: 2026-08-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_persist_llm_candidate_audit"
down_revision: Union[str, None] = "0008_add_users_and_auth_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("llm_candidate_audit", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reports", "llm_candidate_audit")
