from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.config import settings
from core.database import Base, engine, redis_client

from database.models import Document
from database.models import ProcessingJob
from database.models import OCRResult


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("=" * 60)
    print(settings.app_name)
    print("=" * 60)

    Base.metadata.create_all(bind=engine)
    print("✓ PostgreSQL Connected")

    redis_client.ping()
    print("✓ Redis Connected")

    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)