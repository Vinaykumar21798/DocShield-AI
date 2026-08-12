"""add run and run sequence tables
 
Revision ID: 0006_add_run_tracking
Revises: 0005_processing_job_checkpoint
Create Date: 2026-08-12 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_add_run_tracking"
down_revision: Union[str, None] = "0005_processing_job_checkpoint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create run_sequence table
    op.create_table(
        "run_sequence",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("last_value", sa.Integer(), nullable=False),
    )
    # Initialize sequence
    op.execute("INSERT INTO run_sequence (id, last_value) VALUES (1, 0)")

    # Create runs table
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=36), nullable=False, primary_key=True),
        sa.Column("run_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("total_files", sa.Integer(), nullable=False),
        sa.Column("completed_files", sa.Integer(), nullable=False),
        sa.Column("failed_files", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_runs_run_id", "runs", ["run_id"], unique=True)

    # Add run_id to documents with Foreign Key
    op.add_column(
        "documents", 
        sa.Column("run_id", sa.String(length=36), nullable=True)
    )
    op.create_foreign_key(
        "fk_documents_run_id", 
        "documents", "runs", 
        ["run_id"], ["id"]
    )
    op.create_index("ix_documents_run_id", "documents", ["run_id"])


def downgrade() -> None:
    op.drop_constraint("fk_documents_run_id", "documents", type_="foreignkey")
    op.drop_index("ix_documents_run_id", table_name="documents")
    op.drop_column("documents", "run_id")
    op.drop_index("ix_runs_run_id", table_name="runs")
    op.drop_table("runs")
    op.drop_table("run_sequence")
