"""add ocr structured output

Revision ID: 0003_add_ocr_structured_output
Revises: 0002_expand_document_file_type
Create Date: 2026-07-27 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_add_ocr_structured_output"
down_revision: Union[str, None] = "0002_expand_document_file_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ocr_results",
        sa.Column("structured_output", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ocr_results", "structured_output")
