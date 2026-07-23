from sqlalchemy import Column, String, Text, Float, DateTime
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

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )