
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.config import settings
from core.database import engine
from core.database import Base
from core.database import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / Shutdown lifecycle.
    """

    print("=" * 60)
    print(f"{settings.app_name}")
    print("=" * 60)

    # PostgreSQL

    Base.metadata.create_all(bind=engine)

    print("✓ PostgreSQL Connected")

    # Redis

    redis_client.ping()

    print("✓ Redis Connected")

    yield

    print("Application Shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/", tags=["Health"])
def root():
    """
    Root endpoint.
    """

    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health():
    """
    Health endpoint.
    """

    return {
        "status": "healthy",
        "postgres": "connected",
        "redis": "connected",
    }

print(settings.app_name)
print(settings.database_url)
print(settings.redis_url)