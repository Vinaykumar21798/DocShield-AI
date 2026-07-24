from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    extraction_method = Column(
        String(100),
        nullable=False,
    )

    is_searchable = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    extracted_text = Column(
        Text,
        nullable=True,
    )

    extracted_text_path = Column(
        String(500),
        nullable=True,
    )

    page_count = Column(
        Integer,
        default=0,
    )

    confidence_score = Column(
        Float,
        default=0.0,
    )

    processing_time = Column(
        Float,
        default=0.0,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    document = relationship(
        "Document",
        back_populates="ocr_results",
    )