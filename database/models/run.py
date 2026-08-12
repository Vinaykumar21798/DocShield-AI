from uuid import uuid4
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    run_id = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    status = Column(
        String(50),
        default="QUEUED",
        nullable=False,
    )

    total_files = Column(Integer, default=0, nullable=False)
    completed_files = Column(Integer, default=0, nullable=False)
    failed_files = Column(Integer, default=0, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    documents = relationship(
        "Document",
        back_populates="run",
        cascade="all, delete-orphan",
    )
