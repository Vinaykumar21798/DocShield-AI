from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.base import Base


class Redaction(Base):
    __tablename__ = "redactions"
    __table_args__ = (
        Index("ix_redactions_document_id", "document_id"),
        Index("ix_redactions_type", "redaction_type"),
    )

    id = Column(String, primary_key=True)

    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    redaction_type = Column(String, nullable=False)

    redacted_file_path = Column(String)

    redaction_summary = Column(Text)

    processed_by = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document = relationship(
        "Document",
        back_populates="redactions",
    )