import logging
import sys
from pathlib import Path
from typing import Callable, Optional

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from redis.exceptions import TimeoutError
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from database.repositories.processing_job_repository import (
    ProcessingJobRepository,
    processing_job_repository,
)
from orchestration.workflow import DocumentProcessingWorkflow
from redis_queue.consumer import RedisConsumer
from redis_queue.job_schema import DocumentJob
from redis_queue.producer import RedisProducer
from redis_queue.redis_client import redis_client

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
logger = logging.getLogger(__name__)


from core.logger import pipeline_stage_context, setup_logging, stage_timer


class Worker:
    """
    Background worker that continuously processes Redis jobs.
    """

    def __init__(
        self,
        consumer: Optional[RedisConsumer] = None,
        producer: Optional[RedisProducer] = None,
        session_factory: Callable[[], Session] = SessionLocal,
        workflow_factory: Callable[[Session], DocumentProcessingWorkflow] = (
            DocumentProcessingWorkflow
        ),
        max_retries: Optional[int] = None,
        job_repository: ProcessingJobRepository = processing_job_repository,
    ):
        setup_logging(log_level="DEBUG" if settings.debug else "INFO")
        self.consumer = consumer or RedisConsumer(redis_client)
        self.producer = producer or RedisProducer(redis_client)
        self.session_factory = session_factory
        self.workflow_factory = workflow_factory
        self.max_retries = (
            settings.processing_job_max_retries
            if max_retries is None
            else max_retries
        )
        self.job_repository = job_repository

    def start(self):
        logger.info("==================================================")
        logger.info("DocShield-AI Redis Worker Started")
        logger.info("Waiting for incoming document processing jobs...")
        logger.info("==================================================")

        while True:
            try:
                self.process_next_job()

            except TimeoutError:
                continue

            except KeyboardInterrupt:
                logger.info("Worker stopped by user.")
                break

            except Exception:
                logger.exception("Worker loop encountered an unexpected error.")

    def process_next_job(self) -> bool:
        """
        Process a single queue item if one is available.
        """

        job = self.consumer.consume()

        if job is None:
            return False

        self.process_job(job)
        return True

    def process_job(self, job: DocumentJob) -> None:
        db = self.session_factory()
        job_id_str = str(getattr(job, "job_id", "") or getattr(job, "id", ""))
        doc_id_str = str(job.document_id)

        with pipeline_stage_context(stage="REDIS_WORKER", document_id=doc_id_str, job_id=job_id_str):
            with stage_timer("JOB_EXECUTION"):
                try:
                    if job.run_id:
                        logger.info("Processing document_id=%s within run_id=%s", job.document_id, job.run_id)

                    workflow = self.workflow_factory(db)
                    workflow.execute(str(job.document_id))

                except Exception:
                    logger.exception(
                        "Worker failed to process document_id=%s",
                        job.document_id,
                    )
                    self._schedule_retry_if_available(db, job)

                finally:
                    db.close()

    def _schedule_retry_if_available(
        self,
        db: Session,
        job: DocumentJob,
    ) -> bool:
        processing_job = self.job_repository.get_latest_job_by_document(
            db,
            str(job.document_id),
        )

        if processing_job is None:
            logger.warning(
                "Retry skipped because no processing job exists for "
                "document_id=%s",
                job.document_id,
            )
            return False

        retry_count = processing_job.retry_count or 0

        if retry_count >= self.max_retries:
            logger.warning(
                "Retry limit exhausted for document_id=%s retry_count=%s "
                "max_retries=%s",
                job.document_id,
                retry_count,
                self.max_retries,
            )
            return False

        processing_job = self.job_repository.mark_retry_queued(
            db,
            processing_job,
        )

        try:
            self.producer.publish(DocumentJob(
                document_id=job.document_id,
                run_id=job.run_id,
            ))
        except Exception as exc:
            logger.exception(
                "Failed to requeue document_id=%s after retry scheduling",
                job.document_id,
            )
            self.job_repository.mark_failed(
                db,
                processing_job,
                f"Retry enqueue failed: {exc}",
            )
            return False

        logger.warning(
            "Requeued document_id=%s retry_count=%s max_retries=%s",
            job.document_id,
            processing_job.retry_count,
            self.max_retries,
        )
        return True


if __name__ == "__main__":
    setup_logging(log_level="DEBUG" if settings.debug else "INFO")
    worker = Worker()
    worker.start()