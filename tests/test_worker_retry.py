from uuid import uuid4

from database.models import Document, ProcessingJob
from orchestration.workflow import RedactionVerificationError
from redis_queue.job_schema import DocumentJob
from redis_queue.worker import Worker


class FakeConsumer:
    def __init__(self, jobs):
        self.jobs = list(jobs)

    def consume(self):
        if not self.jobs:
            return None
        return self.jobs.pop(0)


class FakeProducer:
    def __init__(self):
        self.published = []

    def publish(self, job):
        self.published.append(job)
        return True


class RedactionVerificationFailureWorkflow:
    def execute(self, document_id):
        raise RedactionVerificationError(
            "Post-redaction verification failed"
        )


def create_missing_file_job(session_factory, retry_count=0):
    db = session_factory()
    document = Document(
        id=str(uuid4()),
        filename="invoice.txt",
        stored_filename=f"{uuid4()}.txt",
        file_type="text/plain",
        file_size=100,
        storage_path="missing.txt",
        status="PENDING",
    )
    processing_job = ProcessingJob(
        id=str(uuid4()),
        document_id=document.id,
        job_status="PENDING",
        workflow_stage="UPLOAD",
        queue_name="document_processing",
        retry_count=retry_count,
    )

    db.add(document)
    db.add(processing_job)
    db.commit()
    document_id = document.id
    db.close()

    return document_id


def get_processing_job(session_factory, document_id):
    db = session_factory()
    try:
        return (
            db.query(ProcessingJob)
            .filter(ProcessingJob.document_id == document_id)
            .one()
        )
    finally:
        db.close()


def test_worker_requeues_failed_job_when_retry_budget_remains(
    session_factory,
):
    document_id = create_missing_file_job(session_factory, retry_count=0)
    job = DocumentJob(document_id=document_id)
    producer = FakeProducer()
    worker = Worker(
        consumer=FakeConsumer([job]),
        producer=producer,
        session_factory=session_factory,
        max_retries=1,
    )

    assert worker.process_next_job() is True

    processing_job = get_processing_job(session_factory, document_id)
    assert processing_job.job_status == "PENDING"
    assert processing_job.workflow_stage == "RETRY_QUEUED"
    assert processing_job.last_completed_stage == "DOCUMENT_CLASSIFICATION"
    assert processing_job.retry_count == 1
    assert len(producer.published) == 1
    assert producer.published[0].document_id == job.document_id


def test_worker_leaves_failed_job_when_retry_budget_is_exhausted(
    session_factory,
):
    document_id = create_missing_file_job(session_factory, retry_count=1)
    producer = FakeProducer()
    worker = Worker(
        consumer=FakeConsumer([DocumentJob(document_id=document_id)]),
        producer=producer,
        session_factory=session_factory,
        max_retries=1,
    )

    assert worker.process_next_job() is True

    processing_job = get_processing_job(session_factory, document_id)
    assert processing_job.job_status == "FAILED"
    assert processing_job.workflow_stage == "OCR_DECISION"
    assert processing_job.last_completed_stage == "DOCUMENT_CLASSIFICATION"
    assert processing_job.retry_count == 1
    assert "Stored document file not found" in processing_job.error_message
    assert producer.published == []


def test_worker_does_not_retry_redaction_verification_failure(
    session_factory,
):
    document_id = create_missing_file_job(session_factory, retry_count=0)
    producer = FakeProducer()
    worker = Worker(
        consumer=FakeConsumer([DocumentJob(document_id=document_id)]),
        producer=producer,
        session_factory=session_factory,
        workflow_factory=lambda db: RedactionVerificationFailureWorkflow(),
        max_retries=4,
    )

    assert worker.process_next_job() is True

    processing_job = get_processing_job(session_factory, document_id)
    assert processing_job.retry_count == 0
    assert producer.published == []
