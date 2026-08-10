# DocShield-AI Developer Runbook

This document is the detailed developer guide for DocShield-AI. For the shortest setup path, start with `README.md`.

## 1. Purpose

DocShield-AI processes uploaded documents through extraction, detection, human review, redaction, and reporting.

The backend is FastAPI. The proof-of-concept frontend is static HTML/CSS/JavaScript served by FastAPI at `/ui/`. Background processing is done by a Redis-backed Python worker. PostgreSQL stores workflow state and review/redaction/report metadata.

## 2. Runtime Separation

Docker and local Python are separate profiles. This prevents port conflicts and avoids leaking local credentials into containers.

| Profile | API | PostgreSQL | Redis | Environment source |
| --- | --- | --- | --- | --- |
| Docker | `http://localhost:8001` | `127.0.0.1:5433` | `127.0.0.1:6380` | `docker-compose.yml` |
| Local Python | `http://localhost:8000` | `127.0.0.1:5432` | `127.0.0.1:6379` | `.env.local` |

Rules:

- Use Docker port `5433`, not `5432`, for Docker Postgres.
- Use Docker port `6380`, not `6379`, for Docker Redis.
- Use `.env.local` only for local Python.
- Do not add fixed `container_name` values to Compose.
- Keep `qwen3:4b` as the only configured Ollama model.

## 3. Components

| Component | Responsibility |
| --- | --- |
| `app.py` | FastAPI app, routers, Swagger customization, startup validation |
| `api/routes` | Upload, document, review, redaction, report, and health endpoints |
| `api/schemas` | Pydantic API contracts |
| `frontend` | Static PoC UI |
| `database/models` | SQLAlchemy ORM models |
| `database/repositories` | Database access layer |
| `database/migrations` | Alembic migrations |
| `modules/upload` | File validation, file storage, DB document row creation, Redis enqueue |
| `modules/extraction` | TXT/DOCX/PDF/image extraction and OCR handling |
| `modules/classification` | Document type/domain classification |
| `modules/detection` | Detector orchestration, masking, confidence, deduplication |
| `orchestration` | End-to-end processing workflow |
| `redis_queue` | Redis producer, consumer, job schema, worker entrypoint |
| `storage` | Runtime files for uploads, extracted text, redactions, reports |

## 4. End-to-End Workflow

```text
Client uploads document
  -> FastAPI validates file
  -> API stores original file under storage/uploads
  -> API creates documents row
  -> API creates processing_jobs row
  -> API pushes job to Redis key document_processing
  -> Worker consumes Redis job
  -> Worker runs DocumentProcessingWorkflow
  -> Workflow classifies document/domain
  -> Workflow extracts text and OCR metadata
  -> Workflow stores ocr_results row
  -> Workflow writes extracted text artifact
  -> Workflow runs detection pipeline
  -> Workflow stores entities and confidence_scores rows
  -> Workflow creates reviews rows where human decision is needed
  -> Workflow creates redacted artifact
  -> Workflow creates audit report JSON
  -> Workflow marks document/job completed
```

Failure state:

```text
PROCESSING -> FAILED
```

Retry state:

```text
FAILED -> RETRY_QUEUED or PENDING -> PROCESSING
```

`workflow_stage` stores the current or failed stage. `last_completed_stage` stores the latest durable checkpoint so retries can avoid repeating completed work where supported.

## 5. Detection Workflow

Detection is routed by document domain and remaining unresolved candidate spans.

Generic, financial, corporate, and legal flow:

```text
Extracted text
  -> Regex
  -> mask accepted high-confidence spans
  -> check remaining candidates
  -> Presidio if needed
  -> mask accepted high-confidence spans
  -> check remaining candidates
  -> GLiNER if needed
  -> mask accepted high-confidence spans
  -> check remaining candidates
  -> Qwen3:4b only for unresolved/low-confidence spans
  -> Human Review for unresolved or final low-confidence results
```

Healthcare and mixed flow:

```text
Extracted text
  -> Regex
  -> mask accepted high-confidence spans
  -> check remaining candidates
  -> Presidio if needed
  -> mask accepted high-confidence spans
  -> check remaining candidates
  -> MedSpaCy if needed
  -> mask accepted high-confidence spans
  -> check remaining candidates
  -> GLiNER if needed
  -> mask accepted high-confidence spans
  -> check remaining candidates
  -> Qwen3:4b only for unresolved/low-confidence spans
  -> Human Review for unresolved or final low-confidence results
```

Confidence rule:

```text
Regex >= 80%     -> store/finalize that span
Regex < 80%      -> next detector
Presidio >= 80%  -> store/finalize that span
Presidio < 80%   -> next detector
MedSpaCy >= 80%  -> store/finalize that span
MedSpaCy < 80%   -> next detector
GLiNER >= 80%    -> store/finalize that span
GLiNER < 80%     -> Qwen3:4b
Qwen3:4b >= 80%  -> store/finalize that span
Qwen3:4b < 80%   -> Human Review
```

Important behavior:

- The pipeline does not stop just because Regex found something.
- A high-confidence span is masked so later detectors do not duplicate it.
- Remaining unresolved spans continue to the next detector.
- Qwen3:4b is a final detector, not a validation layer.
- Human review is the validation step.
- If a detector crashes, the error is logged, that detector is skipped, and the next detector runs when candidates remain.
- A detector crash should not fail the whole document unless the workflow cannot continue safely.

## 6. Detection UI Result Rule

The UI should display the final stored detector for each persisted entity row.

Example stored Regex result:

```text
Entity: ICD10_CODE
Value: E11.9
Category: PHI
Confidence: 85%
Detector: Regex
Status: Auto Ready or Review state from DB
Decision: Approve / Reject only when review is required
```

Example stored Qwen result:

```text
Entity: HOSPITAL_OR_FACILITY
Value: Farmington Medical Center
Category: PHI
Confidence: 96%
Detector: Qwen3:4b
Status: Auto Ready or Review state from DB
Decision: Approve / Reject only when review is required
```

Do not show detector chains like `Regex,ollama` unless the database intentionally stores a combined detector provenance field. The review UI should stay aligned with the persisted entity/review records.

## 7. Database Schema

Current Alembic head:

```text
0005_processing_job_checkpoint
```

Expected public tables:

```text
alembic_version
confidence_scores
documents
entities
ocr_results
processing_jobs
redactions
reports
reviews
```

Table responsibilities:

| Table | Purpose |
| --- | --- |
| `documents` | Uploaded document metadata and status |
| `processing_jobs` | Queue/workflow status, retry count, workflow checkpoints |
| `ocr_results` | Extracted text, OCR method, confidence, structured OCR metadata |
| `entities` | Persisted detected entity values and confidence |
| `confidence_scores` | Detailed confidence metadata per detection |
| `reviews` | Human review decisions and corrections |
| `redactions` | Redaction metadata and output file path |
| `reports` | Audit report metadata and output file path |
| `alembic_version` | Current migration version |

Useful SQL:

```sql
select id, filename, document_type, status, created_at
from documents
order by created_at desc
limit 20;

select document_id, job_status, workflow_stage, last_completed_stage, error_message, retry_count
from processing_jobs
order by created_at desc
limit 20;

select document_id, entity_type, entity_value, detector, confidence_score, is_review_required, is_redacted
from entities
order by created_at desc
limit 20;

select document_id, review_status, reviewer_decision, created_at
from reviews
order by created_at desc
limit 20;

select document_id, report_type, total_entities, total_redactions, review_completion, redaction_completion, report_path
from reports
order by created_at desc
limit 10;
```

## 8. Docker Runbook

Start Docker:

```powershell
cd E:\Office\DocShield-AI
.\scripts\docker-up.ps1
```

Equivalent raw command:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml up -d --build --remove-orphans
```

Check services:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml ps
```

Expected services:

| Service | Expected state | Host access |
| --- | --- | --- |
| `api` | running | `http://localhost:8001` |
| `worker` | running | no direct host port |
| `migrate` | exited 0 | no direct host port |
| `postgres` | healthy | `127.0.0.1:5433` |
| `redis` | healthy | `127.0.0.1:6380` |

Docker service notes:

- API uses `BYPASS_LLM=True` because it does not run document detection directly.
- Worker uses `BYPASS_LLM=False`, `OLLAMA_REQUIRED=True`, and `OLLAMA_REQUIRED_MODELS=qwen3:4b`.
- Containers reach Ollama through `http://host.docker.internal:11434`.
- The local GUI override bind mounts `./storage:/app/storage`.

Watch logs:

```powershell
.\scripts\docker-logs.ps1
```

Stop Docker:

```powershell
.\scripts\docker-down.ps1
```

## 9. Local Python Runbook

Initialize local environment:

```powershell
cd E:\Office\DocShield-AI
.\scripts\local-init.ps1
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Edit `.env.local`:

```text
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=pii_phi_document_intelligence_poc
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-local-password>
DATABASE_URL=postgresql+psycopg2://postgres:<your-local-password>@127.0.0.1:5432/pii_phi_document_intelligence_poc
REDIS_URL=redis://localhost:6379/0
OLLAMA_REQUIRED_MODELS=qwen3:4b
GLINER_ALLOW_MODEL_DOWNLOAD=True
HF_HOME=.cache/huggingface
DETECTION_HIGH_CONFIDENCE_THRESHOLD=0.80
```

Check local services:

```powershell
.\scripts\local-check.ps1
```

Run migrations:

```powershell
.\scripts\local-migrate.ps1
```

Run API:

```powershell
.\scripts\local-api.ps1
```

Run worker in a second terminal:

```powershell
cd E:\Office\DocShield-AI
.\.venv\Scripts\Activate.ps1
.\scripts\local-worker.ps1
```

Local UI:

```text
http://localhost:8000/ui/
```

## 10. UI Test

Use Docker UI unless you are specifically testing local Python:

```text
http://localhost:8001/ui/
```

Upload a `.txt` file:

```text
Patient Name: Jane Patient
Email: jane.patient@example.com
Phone: 9876543210
Hospital: Farmington Medical Center
Diagnosis: E11.9
Medication: Metformin
```

Expected flow:

```text
Upload succeeds
  -> document status changes from pending/processing to completed
  -> extracted text is visible
  -> review rows are visible when review is required
  -> redacted file is available
  -> audit report is available
```

If the UI stays pending, check worker logs:

```powershell
.\scripts\docker-logs.ps1
```

## 11. pgAdmin Test

Docker connection:

```text
Name: DocShield Docker
Host name/address: 127.0.0.1
Port: 5433
Maintenance database: pii_phi_document_intelligence_poc
Username: postgres
Password: postgres
```

Local connection:

```text
Name: DocShield Local
Host name/address: 127.0.0.1
Port: 5432
Maintenance database: pii_phi_document_intelligence_poc
Username: postgres
Password: value from .env.local
```

Refresh this path:

```text
Servers
  <server name>
    Databases
      pii_phi_document_intelligence_poc
        Schemas
          public
            Tables
```

You should see the 9 expected tables listed in the database schema section.

## 12. RedisInsight Test

Docker Redis connection:

```text
Name: DocShield Docker Redis
Host: 127.0.0.1
Port: 6380
Username: empty
Password: empty
```

Local Redis connection:

```text
Name: DocShield Local Redis
Host: 127.0.0.1
Port: 6379
Username: empty
Password: empty
```

Terminal check for Docker Redis:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml exec redis redis-cli ping
```

Expected output:

```text
PONG
```

Redis key:

```text
document_processing
```

The key may disappear or stay empty because the worker consumes jobs quickly.

## 13. Storage

Docker with `docker-compose.local-gui.yml` writes runtime artifacts to the repo:

```text
storage/uploads/
storage/extracted_text/
storage/redacted/
storage/reports/
```

Check files through the API container:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml exec api sh -lc "find /app/storage -maxdepth 3 -type f | sort"
```

Runtime files are ignored by git. Keep only `.gitkeep` placeholders if a directory needs to exist in a clean clone.

## 14. OCR Behavior

Extraction routing:

| Input | Engine |
| --- | --- |
| TXT/DOCX | Native text extraction |
| Searchable PDF | PyMuPDF native PDF text extraction |
| Scanned PDF | PaddleOCR |
| Mixed PDF | PyMuPDF for searchable pages, PaddleOCR for scanned pages |
| Image | PaddleOCR |

Mixed PDF output includes page-level metadata such as searchable pages, OCR pages, extraction method, and structured OCR output when available.

## 15. API Reference

Base URLs:

```text
Docker: http://localhost:8001
Local:  http://localhost:8000
```

Main endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Root status |
| GET | `/health/` | Health check |
| POST | `/upload/` | Upload one document |
| POST | `/upload/bulk` | Upload multiple documents |
| GET | `/documents/{document_id}/status` | Document and job status |
| GET | `/documents/{document_id}/text` | Extracted text and OCR metadata |
| GET | `/documents/{document_id}/reviews` | Review records |
| PATCH | `/reviews/{review_id}` | Approve/reject review item |
| GET | `/documents/{document_id}/redactions` | Redaction records |
| GET | `/redactions/{redaction_id}/file` | Download redacted file |
| GET | `/documents/{document_id}/reports` | Report list |
| GET | `/reports/{report_id}` | Report metadata and JSON |
| GET | `/reports/{report_id}/file` | Download report file |

Swagger UI:

```text
Docker: http://localhost:8001/docs
Local:  http://localhost:8000/docs
```

## 16. Tests

Run local tests:

```powershell
python -m pytest -q
```

Run tests inside Docker:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml exec api pytest -q
```

Focused detection tests:

```powershell
python -m pytest tests/test_detection.py tests/test_detector_selector.py tests/test_regex_detector.py -q
```

## 17. Troubleshooting

Docker project is missing or split in Docker Desktop:

```powershell
.\scripts\docker-up.ps1
```

Docker Postgres is not reachable:

```powershell
Test-NetConnection 127.0.0.1 -Port 5433
```

Docker Redis is not reachable:

```powershell
Test-NetConnection 127.0.0.1 -Port 6380
```

Local DB exists but tables are missing:

```powershell
.\scripts\local-migrate.ps1
```

Local Redis is not running on `6379`:

```powershell
docker run --name docshield-local-redis -p 6379:6379 -d redis:7
```

If that container already exists:

```powershell
docker start docshield-local-redis
```

Worker is failing or document remains pending:

```powershell
.\scripts\docker-logs.ps1
```

Dependency binary error after package changes:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml build --no-cache
```

Keep `numpy==1.26.4` unless the spaCy/thinc/MedSpaCy stack is retested.

## 18. Maintenance Rules

- Keep README focused on first-run setup.
- Keep detailed operating notes in this file.
- Keep Docker and local Python profiles separate.
- Do not commit `.env.local`, runtime uploads, extracted text, redacted files, or generated reports.
- Do not reintroduce `container_name` in Compose.
- Keep Ollama configuration on `qwen3:4b` unless the team explicitly changes the model decision.