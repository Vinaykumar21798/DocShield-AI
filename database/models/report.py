from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.base import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_document_id", "document_id"),
        Index("ix_reports_type", "report_type"),
    )

    id = Column(String, primary_key=True)

    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    report_type = Column(String, nullable=False)

    total_entities = Column(Integer, default=0)

    total_redactions = Column(Integer, default=0)

    report_path = Column(String)

    generated_by = Column(String)

    processing_duration_ms = Column(Integer)
    detectors_used = Column(String)
    qwen_invoked = Column(Boolean, default=False)
    total_pii = Column(Integer, default=0)
    total_phi = Column(Integer, default=0)
    review_completion = Column(Boolean, default=False)
    redaction_completion = Column(Boolean, default=False)
    llm_candidate_audit = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document = relationship(
        "Document",
        back_populates="reports",
    )
