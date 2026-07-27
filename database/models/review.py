from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func

from database.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True)

    entity_id = Column(String, nullable=False)

    reviewer = Column(String)

    review_status = Column(String)

    review_comment = Column(Text)

    reviewed_at = Column(DateTime(timezone=True))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )