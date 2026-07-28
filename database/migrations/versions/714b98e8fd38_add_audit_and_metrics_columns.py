"""add audit and metrics columns

Revision ID: 714b98e8fd38
Revises: 247b84e8fd37
Create Date: 2026-07-27 13:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '714b98e8fd38'
down_revision: Union[str, Sequence[str], None] = '247b84e8fd37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to entities table
    op.add_column('entities', sa.Column('start_char', sa.Integer(), nullable=True))
    op.add_column('entities', sa.Column('end_char', sa.Integer(), nullable=True))
    op.add_column('entities', sa.Column('privacy_category', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('entity_owner', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('canonical_type', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('processing_stage', sa.String(), server_default='DETECTION', nullable=True))
    op.add_column('entities', sa.Column('is_review_required', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('entities', sa.Column('is_redacted', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('entities', sa.Column('final_confidence', sa.Float(), nullable=True))

    # Add columns to reports table
    op.add_column('reports', sa.Column('processing_duration_ms', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('detectors_used', sa.String(), nullable=True))
    op.add_column('reports', sa.Column('qwen_invoked', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('reports', sa.Column('total_pii', sa.Integer(), server_default='0', nullable=True))
    op.add_column('reports', sa.Column('total_phi', sa.Integer(), server_default='0', nullable=True))
    op.add_column('reports', sa.Column('review_completion', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('reports', sa.Column('redaction_completion', sa.Boolean(), server_default=sa.text('false'), nullable=True))


def downgrade() -> None:
    # Drop columns from reports table
    op.drop_column('reports', 'redaction_completion')
    op.drop_column('reports', 'review_completion')
    op.drop_column('reports', 'total_phi')
    op.drop_column('reports', 'total_pii')
    op.drop_column('reports', 'qwen_invoked')
    op.drop_column('reports', 'detectors_used')
    op.drop_column('reports', 'processing_duration_ms')

    # Drop columns from entities table
    op.drop_column('entities', 'final_confidence')
    op.drop_column('entities', 'is_redacted')
    op.drop_column('entities', 'is_review_required')
    op.drop_column('entities', 'processing_stage')
    op.drop_column('entities', 'canonical_type')
    op.drop_column('entities', 'entity_owner')
    op.drop_column('entities', 'privacy_category')
    op.drop_column('entities', 'end_char')
    op.drop_column('entities', 'start_char')
