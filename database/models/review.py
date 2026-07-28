from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.base import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        Index("ix_reviews_entity_id", "entity_id"),
        Index("ix_reviews_status", "review_status"),
    )

    id = Column(String, primary_key=True)

    entity_id = Column(
        String,
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    reviewer = Column(String)

    review_status = Column(String)

    review_comment = Column(Text)

    reviewed_at = Column(DateTime(timezone=True))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    entity = relationship(
        "Entity",
        back_populates="reviews",
    )