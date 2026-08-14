import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.base import Base
from database.models import Document, Run, ProcessingJob, Entity
from benchmarks.docs_synth import native_2page_pdf
from orchestration.workflow import DocumentProcessingWorkflow
from modules.upload.storage import StorageService

def create_document_with_job(db_session, storage_path, filename="invoice.pdf"):
    run = Run(id="run-1", run_id="RUN-001", status="QUEUED", total_files=1)
    document = Document(
        id="doc-1",
        filename=filename,
        stored_filename="stored_doc.pdf",
        file_type="application/pdf",
        file_size=100,
        storage_path=str(storage_path),
        status="PENDING",
        run_id=run.id
    )
    processing_job = ProcessingJob(
        id="job-1",
        document_id=document.id,
        job_status="PENDING",
        workflow_stage="UPLOAD",
        queue_name="document_processing",
        retry_count=0
    )
    db_session.add(run)
    db_session.add(document)
    db_session.add(processing_job)
    db_session.commit()
    return document, processing_job

def test_reproduce_native_page_attribution(tmp_path, db_session, monkeypatch):
    """
    Verify that multi-page native PDFs have correct page attribution
    after the fix to the page separator.
    """
    monkeypatch.chdir(tmp_path)
    
    # 1. Build 2-page native PDF with entities on different pages
    pdf_path = tmp_path / "page_attr_test.pdf"
    native_2page_pdf(pdf_path)
    
    doc, job = create_document_with_job(db_session, pdf_path)

    # 2. Run existing workflow
    workflow = DocumentProcessingWorkflow(db_session)
    workflow.execute(doc.id)

    # 3. Verify entities
    entities = db_session.query(Entity).filter(Entity.document_id == doc.id).all()
    
    # Fixed: Email on page 1, SSN on page 2
    email_entity = next(e for e in entities if "john.smith@example.com" in e.entity_value)
    ssn_entity = next(e for e in entities if "123-45-6789" in e.entity_value)

    assert email_entity.page_number == "1"
    assert ssn_entity.page_number == "2", f"Bug still present: SSN entity attributed to page {ssn_entity.page_number}, expected 2"
