from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func

from database.base import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True)

    document_id = Column(String, nullable=False)

    report_type = Column(String, nullable=False)

    total_entities = Column(Integer, default=0)

    total_redactions = Column(Integer, default=0)

    report_path = Column(String)

    generated_by = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )