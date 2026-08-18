from uuid import uuid4
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    filename = Column(String(255), nullable=False)

    stored_filename = Column(
        String(255),
        nullable=False,
        unique=True,
    )

    file_type = Column(String(255), nullable=False)

    document_type = Column(String(100))

    file_size = Column(Integer, nullable=False)

    content_hash = Column(
        String(64),
        nullable=True,
        index=True,
    )

    storage_path = Column(
        String(500),
        nullable=False,
    )

    status = Column(
        String(50),
        default="UPLOADED",
        nullable=False,
    )

    run_id = Column(
        String(36),
        ForeignKey("runs.id"),
        nullable=True,
        index=True,
    )

    uploaded_by = Column(String(100))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    processing_jobs = relationship(
        "ProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    ocr_results = relationship(
        "OCRResult",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    entities = relationship(
        "Entity",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    redactions = relationship(
        "Redaction",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    reports = relationship(
        "Report",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    run = relationship(
        "Run",
        back_populates="documents",
    )