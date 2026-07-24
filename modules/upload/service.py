from typing import List

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.models.document import Document
from database.models.processing_job import ProcessingJob
from modules.upload.storage import StorageService
from modules.upload.validator import UploadValidator

from redis_queue.job_schema import DocumentJob
from redis_queue.producer import RedisProducer
from redis_queue.redis_client import redis_client


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

    async def upload_documents(
        self,
        files: List[UploadFile],
    ) -> List[Document]:

        if len(files) > self.MAX_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {self.MAX_FILES} files are allowed."
            )

        documents = []

        for file in files:
            document = await self.upload_single_document(file)
            documents.append(document)

        return documents

    async def upload_single_document(
        self,
        file: UploadFile,
    ) -> Document:

        # Validate
        file_content = await self.validator.validate(file)

        # Store file
        stored_filename, file_path = self.storage.save(
            filename=file.filename,
            content=file_content,
        )

        # Create document
        document = Document(
            filename=file.filename,
            stored_filename=stored_filename,
            file_type=file.content_type,
            file_size=len(file_content),
            storage_path=file_path,
            status="UPLOADED",
        )

        self.db.add(document)
        self.db.flush()

        # Create processing job
        processing_job = ProcessingJob(
            document_id=document.id,
            workflow_stage="UPLOAD",
            queue_name="document_processing",
            job_status="PENDING",
        )

        self.db.add(processing_job)

        # Commit
        self.db.commit()

        # Refresh
        self.db.refresh(document)

        # Publish Redis Job
        job = DocumentJob(
            document_id=document.id,
        )

        self.producer.publish(job)

        return document