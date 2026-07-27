from sqlalchemy import Column, String, Text, Float, DateTime, Integer, Boolean
from sqlalchemy.sql import func

from database.base import Base


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String, primary_key=True)

    document_id = Column(String, nullable=False)
    ocr_result_id = Column(String)

    entity_type = Column(String, nullable=False)
    entity_value = Column(Text, nullable=False)

    page_number = Column(String)
    confidence_score = Column(Float)

    detector = Column(String)

    # Lineage, Position and Lifecycle fields (Issue 4 & Issue 6)
    start_char = Column(Integer)
    end_char = Column(Integer)
    privacy_category = Column(String)
    entity_owner = Column(String)
    canonical_type = Column(String)
    processing_stage = Column(String, default="DETECTION")
    is_review_required = Column(Boolean, default=False)
    is_redacted = Column(Boolean, default=False)
    final_confidence = Column(Float)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )