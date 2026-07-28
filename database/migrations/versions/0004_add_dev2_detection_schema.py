"""add dev2 detection schema

Revision ID: 0004_add_dev2_detection_schema
Revises: 0003_add_ocr_structured_output
Create Date: 2026-07-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_add_dev2_detection_schema"
down_revision: Union[str, None] = "0003_add_ocr_structured_output"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _existing_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _existing_columns(table_name):
        op.add_column(table_name, column)


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    return any(
        index["name"] == index_name
        for index in sa.inspect(bind).get_indexes(table_name)
    )


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _foreign_key_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    return any(
        fk.get("name") == constraint_name
        for fk in sa.inspect(bind).get_foreign_keys(table_name)
    )


def _create_foreign_key_if_missing(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    ondelete: str,
) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    if not _foreign_key_exists(source_table, constraint_name):
        op.create_foreign_key(
            constraint_name,
            source_table,
            referent_table,
            local_cols,
            remote_cols,
            ondelete=ondelete,
        )


def _create_entities() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("ocr_result_id", sa.String(length=36), nullable=True),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_value", sa.Text(), nullable=False),
        sa.Column("page_number", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("detector", sa.String(), nullable=True),
        sa.Column("start_char", sa.Integer(), nullable=True),
        sa.Column("end_char", sa.Integer(), nullable=True),
        sa.Column("privacy_category", sa.String(), nullable=True),
        sa.Column("entity_owner", sa.String(), nullable=True),
        sa.Column("canonical_type", sa.String(), nullable=True),
        sa.Column("processing_stage", sa.String(), server_default="DETECTION", nullable=True),
        sa.Column("is_review_required", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("is_redacted", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("final_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ocr_result_id"], ["ocr_results.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_confidence_scores() -> None:
    op.create_table(
        "confidence_scores",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("confidence_level", sa.String(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_reviews() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("reviewer", sa.String(), nullable=True),
        sa.Column("review_status", sa.String(), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_redactions() -> None:
    op.create_table(
        "redactions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("redaction_type", sa.String(), nullable=False),
        sa.Column("redacted_file_path", sa.String(), nullable=True),
        sa.Column("redaction_summary", sa.Text(), nullable=True),
        sa.Column("processed_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_reports() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("total_entities", sa.Integer(), server_default="0", nullable=True),
        sa.Column("total_redactions", sa.Integer(), server_default="0", nullable=True),
        sa.Column("report_path", sa.String(), nullable=True),
        sa.Column("generated_by", sa.String(), nullable=True),
        sa.Column("processing_duration_ms", sa.Integer(), nullable=True),
        sa.Column("detectors_used", sa.String(), nullable=True),
        sa.Column("qwen_invoked", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("total_pii", sa.Integer(), server_default="0", nullable=True),
        sa.Column("total_phi", sa.Integer(), server_default="0", nullable=True),
        sa.Column("review_completion", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("redaction_completion", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def upgrade() -> None:
    tables = _existing_tables()

    if "entities" not in tables:
        _create_entities()
    else:
        _add_column_if_missing("entities", sa.Column("start_char", sa.Integer(), nullable=True))
        _add_column_if_missing("entities", sa.Column("end_char", sa.Integer(), nullable=True))
        _add_column_if_missing("entities", sa.Column("privacy_category", sa.String(), nullable=True))
        _add_column_if_missing("entities", sa.Column("entity_owner", sa.String(), nullable=True))
        _add_column_if_missing("entities", sa.Column("canonical_type", sa.String(), nullable=True))
        _add_column_if_missing("entities", sa.Column("processing_stage", sa.String(), server_default="DETECTION", nullable=True))
        _add_column_if_missing("entities", sa.Column("is_review_required", sa.Boolean(), server_default=sa.text("false"), nullable=True))
        _add_column_if_missing("entities", sa.Column("is_redacted", sa.Boolean(), server_default=sa.text("false"), nullable=True))
        _add_column_if_missing("entities", sa.Column("final_confidence", sa.Float(), nullable=True))
        _create_foreign_key_if_missing("fk_entities_document_id_documents", "entities", "documents", ["document_id"], ["id"], "CASCADE")
        _create_foreign_key_if_missing("fk_entities_ocr_result_id_ocr_results", "entities", "ocr_results", ["ocr_result_id"], ["id"], "SET NULL")

    tables = _existing_tables()
    if "confidence_scores" not in tables:
        _create_confidence_scores()
    else:
        _create_foreign_key_if_missing("fk_confidence_scores_entity_id_entities", "confidence_scores", "entities", ["entity_id"], ["id"], "CASCADE")

    if "reviews" not in tables:
        _create_reviews()
    else:
        _create_foreign_key_if_missing("fk_reviews_entity_id_entities", "reviews", "entities", ["entity_id"], ["id"], "CASCADE")

    if "redactions" not in tables:
        _create_redactions()
    else:
        _create_foreign_key_if_missing("fk_redactions_document_id_documents", "redactions", "documents", ["document_id"], ["id"], "CASCADE")

    if "reports" not in tables:
        _create_reports()
    else:
        _add_column_if_missing("reports", sa.Column("processing_duration_ms", sa.Integer(), nullable=True))
        _add_column_if_missing("reports", sa.Column("detectors_used", sa.String(), nullable=True))
        _add_column_if_missing("reports", sa.Column("qwen_invoked", sa.Boolean(), server_default=sa.text("false"), nullable=True))
        _add_column_if_missing("reports", sa.Column("total_pii", sa.Integer(), server_default="0", nullable=True))
        _add_column_if_missing("reports", sa.Column("total_phi", sa.Integer(), server_default="0", nullable=True))
        _add_column_if_missing("reports", sa.Column("review_completion", sa.Boolean(), server_default=sa.text("false"), nullable=True))
        _add_column_if_missing("reports", sa.Column("redaction_completion", sa.Boolean(), server_default=sa.text("false"), nullable=True))
        _create_foreign_key_if_missing("fk_reports_document_id_documents", "reports", "documents", ["document_id"], ["id"], "CASCADE")

    _create_index_if_missing("ix_entities_document_id", "entities", ["document_id"])
    _create_index_if_missing("ix_entities_ocr_result_id", "entities", ["ocr_result_id"])
    _create_index_if_missing("ix_entities_document_type", "entities", ["document_id", "entity_type"])
    _create_index_if_missing("ix_entities_privacy_category", "entities", ["privacy_category"])
    _create_index_if_missing("ix_confidence_scores_entity_id", "confidence_scores", ["entity_id"])
    _create_index_if_missing("ix_confidence_scores_level", "confidence_scores", ["confidence_level"])
    _create_index_if_missing("ix_reviews_entity_id", "reviews", ["entity_id"])
    _create_index_if_missing("ix_reviews_status", "reviews", ["review_status"])
    _create_index_if_missing("ix_redactions_document_id", "redactions", ["document_id"])
    _create_index_if_missing("ix_redactions_type", "redactions", ["redaction_type"])
    _create_index_if_missing("ix_reports_document_id", "reports", ["document_id"])
    _create_index_if_missing("ix_reports_type", "reports", ["report_type"])


def downgrade() -> None:
    op.drop_table("reviews")
    op.drop_table("confidence_scores")
    op.drop_table("reports")
    op.drop_table("redactions")
    op.drop_table("entities")