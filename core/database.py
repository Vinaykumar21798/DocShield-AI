from pathlib import Path
from typing import Generator

import redis
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from core.config import settings


def _ensure_sqlite_database_parent(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return

    database_path = url.database
    if not database_path or database_path == ":memory:":
        return

    Path(database_path).expanduser().parent.mkdir(
        parents=True,
        exist_ok=True,
    )


_ensure_sqlite_database_parent(settings.database_url)

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