import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    echo=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def run_startup_validation():
    """
    Validates dependencies, database connections, schemas, and Ollama status on startup.
    Raises RuntimeError if any critical validator fails.
    """
    logger = logging.getLogger(__name__)
    logger.info("Initializing Startup Validation...")

    # 1. Environment & Configuration Check
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("Startup Validation Failed: Environment variable 'DATABASE_URL' is missing or empty.")

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    logger.info(f"Configuration Verified: DATABASE_URL present, OLLAMA_HOST={ollama_host}")

    # 2. Database Connection Check
    try:
        connection = engine.connect()
        connection.close()
        logger.info("Database Connection: OK")
    except Exception as exc:
        raise RuntimeError(f"Startup Validation Failed: Database connection could not be established. Details: {exc}")

    # 3. Database Schema Verification & Compatibility Checker
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = ["entities", "confidence_scores", "reviews", "redactions", "reports"]
        
        # Verify required tables exist
        missing_tables = [table for table in required_tables if table not in existing_tables]
        if missing_tables:
            raise RuntimeError(f"Startup Validation Failed: Missing required database tables: {missing_tables}. Run migrations first.")
        logger.info("Database Tables Verification: OK")

        # Diagnostics-only Column Compatibility Check (Issue 4)
        from database.models.entity import Entity
        from database.models.confidence import ConfidenceScore
        from database.models.review import Review
        from database.models.redaction import Redaction
        from database.models.report import Report
        
        models_to_check = [Entity, ConfidenceScore, Review, Redaction, Report]
        
        missing_columns_report = []
        for model in models_to_check:
            table_name = model.__tablename__
            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}
            
            # Compare mapper columns against DB columns
            for column in model.__table__.columns:
                if column.name not in db_columns:
                    missing_columns_report.append(f"{table_name}.{column.name}")
        
        if missing_columns_report:
            logger.warning(
                "\n⚠️  DATABASE SCHEMA COMPATIBILITY DIAGNOSTICS ⚠️\n"
                "The following columns exist in SQLAlchemy models but are missing in the PostgreSQL database:\n"
                + "\n".join(f" - {col}" for col in missing_columns_report)
                + "\n\nMigration Hint: Run `alembic upgrade head` to synchronize the database schema.\n"
            )
        else:
            logger.info("Database Schema Compatibility Check: OK (All columns matched)")

    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise exc
        raise RuntimeError(f"Startup Validation Failed: Schema verification encountered an error. Details: {exc}")

    # 4. Ollama Availability & Model Gating Verification
    try:
        from ollama import Client
        client = Client(host=ollama_host)
        
        # Test availability by listing models
        models_response = client.list()
        logger.info("Ollama Connection: OK")
        
        # Verify required models are installed
        installed_models = []
        for m in models_response.get("models", []):
            name = m.get("name", "")
            installed_models.append(name)
            # Ollama lists tag formats (e.g. "qwen2.5:8b"), so keep lowercase and base name
            if ":" in name:
                installed_models.append(name.split(":")[0])

        required_models = ["qwen2.5:8b", "qwen3:4b"]
        missing_models = []
        for req in required_models:
            # Check if any installed model matches or contains the name prefix
            req_base = req.split(":")[0]
            matched = False
            for inst in installed_models:
                if req in inst or inst.startswith(req) or inst == req_base:
                    matched = True
                    break
            if not matched:
                missing_models.append(req)

        if missing_models:
            raise RuntimeError(
                f"Startup Validation Failed: Missing required models in Ollama: {missing_models}. "
                f"Please run `ollama pull <model_name>` to install them. Available models: {installed_models}"
            )
        logger.info("Ollama Models Verification: OK")

    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise exc
        raise RuntimeError(
            f"Startup Validation Failed: Ollama service is unreachable at '{ollama_host}'. "
            f"Please verify Ollama is running and healthy. Details: {exc}"
        )

    logger.info("Startup Validation completed successfully. All dependencies ready!")