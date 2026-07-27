# PII/PHI Document Intelligence PoC - Dev1 Documentation

## 1. Purpose

This FastAPI project is the Dev1 backend for an enterprise Document Intelligence PoC. It handles document upload, validation, local storage, PostgreSQL metadata, Redis queueing, background processing, document classification, OCR/text extraction, OCR confidence evaluation, and extracted-text handoff to Dev2 for PII/PHI detection.

## 2. Current Dev1 Status

Completed:

- FastAPI project setup.
- PostgreSQL integration.
- Redis integration.
- SQLAlchemy models and repositories.
- Single and bulk upload APIs.
- File validation.
- Local document storage.
- Redis producer, consumer, and worker.
- Document Processing Orchestrator.
- Document and ProcessingJob lifecycle updates.
- Rule-based document classification.
- OCR decision engine.
- Native PDF text extraction.
- PaddleOCR image/scanned PDF extraction.
- OCR result storage.
- OCR confidence evaluation.
- Native text extraction for `.txt` and `.docx` documents.
- Document status API.
- Extracted text API for Dev2.
- Worker retry policy for failed jobs.
- Initial Alembic schema migration.
- Automated success/failure tests for workflow, retry behavior, and upload-to-text API flow.
- Fresh local validation after latest code changes.

Pending / next work:

- Run a PostgreSQL-backed deployment smoke test in the target environment.
- Integrate Dev2 PII/PHI detection.



## 3. Technology Stack


| Layer                     | Technology                    |
| ------------------------- | ----------------------------- |
| API                       | FastAPI                       |
| Database                  | PostgreSQL                    |
| ORM                       | SQLAlchemy                    |
| Queue                     | Redis                         |
| Validation                | Pydantic / FastAPI UploadFile |
| Searchable PDF Extraction | PyMuPDF                       |
| Scanned PDF / Image OCR   | PaddleOCR                     |
| Storage                   | Local filesystem              |
| API Docs                  | Swagger / OpenAPI             |




## 4. Clean Project Structure

```text
PII-PHI-Document-Intelligence-PoC/
|-- api/
|   |-- dependencies.py
|   |-- routes/
|   |   |-- __init__.py
|   |   |-- health.py
|   |   |-- upload.py
|   |   |-- documents.py
|   |-- schemas/
|       |-- __init__.py
|       |-- document.py
|       |-- document_status.py
|       |-- extracted_text.py
|       |-- ocr_result.py
|       |-- processing_job.py
|
|-- core/
|   |-- __init__.py
|   |-- config.py
|   |-- constants.py
|   |-- database.py
|   |-- logger.py
|
|-- database/
|   |-- __init__.py
|   |-- migrations/
|   |   |-- __init__.py
|   |   |-- env.py
|   |   |-- script.py.mako
|   |   |-- versions/
|   |       |-- 0001_initial_schema.py
|   |-- models/
|   |   |-- __init__.py
|   |   |-- document.py
|   |   |-- ocr_result.py
|   |   |-- processing_job.py
|   |-- repositories/
|       |-- __init__.py
|       |-- base_repository.py
|       |-- document_repository.py
|       |-- ocr_result_repository.py
|       |-- processing_job_repository.py
|
|-- modules/
|   |-- __init__.py
|   |-- classification/
|   |   |-- __init__.py
|   |   |-- service.py
|   |-- extraction/
|   |   |-- __init__.py
|   |   |-- evaluation.py
|   |   |-- native.py
|   |   |-- ocr.py
|   |   |-- paddle.py
|   |   |-- service.py
|   |-- upload/
|       |-- __init__.py
|       |-- service.py
|       |-- storage.py
|       |-- validator.py
|
|-- orchestration/
|   |-- __init__.py
|   |-- execution_plan.py
|   |-- planner.py
|   |-- state.py
|   |-- workflow.py
|
|-- redis_queue/
|   |-- __init__.py
|   |-- consumer.py
|   |-- job_schema.py
|   |-- producer.py
|   |-- redis_client.py
|   |-- worker.py
|
|-- shared/
|   |-- __init__.py
|   |-- contracts.py
|   |-- enums.py
|   |-- helpers.py
|   |-- utils.py
|
|-- storage/
|   |-- __init__.py
|   |-- uploads/
|       |-- __init__.py
|
|-- tests/
|   |-- __init__.py
|
|-- .env.example
|-- alembic.ini
|-- .gitignore
|-- app.py
|-- docker-compose.yml
|-- doc.md
|-- Dockerfile
|-- README.md
|-- requirements.txt
```

Note: the correct filename is `evaluation.py`, not `evalution.py`.

## 5. Runtime Workflow

```text
Client
  |
  v
Upload Document
  |
  v
File Validation
  |
  v
Store Original File
  |
  v
Create Document Record: PENDING
  |
  v
Create Processing Job: PENDING
  |
  v
Push document_id to Redis Queue
  |
  v
Redis Worker
  |
  v
DocumentProcessingWorkflow.execute(document_id)
  |
  v
Update Document and ProcessingJob: PROCESSING
  |
  v
Document Classification from metadata
  |
  v
OCR Decision Engine
  |
  |-- Searchable PDF -> Native PDF Parser
  |-- Image / Scanned PDF -> PaddleOCR
  |
  v
Extract Text
  |
  v
OCR Confidence Evaluation
  |
  v
Refine Document Classification from extracted text
  |
  v
Store OCR Result and Metadata
  |
  v
Update Document and ProcessingJob: COMPLETED
  |
  v
Extracted Text API for Dev2
```

Failure path:

```text
PROCESSING -> FAILED
```

Both `documents.status` and `processing_jobs.job_status` are updated to `FAILED` on processing errors.

## 6. Status Lifecycle

Document lifecycle:

```text
PENDING -> PROCESSING -> COMPLETED
PENDING -> PROCESSING -> FAILED
FAILED -> PROCESSING -> COMPLETED, when a retry succeeds
```

ProcessingJob lifecycle:

```text
PENDING -> PROCESSING -> COMPLETED
PENDING -> PROCESSING -> FAILED
FAILED -> RETRY_QUEUED/PENDING -> PROCESSING, until retry limit is reached
```

Workflow stages:

- `LOAD_DOCUMENT`
- `UPDATE_PROCESSING_STATUS`
- `DOCUMENT_CLASSIFICATION`
- `OCR_DECISION`
- `OCR_EXECUTION`
- `STORE_OCR_RESULTS`
- `COMPLETE_WORKFLOW`



## 7. Module Responsibilities



### Upload Module

Files:

- `modules/upload/validator.py`
- `modules/upload/storage.py`
- `modules/upload/service.py`

Responsibilities:

- Validate file name, extension, size, and empty content.
- Store original file locally.
- Create `Document` record with status `PENDING`.
- Create `ProcessingJob` record with status `PENDING`.
- Publish Redis job with `document_id`.



### Redis Worker

Files:

- `redis_queue/producer.py`
- `redis_queue/consumer.py`
- `redis_queue/worker.py`

Responsibilities:

- Producer pushes jobs to Redis.
- Consumer reads jobs from Redis.
- Worker extracts `document_id` and calls `DocumentProcessingWorkflow.execute(document_id)`.
- Worker requeues failed jobs while `retry_count < PROCESSING_JOB_MAX_RETRIES`.
- Worker does not contain OCR, classification, or database business logic.



### Orchestration Module

Files:

- `orchestration/state.py`
- `orchestration/execution_plan.py`
- `orchestration/planner.py`
- `orchestration/workflow.py`

Responsibilities:

- Store workflow state.
- Define workflow steps.
- Decide execution order.
- Coordinate repositories, classification, OCR decision, extraction, confidence evaluation, OCR storage, status updates, and failure handling.



### Classification Module

File:

- `modules/classification/service.py`

Current behavior:

- Deterministic rule-based classification.
- No ML or LLM dependency.
- Classifies from metadata before OCR.
- Refines classification from extracted text after OCR.

Supported document types:

- `INVOICE`
- `RECEIPT`
- `MEDICAL_RECORD`
- `LAB_REPORT`
- `PRESCRIPTION`
- `INSURANCE`
- `BANK_STATEMENT`
- `TAX_FORM`
- `IDENTITY_DOCUMENT`
- `CONTRACT`
- `UNKNOWN`



### Extraction Module

Files:

- `modules/extraction/ocr.py`
- `modules/extraction/native.py`
- `modules/extraction/paddle.py`
- `modules/extraction/evaluation.py`
- `modules/extraction/service.py`

Responsibilities:

- Select extraction method.
- Extract text from searchable PDFs with PyMuPDF.
- Extract text from images and scanned PDFs with PaddleOCR.
- Evaluate production OCR confidence.
- Serve extracted text outputs to APIs.



## 8. OCR Decision Logic

Current OCR engine options:

- `NATIVE_PDF`
- `PADDLEOCR`
- `NATIVE_TEXT`

Decision behavior:

- Searchable PDF -> `NATIVE_PDF`
- Scanned PDF -> `PADDLEOCR`
- Image file -> `PADDLEOCR`
- Text/docx document -> `NATIVE_TEXT`

## 8.1 OCR Engine Comparison

| Feature | PaddleOCR (Current) | GLM OCR | Baidu OCR |
|---------|----------------------|---------|-----------|
| Type | Open Source | Vision Language Model | Cloud OCR API |
| Cost | Free | API/GPU Cost | API Cost |
| Offline Support | Yes | Depends on Deployment | No |
| Printed Text | Excellent | Excellent | Excellent |
| Scanned Documents | Excellent | Excellent | Excellent |
| Table Extraction | Good | Excellent | Excellent |
| Form/Layout Understanding | Basic | Advanced | Advanced |
| Handwriting | Moderate | Good | Good |
| Integration | Easy | Medium | Easy |

Current Choice

The current implementation uses **PaddleOCR** because it:

- Is open-source and free.
- Supports offline processing.
- Provides fast and accurate OCR for scanned PDFs and images.
- Is easy to integrate with the current FastAPI pipeline.

Future Enhancement

The OCR engine can be extended to support additional providers based on document complexity.

| Document Type | Recommended Engine |
|--------------|--------------------|
| Searchable PDF | Native PDF Extraction |
| Scanned PDF / Images | PaddleOCR |
| Complex Forms | GLM OCR |
| Complex Tables | GLM OCR / Baidu OCR |
| Handwritten Documents | GLM OCR |

## 9. OCR Confidence Evaluation

File:

- `modules/extraction/evaluation.py`

Purpose:

Production confidence estimates OCR quality without ground truth.

Method:

```text
WEIGHTED_ENGINE_TEXT_QUALITY_COVERAGE_V1
```

Formula:

```text
final_confidence =
  (raw_engine_confidence * 0.70) +
  (text_quality_score * 0.20) +
  (coverage_score * 0.10)
```

Signals:

- `raw_engine_confidence`: score returned by OCR engine.
- `text_quality_score`: readability/noise quality of extracted text.
- `coverage_score`: extracted text volume per page.

Quality caps:

- `text_quality_score < 0.30` caps final confidence at `0.45`.
- `text_quality_score < 0.50` caps final confidence at `0.65`.
- Very low coverage with weak text quality caps final confidence at `0.75`.
- Empty or placeholder text returns `0.0`.

Stored field:

```text
ocr_results.confidence_score
```



## 10. Database Tables



### documents

Stores uploaded document metadata.

Important fields:

- `id`
- `filename`
- `stored_filename`
- `file_type`
- `document_type`
- `file_size`
- `storage_path`
- `status`
- `created_at`
- `updated_at`



### processing_jobs

Tracks async processing state.

Important fields:

- `id`
- `document_id`
- `job_status`
- `workflow_stage`
- `queue_name`
- `worker_id`
- `retry_count`
- `error_message`
- `started_at`
- `completed_at`
- `created_at`
- `updated_at`



### ocr_results

Stores extracted text and OCR metadata.

Important fields:

- `id`
- `document_id`
- `extraction_method`
- `is_searchable`
- `extracted_text`
- `extracted_text_path`
- `page_count`
- `confidence_score`
- `processing_time`
- `created_at`
- `updated_at`



## 11. API Endpoints

Base URL:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```



### Health Check

```http
GET /health/
```



### Upload Single Document

```http
POST /upload/
```

Form field:

```text
file=<document>
```

Response example:

```json
{
  "message": "Document uploaded successfully.",
  "document": {
    "document_id": "document-uuid",
    "filename": "invoice.pdf",
    "status": "PENDING"
  }
}
```



### Upload Multiple Documents

```http
POST /upload/bulk
```

Form field:

```text
files=<document1>
files=<document2>
```



### Get Document Status

```http
GET /documents/{document_id}/status
```

Returns document status, processing status, workflow stage, OCR availability, and error details.

### Get Extracted Text

```http
GET /documents/{document_id}/text
```

Returns latest OCR result and metadata.

Important response fields:

- `document_id`
- `filename`
- `file_type`
- `document_type`
- `document_status`
- `processing_status`
- `workflow_stage`
- `ocr_result_id`
- `extraction_method`
- `is_searchable`
- `extracted_text`
- `page_count`
- `confidence_score`
- `processing_time`



## 12. Supported Upload Types

Supported extensions:

- `.pdf`
- `.png`
- `.jpg`
- `.jpeg`
- `.tiff`
- `.bmp`
- `.docx`
- `.txt`

Current validator limit:

```text
20 MB
```



## 13. Local Setup

Activate virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start PostgreSQL and Redis:

```powershell
docker compose up -d
```

Apply database migrations:

```powershell
python -m alembic upgrade head
```

Configured container names:

```text
datafactz-postgres
datafactz-redis
```

Open PostgreSQL shell:

```powershell
docker exec -it datafactz-postgres psql -U postgres -d pii_phi_document_intelligence_poc
```

Open Redis CLI:

```powershell
docker exec -it datafactz-redis redis-cli
```

Start FastAPI:

```powershell
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Start worker from project root:

```powershell
python redis_queue/worker.py
```



## 14. Testing Flow

Run automated tests:

```powershell
python -m pytest
```

Manual smoke test:

1. Start Docker services.
2. Apply migrations with `python -m alembic upgrade head`.
3. Start FastAPI.
4. Start Redis worker.
5. Upload document through `/upload/` or `/upload/bulk`.
6. Check `/documents/{document_id}/status`.
7. When completed, call `/documents/{document_id}/text`.

Expected examples:

- Searchable PDF -> `extraction_method=NATIVE_PDF`
- Image/scanned PDF -> `extraction_method=PADDLEOCR`
- Text document -> `extraction_method=NATIVE_TEXT`
- Invoice content -> `document_type=INVOICE`



## 15. Common Troubleshooting



### No such container: postgres

Use the actual configured name:

```powershell
docker exec -it datafactz-postgres psql -U postgres -d pii_phi_document_intelligence_poc
```



### No such container: redis

Use the actual configured name:

```powershell
docker exec -it datafactz-redis redis-cli
```



### No module named core

Run worker from project root:

```powershell
python redis_queue/worker.py
```



### Extracted text endpoint returns 404

Possible causes:

- Worker is not running.
- Redis job is still pending.
- Processing failed.
- OCR result does not exist yet.

Check:

```http
GET /documents/{document_id}/status
```



## 16. Dev2 Handoff

Dev2 should use:

```http
GET /documents/{document_id}/text
```

Required fields:

- `document_id`
- `filename`
- `file_type`
- `document_type`
- `extracted_text`
- `extraction_method`
- `is_searchable`
- `confidence_score`
- `page_count`
- `processing_status`
- `workflow_stage`

Dev2 should process only when:

```text
document_status = COMPLETED
processing_status = COMPLETED
extracted_text is not empty
```



## 17. Design Principles

- Worker stays thin.
- Workflow owns orchestration only.
- OCR decision is separate from OCR execution.
- Classification is separate from workflow.
- Confidence evaluation is separate from OCR extraction.
- Repositories own database access.
- APIs expose stable contracts for Dev2.

