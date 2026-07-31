"""add processing job checkpoint

Revision ID: 0005_processing_job_checkpoint
Revises: 0004_add_dev2_detection_schema
Create Date: 2026-07-29 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_processing_job_checkpoint"
down_revision: Union[str, None] = "0004_add_dev2_detection_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {
        column["name"]
        for column in sa.inspect(bind).get_columns(table_name)
    }


def upgrade() -> None:
    if "last_completed_stage" not in _existing_columns("processing_jobs"):
        op.add_column(
            "processing_jobs",
            sa.Column("last_completed_stage", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    if "last_completed_stage" in _existing_columns("processing_jobs"):
        op.drop_column("processing_jobs", "last_completed_stage")
