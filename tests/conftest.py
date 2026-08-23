import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["APP_NAME"] = "PII/PHI Document Intelligence PoC Test"
os.environ["APP_VERSION"] = "test"
os.environ["DEBUG"] = "False"
os.environ["DATABASE_URL"] = "sqlite:///./storage/test_settings.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["UPLOAD_DIR"] = "storage/uploads"
os.environ["STORAGE_DIR"] = "storage"
os.environ["MAX_FILE_SIZE_MB"] = "20"
os.environ["PROCESSING_JOB_MAX_RETRIES"] = "1"
os.environ["STARTUP_VALIDATION_ENABLED"] = "False"
os.environ["AUTH_TOKEN_TTL_HOURS"] = "1"
os.environ["AUTH_PBKDF2_ITERATIONS"] = "1000"
os.environ["BYPASS_LLM"] = "true"
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["GLINER_ENABLED"] = "False"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["SENTENCE_TRANSFORMERS_OFFLINE"] = "1"

from core.database import Base  # noqa: E402
from database import models  # noqa: E402,F401


@pytest.fixture()
def session_factory(tmp_path):
    database_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(session_factory):
    db = session_factory()

    try:
        yield db
    finally:
        db.close()
