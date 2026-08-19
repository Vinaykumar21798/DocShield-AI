from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    name = Column(String(255), nullable=False)

    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash = Column(String(255), nullable=False)

    role = Column(
        String(20),
        default="USER",
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
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

    sessions = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    documents = relationship(
        "Document",
        back_populates="owner",
    )