from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func

from database.base import Base


class Redaction(Base):
    __tablename__ = "redactions"

    id = Column(String, primary_key=True)

    document_id = Column(String, nullable=False)

    redaction_type = Column(String, nullable=False)

    redacted_file_path = Column(String)

    redaction_summary = Column(Text)

    processed_by = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )