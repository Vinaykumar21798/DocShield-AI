"""add content hash column to documents

Revision ID: 0007_add_document_content_hash
Revises: 0006_add_run_tracking
Create Date: 2026-08-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_add_document_content_hash"
down_revision: Union[str, None] = "0006_add_run_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_documents_content_hash", "documents", ["content_hash"]
    )


def downgrade() -> None:
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_column("documents", "content_hash")
