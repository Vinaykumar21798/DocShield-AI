from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.base import Base


class ConfidenceScore(Base):
    __tablename__ = "confidence_scores"
    __table_args__ = (
        Index("ix_confidence_scores_entity_id", "entity_id"),
        Index("ix_confidence_scores_level", "confidence_level"),
    )

    id = Column(String, primary_key=True)

    entity_id = Column(
        String,
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    confidence_score = Column(Float, nullable=False)

    confidence_level = Column(String)

    threshold = Column(Float)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    entity = relationship(
        "Entity",
        back_populates="confidence_scores",
    )