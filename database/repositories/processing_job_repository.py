from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from database.models import ProcessingJob
from database.repositories.base_repository import BaseRepository


class ProcessingJobRepository(BaseRepository[ProcessingJob]):

    def __init__(self):
        super().__init__(ProcessingJob)

    def create_job(
        self,
        db: Session,
        job: ProcessingJob,
    ) -> ProcessingJob:
        return self.create(db, job)

    def get_job_by_id(
        self,
        db: Session,
        job_id: str,
    ) -> Optional[ProcessingJob]:
        return self.get_by_id(db, job_id)

    def get_jobs_by_document(
        self,
        db: Session,
        document_id: str,
    ) -> List[ProcessingJob]:
        return (
            db.query(ProcessingJob)
            .filter(ProcessingJob.document_id == document_id)
            .all()
        )

    def get_latest_job_by_document(
        self,
        db: Session,
        document_id: str,
    ) -> Optional[ProcessingJob]:

        return (
            db.query(ProcessingJob)
            .filter(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at.desc())
            .first()
        )

    def get_jobs_by_status(
        self,
        db: Session,
        status: str,
    ) -> List[ProcessingJob]:
        return (
            db.query(ProcessingJob)
            .filter(ProcessingJob.job_status == status)
            .all()
        )

    def update_job_status(
        self,
        db: Session,
        job: ProcessingJob,
        status: str,
    ) -> ProcessingJob:

        return self.update(
            db,
            job,
            {
                "job_status": status,
            },
        )

    def update_workflow_stage(
        self,
        db: Session,
        job: ProcessingJob,
        stage: str,
    ) -> ProcessingJob:

        return self.update(
            db,
            job,
            {
                "workflow_stage": stage,
            },
        )

    def update_last_completed_stage(
        self,
        db: Session,
        job: ProcessingJob,
        stage: str,
    ) -> ProcessingJob:

        return self.update(
            db,
            job,
            {
                "last_completed_stage": stage,
            },
        )

    def assign_worker(
        self,
        db: Session,
        job: ProcessingJob,
        worker_id: str,
    ) -> ProcessingJob:

        return self.update(
            db,
            job,
            {
                "worker_id": worker_id,
                "started_at": datetime.utcnow(),
                "completed_at": None,
                "error_message": None,
            },
        )

    def increment_retry(
        self,
        db: Session,
        job: ProcessingJob,
    ) -> ProcessingJob:

        return self.update(
            db,
            job,
            {
                "retry_count": (job.retry_count or 0) + 1,
            },
        )

    def mark_retry_queued(
        self,
        db: Session,
        job: ProcessingJob,
    ) -> ProcessingJob:

        return self.update(
            db,
            job,
            {
                "job_status": "PENDING",
                "workflow_stage": "RETRY_QUEUED",
                "retry_count": (job.retry_count or 0) + 1,
                "worker_id": None,
                "started_at": None,
                "completed_at": None,
            },
        )

    def mark_completed(
        self,
        db: Session,
        job: ProcessingJob,
    ) -> ProcessingJob:

        return self.update(
            db,
            job,
            {
                "job_status": "COMPLETED",
                "workflow_stage": "COMPLETE_WORKFLOW",
                "last_completed_stage": "COMPLETE_WORKFLOW",
                "error_message": None,
                "completed_at": datetime.utcnow(),
            },
        )

    def mark_failed(
        self,
        db: Session,
        job: ProcessingJob,
        error_message: str,
    ) -> ProcessingJob:

        return self.update(
            db,
            job,
            {
                "job_status": "FAILED",
                "error_message": error_message,
                "completed_at": datetime.utcnow(),
            },
        )


processing_job_repository = ProcessingJobRepository()
