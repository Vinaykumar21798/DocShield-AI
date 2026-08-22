import logging
import os
from typing import Iterable

from sqlalchemy import inspect

from core.database import SessionLocal, engine

TRUE_VALUES = {"1", "true", "yes", "on"}


def _is_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def _get_model_names(models_response) -> list[str]:
    raw_models = getattr(models_response, "models", None)
    if raw_models is None and isinstance(models_response, dict):
        raw_models = models_response.get("models", [])

    model_names: list[str] = []
    for model in raw_models or []:
        name = None
        if isinstance(model, dict):
            name = model.get("name") or model.get("model")
        else:
            name = getattr(model, "name", None) or getattr(model, "model", None)

        if not name:
            continue

        model_names.append(str(name))
        if ":" in str(name):
            model_names.append(str(name).split(":", 1)[0])

    return model_names


def _missing_models(
    installed_models: Iterable[str],
    required_models: Iterable[str],
) -> list[str]:
    installed = {model.lower() for model in installed_models}
    missing: list[str] = []

    for required_model in required_models:
        required = required_model.lower()
        required_base = required.split(":", 1)[0]
        if required not in installed and required_base not in installed:
            missing.append(required_model)

    return missing


def run_startup_validation() -> None:
    """
    Validate critical runtime dependencies and schema compatibility.

    PostgreSQL schema validation is strict because the API cannot safely serve
    document state without it. The Ollama startup model check is optional and
    enabled with OLLAMA_REQUIRED=true for the Gemma detector runtime.
    """
    logger = logging.getLogger(__name__)
    logger.info("Initializing startup validation")

    if not os.getenv("DATABASE_URL"):
        raise RuntimeError(
            "Startup Validation Failed: Environment variable "
            "'DATABASE_URL' is missing or empty."
        )

    try:
        with engine.connect():
            logger.info("Database connection: OK")
    except Exception as exc:
        raise RuntimeError(
            "Startup Validation Failed: Database connection could not be "
            f"established. Details: {exc}"
        ) from exc

    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = [
            "documents",
            "processing_jobs",
            "ocr_results",
            "entities",
            "confidence_scores",
            "reviews",
            "redactions",
            "reports",
            "users",
            "auth_sessions",
        ]

        missing_tables = [
            table for table in required_tables if table not in existing_tables
        ]
        if missing_tables:
            raise RuntimeError(
                "Startup Validation Failed: Missing required database "
                f"tables: {missing_tables}. Run migrations first."
            )

        from database.models import (  # noqa: WPS433
            AuthSession,
            ConfidenceScore,
            Document,
            Entity,
            OCRResult,
            ProcessingJob,
            Redaction,
            Report,
            Review,
            User,
        )

        models_to_check = [
            Document,
            ProcessingJob,
            OCRResult,
            Entity,
            ConfidenceScore,
            Review,
            Redaction,
            Report,
            User,
            AuthSession,
        ]

        missing_columns = []
        for model in models_to_check:
            table_name = model.__tablename__
            db_columns = {
                column["name"]
                for column in inspector.get_columns(table_name)
            }
            for column in model.__table__.columns:
                if column.name not in db_columns:
                    missing_columns.append(f"{table_name}.{column.name}")

        if missing_columns:
            logger.warning(
                "Database schema compatibility warning. Columns present in "
                "models but missing in the database: %s. Run `alembic "
                "upgrade head` to synchronize the schema.",
                ", ".join(missing_columns),
            )
        else:
            logger.info("Database schema compatibility: OK")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "Startup Validation Failed: Schema verification encountered an "
            f"error. Details: {exc}"
        ) from exc

    if not _is_enabled(os.getenv("OLLAMA_REQUIRED", "false")):
        logger.info("Ollama startup model check skipped")
        return

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    required_models = [
        model.strip()
        for model in os.getenv(
            "OLLAMA_REQUIRED_MODELS",
            "gemma4:e4b",
        ).split(",")
        if model.strip()
    ]

    try:
        from ollama import Client
    except ImportError as exc:
        raise RuntimeError(
            "Startup Validation Failed: OLLAMA_REQUIRED=true but the "
            "`ollama` Python package is not installed."
        ) from exc

    try:
        client = Client(host=ollama_host)
        installed_models = _get_model_names(client.list())
        missing_models = _missing_models(installed_models, required_models)
        if missing_models:
            raise RuntimeError(
                "Startup Validation Failed: Missing required models in "
                f"Ollama: {missing_models}. Available models: "
                f"{installed_models}"
            )
        logger.info("Ollama startup model check: OK")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "Startup Validation Failed: Ollama service is unreachable at "
            f"'{ollama_host}'. Details: {exc}"
        ) from exc
