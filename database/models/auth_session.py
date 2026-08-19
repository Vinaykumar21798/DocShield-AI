from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="sessions",
    )