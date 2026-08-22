import logging
from pathlib import Path
from core.logger import get_logger, setup_logging, pipeline_stage_context, stage_timer


def test_logger_creation_and_pipeline_context(tmp_path):
    """Test setup_logging, get_logger, and pipeline_stage_context."""
    log_dir = tmp_path / "logs"
    setup_logging(
        log_level="INFO",
        log_dir=log_dir,
        app_log_file="test_pipeline.log",
        json_log_file="test_structured.jsonl",
        enable_console_colors=False,
    )

    logger = get_logger("modules.detection.test_logger")

    with pipeline_stage_context(stage="DETECTION", document_id="doc-12345678", job_id="job-87654321"):
        logger.info("Candidate evaluated: value='Dr. Robert Chen' decision='PENDING_FOR_LLM'")

    with stage_timer("TEST_STAGE", logger=logger):
        logger.info("Executing test operation inside stage timer")

    # Verify log files were generated
    app_log = log_dir / "test_pipeline.log"
    json_log = log_dir / "test_structured.jsonl"


    with pipeline_stage_context(stage="DETECTION", document_id="doc-12345678", job_id="job-87654321"):
        logger.info("Candidate evaluated: value='Dr. Robert Chen' decision='PENDING_FOR_LLM'")

    with stage_timer("TEST_STAGE", logger=logger):
        logger.info("Executing test operation inside stage timer")

    # Verify log files were generated
    app_log = log_dir / "test_pipeline.log"
    json_log = log_dir / "test_structured.jsonl"

    assert app_log.exists()
    assert json_log.exists()

    app_content = app_log.read_text(encoding="utf-8")
    assert "Dr. Robert Chen" not in app_content
    assert "value=[REDACTED]" in app_content
    assert "doc=doc-1234" in app_content
    assert "DETECTION" in app_content

    json_content = json_log.read_text(encoding="utf-8")
    assert "Dr. Robert Chen" not in json_content
    assert "pipeline_context" in json_content
