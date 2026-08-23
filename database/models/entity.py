from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.base import Base


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        Index("ix_entities_document_id", "document_id"),
        Index("ix_entities_ocr_result_id", "ocr_result_id"),
        Index("ix_entities_document_type", "document_id", "entity_type"),
        Index("ix_entities_privacy_category", "privacy_category"),
    )

    id = Column(String, primary_key=True)

    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    ocr_result_id = Column(
        String(36),
        ForeignKey("ocr_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    entity_type = Column(String, nullable=False)
    entity_value = Column(Text, nullable=False)

    page_number = Column(String)
    confidence_score = Column(Float)

    detector = Column(String)

    start_char = Column(Integer)
    end_char = Column(Integer)
    privacy_category = Column(String)
    entity_owner = Column(String)
    canonical_type = Column(String)
    processing_stage = Column(String, default="DETECTION")
    is_review_required = Column(Boolean, default=False)
    is_redacted = Column(Boolean, default=False)
    final_confidence = Column(Float)

    ai_decision = Column(String, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    is_accepted_by_ai = Column(Boolean, default=True, server_default="true")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document = relationship(
        "Document",
        back_populates="entities",
    )
    ocr_result = relationship(
        "OCRResult",
        back_populates="entities",
    )
    confidence_scores = relationship(
        "ConfidenceScore",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    reviews = relationship(
        "Review",
        back_populates="entity",
        cascade="all, delete-orphan",
    )