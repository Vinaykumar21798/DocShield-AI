from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.sql import func

from database.base import Base


class ConfidenceScore(Base):
    __tablename__ = "confidence_scores"

    id = Column(String, primary_key=True)

    entity_id = Column(String, nullable=False)

    confidence_score = Column(Float, nullable=False)

    confidence_level = Column(String)

    threshold = Column(Float)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )