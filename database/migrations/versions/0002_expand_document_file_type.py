"""expand document file type length

Revision ID: 0002_expand_document_file_type
Revises: 0001_initial_schema
Create Date: 2026-07-27 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_expand_document_file_type"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "file_type",
            existing_type=sa.String(length=50),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.alter_column(
            "file_type",
            existing_type=sa.String(length=255),
            type_=sa.String(length=50),
            existing_nullable=False,
        )
