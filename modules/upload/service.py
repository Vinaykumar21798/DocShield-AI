from typing import List, Tuple
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.models.document import Document
from database.models.processing_job import ProcessingJob
from database.models.run import Run
from database.repositories.document_repository import document_repository
from database.repositories.run_repository import RunRepository
from modules.upload.hashing import stream_file_sha256
from modules.upload.storage import StorageService
from modules.upload.validator import UploadValidator

from redis_queue.job_schema import DocumentJob
from redis_queue.producer import RedisProducer
from redis_queue.redis_client import redis_client


DOCUMENT_STATUS_PENDING = "PENDING"
PROCESSING_JOB_STATUS_PENDING = "PENDING"
WORKFLOW_STAGE_UPLOAD = "UPLOAD"
DOCUMENT_PROCESSING_QUEUE = "document_processing"


class UploadService:
    """
    Handles document upload workflow.
    """

    MAX_FILES = 100

    def __init__(self, db: Session):
        self.db = db
        self.validator = UploadValidator()
        self.storage = StorageService()
        self.producer = RedisProducer(redis_client)
        self.run_repo = RunRepository(db)
        self.document_repo = document_repository

    async def upload_documents(
        self,
        files: List[UploadFile],
    ) -> Tuple[Run, List[Document]]:

        if len(files) > self.MAX_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {self.MAX_FILES} files are allowed."
            )

        # Create ONE Run for this request
        run = self.run_repo.create_run(total_files=len(files))

        documents = []
        duplicate_count = 0
        for file in files:
            document = await self._process_upload(file, run)
            documents.append(document)
            if getattr(document, "_upload_is_duplicate", False):
                duplicate_count += 1

        # Duplicates are skipped (no processing job is enqueued), so exclude
        # them from the run's file count to keep run status accounting correct.
        if duplicate_count:
            run.total_files = max(0, run.total_files - duplicate_count)

        self.db.commit()
        self.db.refresh(run)
        
        return run, documents

    async def upload_single_document(
        self,
        file: UploadFile,
    ) -> Tuple[Run, Document]:
        # Treat single upload as a bulk upload of 1 file
        return await self.upload_documents([file])

    async def _process_upload(
        self,
        file: UploadFile,
        run: Run,
    ) -> Document:

        # Validate
        file_content = await self.validator.validate(file)

        # Compute a streaming SHA-256 of the original file content (before any
        # OCR/extraction) to detect duplicate uploads.
        file.file.seek(0)
        content_hash = stream_file_sha256(file.file)

        # Duplicate detection: if an identical document already exists, return
        # the existing document/run reference and skip all downstream work
        # (no new artifact, no processing job, no OCR/detection).
        existing = self.document_repo.get_document_by_content_hash(
            self.db,
            content_hash,
        )
        if existing is not None:
            setattr(existing, "_upload_is_duplicate", True)
            return existing

        # Generate Document ID first to use in storage path
        import uuid
        doc_id = str(uuid.uuid4())

        # Store file in run-specific directory
        stored_filename, file_path = self.storage.save(
            filename=file.filename,
            content=file_content,
            run_id=run.id,
            document_id=doc_id,
        )

        # Create document linked to Run
        document = Document(
            id=doc_id,
            filename=file.filename,
            stored_filename=stored_filename,
            file_type=file.content_type,
            file_size=len(file_content),
            content_hash=content_hash,
            storage_path=file_path,
            status=DOCUMENT_STATUS_PENDING,
            run_id=run.id,
        )

        self.db.add(document)
        self.db.flush()

        # Create processing job
        processing_job = ProcessingJob(
            document_id=document.id,
            workflow_stage=WORKFLOW_STAGE_UPLOAD,
            queue_name=DOCUMENT_PROCESSING_QUEUE,
            job_status=PROCESSING_JOB_STATUS_PENDING,
        )

        self.db.add(processing_job)

        # Publish Redis Job with Run Context
        job = DocumentJob(
            document_id=document.id,
            run_id=run.run_id,
        )

        self.producer.publish(job)

        return document
