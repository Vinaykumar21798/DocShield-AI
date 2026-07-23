from typing import Generator

import redis

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes.

    Yields:
        SQLAlchemy Session
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


def get_redis() -> redis.Redis:
    """
    Returns Redis client.
    """

    return redis_client