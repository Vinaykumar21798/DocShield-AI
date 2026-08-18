from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Generator

# Context variable for pipeline execution context (e.g. document_id, job_id, stage)
pipeline_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "pipeline_context", default={}
)


class PipelineLogFormatter(logging.Formatter):
    """
    Formatter that injects pipeline context (document_id, job_id, stage)
    into console and standard log lines.
    """

    COLOR_CODES = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[1;31m", # Bold Red
    }
    RESET_CODE = "\033[0m"

    def __init__(self, fmt: str | None = None, use_colors: bool = False):
        super().__init__(fmt or "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        self.use_colors = use_colors and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        ctx = pipeline_context.get()
        if ctx:
            prefix_parts = []
            if "job_id" in ctx:
                prefix_parts.append(f"job={ctx['job_id'][:8]}")
            if "document_id" in ctx:
                prefix_parts.append(f"doc={ctx['document_id'][:8]}")
            if "stage" in ctx:
                prefix_parts.append(f"stage={ctx['stage']}")
            if prefix_parts:
                record.msg = f"[{' '.join(prefix_parts)}] {record.msg}"

        formatted = super().format(record)
        if self.use_colors and record.levelname in self.COLOR_CODES:
            color = self.COLOR_CODES[record.levelname]
            formatted = f"{color}{formatted}{self.RESET_CODE}"
        return formatted


class JSONLogFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production log aggregation (ELK, CloudWatch, Datadog).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.threadName,
        }
        ctx = pipeline_context.get()
        if ctx:
            log_entry["pipeline_context"] = ctx

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(
    log_level: str | int = logging.INFO,
    log_dir: str | Path = "storage/logs",
    app_log_file: str = "docshield_pipeline.log",
    json_log_file: str = "docshield_structured.jsonl",
    max_bytes: int = 20 * 1024 * 1024,  # 20 MB
    backup_count: int = 5,
    enable_console_colors: bool = True,
) -> None:
    """
    Initializes global logging for the entire DocShield-AI pipeline.
    Sets up:
    1. Colorized / contextual Console logging.
    2. Rotating standard log file (docshield_pipeline.log).
    3. Rotating structured JSON log file (docshield_structured.jsonl).
    """
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate lines
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = PipelineLogFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        use_colors=enable_console_colors,
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. File Handlers (Rotating)
    try:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Standard file handler
        app_log_path = log_path / app_log_file
        file_handler = RotatingFileHandler(
            app_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_formatter = PipelineLogFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            use_colors=False,
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # JSONL structured file handler
        json_log_path = log_path / json_log_file
        json_handler = RotatingFileHandler(
            json_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        json_handler.setLevel(log_level)
        json_handler.setFormatter(JSONLogFormatter())
        root_logger.addHandler(json_handler)

    except Exception as exc:
        root_logger.warning("Could not initialize file log handlers at %s: %s", log_dir, exc)

    # Suppress verbose third-party loggers
    for noisy in ("urllib3", "httpx", "httpcore", "sentence_transformers", "transformers", "torch", "passlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Standard logger factory for any module across the DocShield-AI codebase.
    Usage:
        from core.logger import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)


@contextmanager
def pipeline_stage_context(
    stage: str | None = None,
    document_id: str | None = None,
    job_id: str | None = None,
    **extra: Any,
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager to bind document, job, and pipeline stage metadata to all logs executed within.
    Usage:
        with pipeline_stage_context(stage="DETECTION", document_id=doc_id, job_id=job_id):
            detection_service.detect(text)
    """
    current = pipeline_context.get().copy()
    if stage:
        current["stage"] = stage
    if document_id:
        current["document_id"] = str(document_id)
    if job_id:
        current["job_id"] = str(job_id)
    current.update(extra)

    token = pipeline_context.set(current)
    try:
        yield current
    finally:
        pipeline_context.reset(token)


@contextmanager
def stage_timer(stage_name: str, logger: logging.Logger | None = None) -> Generator[None, None, None]:
    """
    Context manager to time and log execution latency of any pipeline stage.
    """
    log = logger or logging.getLogger("DocShieldPipeline")
    start = time.perf_counter()
    log.info(">> Starting stage: %s", stage_name)
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000.0
        log.info("<< Completed stage: %s (duration=%.2f ms)", stage_name, elapsed)
