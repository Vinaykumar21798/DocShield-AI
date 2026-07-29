from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

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

    job_status = Column(
        String(50),
        nullable=False,
        default="QUEUED",
    )

    workflow_stage = Column(
        String(100),
        nullable=False,
        default="DOCUMENT_UPLOAD",
    )

    last_completed_stage = Column(
        String(100),
        nullable=True,
    )

    queue_name = Column(
        String(100),
        nullable=True,
    )

    worker_id = Column(
        String(100),
        nullable=True,
    )

    retry_count = Column(
        Integer,
        default=0,
    )

    error_message = Column(
        String(1000),
        nullable=True,
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
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
        back_populates="processing_jobs",
    )