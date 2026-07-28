# DocShield-AI Documentation

## 1. Purpose

DocShield-AI is an API-only document intelligence backend. It accepts uploaded documents, stores metadata, queues work in Redis, processes documents through a worker, extracts text/OCR layout, detects sensitive entities, creates review records, writes redaction artifacts, and generates audit reports.

The frontend is intentionally not part of the current repo state.

## 2. Current Status

Completed:

- FastAPI application and Swagger/OpenAPI docs.
- PostgreSQL schema, SQLAlchemy models, repositories, and Alembic migrations.
- Redis queue producer, consumer, and worker.
- Single and bulk document upload APIs.
- Document status and extracted text APIs.
- Human review APIs.
- Redaction metadata and artifact download APIs.
- Report metadata and artifact download APIs.
- Native text extraction for TXT and DOCX.
- Native PDF extraction with PyMuPDF.
- PaddleOCR extraction for scanned PDFs and images.
- Optional layout-preserving OCR metadata.
- PII/PHI entity detection pipeline.
- Worker retry behavior.
- Docker Compose setup for API, worker, migration, Postgres, and Redis.
- Local pytest coverage for workflow, API, PaddleOCR layout parsing, and worker retry logic.

Pending / future work:

- Production authentication and authorization.
- Production object storage such as S3 or MinIO.
- Production monitoring and audit dashboards.
- Full Dev2 handoff hardening.
- Optional OCR/model provider benchmarking, including Ollama-backed paths.

## 3. Runtime Components

| Component | Responsibility |
| --- | --- |
| `app.py` | FastAPI app, routers, Swagger UI customization, startup validation |
| `api/routes` | REST endpoints for upload, documents, reviews, redactions, reports, health |
| `api/schemas` | Pydantic request/response contracts |
| `database/models` | SQLAlchemy tables |
| `database/repositories` | Database access helpers |
| `database/migrations` | Alembic migration scripts |
| `modules/upload` | File validation, storage, DB record creation, Redis publish |
| `modules/extraction` | Native text/PDF extraction and PaddleOCR extraction |
| `modules/detection` | PII/PHI detection, confidence, deduplication, masking support |
| `orchestration` | End-to-end document processing workflow |
| `redis_queue` | Redis producer, consumer, worker, job schema |
| `storage` | Uploaded files and generated text/report artifacts |

## 4. Processing Flow

```text
Client uploads document
  -> API validates file
  -> API stores original file
  -> API creates documents and processing_jobs rows
  -> API pushes document_processing job to Redis
  -> Worker consumes Redis job
  -> Worker runs DocumentProcessingWorkflow
  -> Workflow classifies document
  -> Workflow selects extraction engine
  -> Workflow extracts text/OCR metadata
  -> Workflow stores ocr_results and extracted text file
  -> Workflow detects PII/PHI entities
  -> Workflow stores entities and confidence scores
  -> Workflow creates review records when needed
  -> Workflow creates redacted text artifact
  -> Workflow creates audit report JSON artifact
  -> Workflow marks document/job completed
```

Failure path:

```text
PROCESSING -> FAILED
```

Worker retry path:

```text
FAILED -> RETRY_QUEUED/PENDING -> PROCESSING
```

## 5. Docker Setup

Recommended command for local validation with Docker Desktop, pgAdmin4, RedisInsight, and local storage files:

```powershell
cd E:\Office\DocShield-AI

docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml up -d --build
```

Check containers:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml ps
```

Expected services:

| Service | Expected state | Host access |
| --- | --- | --- |
| `api` | running | `http://localhost:8001` |
| `worker` | running | no host port |
| `migrate` | exited 0 | no host port |
| `postgres` | healthy | `127.0.0.1:5433` |
| `redis` | healthy | `127.0.0.1:6380` |

Health check:

```powershell
Invoke-RestMethod http://localhost:8001/health/
```

Swagger UI:

```text
http://localhost:8001/docs
```

## 6. Local GUI Override

`docker-compose.local-gui.yml` is used to avoid conflicts with other projects and expose convenient local ports.

Current expected file:

```yaml
services:
  migrate:
    container_name: docshield-ai-live-migrate

  api:
    container_name: docshield-ai-live-api
    ports: !override
      - "8001:8000"
    volumes: !override
      - ./storage:/app/storage

  worker:
    container_name: docshield-ai-live-worker
    volumes: !override
      - ./storage:/app/storage

  postgres:
    container_name: docshield-ai-live-postgres
    ports: !override
      - "5433:5432"

  redis:
    container_name: docshield-ai-live-redis
    ports: !override
      - "6380:6379"
```

Why these ports are used:

- `8001` keeps this API separate from any service already using `8000`.
- `5433` avoids conflicts with another local PostgreSQL on `5432`.
- `6380` avoids conflicts with another local Redis on `6379`.

## 7. pgAdmin4

Register a server with:

```text
Name: DocShield Live
Host name/address: 127.0.0.1
Port: 5433
Maintenance database: pii_phi_document_intelligence_poc
Username: postgres
Password: postgres
```

Useful tables:

```text
documents
processing_jobs
ocr_results
entities
confidence_scores
reviews
redactions
reports
```

Useful SQL:

```sql
select id, filename, document_type, status, created_at
from documents
order by created_at desc
limit 20;

select document_id, job_status, workflow_stage, error_message, retry_count
from processing_jobs
order by created_at desc
limit 20;

select document_id, extraction_method, confidence_score, left(extracted_text, 200) as preview
from ocr_results
order by created_at desc
limit 10;

select document_id, entity_type, entity_value, confidence_score, is_review_required, is_redacted
from entities
order by created_at desc
limit 20;

select document_id, report_type, total_entities, total_redactions, review_completion, redaction_completion, report_path
from reports
order by created_at desc
limit 10;
```

## 8. RedisInsight

Add Redis with:

```text
Name: DocShield Live Redis
Host: 127.0.0.1
Port: 6380
Username: leave empty
Password: leave empty
```

Queue key:

```text
document_processing
```

The queue can be empty even when the system is working because the worker uses blocking pop and consumes jobs quickly.

## 9. Storage

With `docker-compose.local-gui.yml`, generated files are bind mounted to the repo:

```text
storage/uploads/
storage/extracted_text/
storage/redacted/
storage/reports/
```

If only `docker-compose.yml` is used, API and worker use Docker named volume `app_storage`, so files will not appear in the local `storage` folder.

Check files inside the API container:

```powershell
docker exec docshield-ai-live-api sh -lc "find /app/storage -maxdepth 3 -type f | sort"
```

## 10. API Endpoints

Base URL for the live Docker setup:

```text
http://localhost:8001
```

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health/` | Service health |
| POST | `/upload/` | Upload one document |
| POST | `/upload/bulk` | Upload multiple documents |
| GET | `/documents/{document_id}/status` | Document status, job status, workflow stage, OCR availability |
| GET | `/documents/{document_id}/text` | Latest extracted text and OCR metadata |
| GET | `/documents/{document_id}/reviews` | Review records for a document |
| PATCH | `/reviews/{review_id}` | Reviewer decision and optional entity corrections |
| GET | `/documents/{document_id}/redactions` | Redaction records for a document |
| GET | `/redactions/{redaction_id}/file` | Redacted text artifact download |
| GET | `/documents/{document_id}/reports` | Report records for a document |
| GET | `/reports/{report_id}` | Report metadata and JSON payload |
| GET | `/reports/{report_id}/file` | Report artifact download |

## 11. Smoke Test

Upload the sample invoice:

```powershell
$response = Invoke-RestMethod `
  -Uri http://localhost:8001/upload/ `
  -Method Post `
  -Form @{ file = Get-Item .\sample-invoice.txt }

$documentId = $response.document.document_id
$documentId
```

Check processing:

```powershell
Invoke-RestMethod "http://localhost:8001/documents/$documentId/status"
```

Check outputs:

```powershell
Invoke-RestMethod "http://localhost:8001/documents/$documentId/text"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/reviews"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/redactions"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/reports"
```

Expected database changes:

- `documents` has one new row.
- `processing_jobs` moves to `COMPLETED` or records an error.
- `ocr_results` has extracted text.
- `entities` has detected sensitive values when present.
- `reviews`, `redactions`, and `reports` are populated by the workflow.

Expected local files:

- Original upload in `storage/uploads/`.
- Extracted text in `storage/extracted_text/`.
- Redacted text in `storage/redacted/`.
- Audit report JSON in `storage/reports/`.

## 12. Supported Upload Types

Supported extensions:

```text
.pdf
.png
.jpg
.jpeg
.tiff
.bmp
.docx
.txt
```

The Docker compose environment sets:

```text
MAX_FILE_SIZE_MB=100
```

## 13. OCR Behavior

Extraction routing:

| Input | Engine |
| --- | --- |
| Searchable PDF | Native PDF extraction with PyMuPDF |
| Scanned PDF | PaddleOCR |
| Image | PaddleOCR |
| TXT/DOCX | Native text extraction |

PaddleOCR can return both:

- `extracted_text`: plain text used by downstream detection.
- `structured_output`: optional page/block/line/table metadata.

When PP-Structure is unavailable, the code falls back to bounding-box reconstruction.

## 14. Local Python Development

Use a virtual environment only for non-Docker development:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

Run locally:

```powershell
python -m alembic upgrade head
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
python redis_queue/worker.py
```

For local Python runs, `.env.example` shows the expected variables. Copy it to `.env` if needed.

## 15. Testing

Run the automated test suite:

```powershell
pytest -q
```

Important current test areas:

- Upload to extracted text API flow.
- Review decision API.
- Redaction and report artifact APIs.
- Native text workflow completion.
- Failure handling for missing files.
- Structured PaddleOCR output persistence.
- PaddleOCR layout reconstruction.
- Worker retry behavior.

## 16. Troubleshooting

### pgAdmin connection timeout

Use `127.0.0.1` and port `5433` for the live setup.

```powershell
Test-NetConnection 127.0.0.1 -Port 5433
```

### RedisInsight cannot connect

Use `127.0.0.1` and port `6380`.

```powershell
Test-NetConnection 127.0.0.1 -Port 6380
```

### Storage folder is empty

Make sure the local GUI override is included. It bind mounts `./storage:/app/storage`.

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml up -d
```

### Worker is restarting

Check logs:

```powershell
docker logs docshield-ai-live-worker --tail 100
```

If logs mention NumPy/spaCy binary incompatibility, keep this pin in `requirements.txt`:

```text
numpy==1.26.4
```

Then rebuild:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml build --no-cache
```

### API works but document stays pending

Check worker logs and Redis queue state:

```powershell
docker logs docshield-ai-live-worker --tail 100
```

In RedisInsight, inspect key:

```text
document_processing
```

## 17. Operational Notes

- `BYPASS_LLM=True` in Docker compose keeps Ollama validation optional.
- `OLLAMA_REQUIRED=False` means startup will not fail when Ollama is unavailable.
- `PADDLEOCR_LAYOUT_ANALYSIS_ENABLED=True` enables layout attempts when supported by the installed PaddleOCR package.
- Do not upgrade NumPy to 2.x with the current spaCy/thinc/medspacy stack unless the Docker worker is retested.
