# DocShield-AI

DocShield-AI is a FastAPI document-processing service for upload, OCR/text extraction, PII/PHI detection, human review, redaction artifacts, and audit reports. The repo also includes a static proof-of-concept UI served by the API at `/ui/`.

## What It Does

- Accepts single and bulk document uploads.
- Stores document and workflow state in PostgreSQL.
- Queues background work in Redis.
- Extracts text from TXT, DOCX, searchable PDFs, scanned PDFs, mixed PDFs, and images.
- Detects sensitive PII/PHI entities with a routed detector pipeline.
- Creates review rows for human approval/rejection.
- Produces redacted text files and JSON audit reports.
- Serves REST APIs, Swagger docs, and a static local UI.

## Runtime Profiles

Docker and local Python are intentionally separated. Do not mix their ports or environment files.

| Profile | API | PostgreSQL | Redis | Env source |
| --- | --- | --- | --- | --- |
| Docker | `http://localhost:8001` | `127.0.0.1:5433` | `127.0.0.1:6380` | values pinned in Compose |
| Local Python | `http://localhost:8000` | `127.0.0.1:5432` | `127.0.0.1:6379` | `.env.local` via `DOCSHIELD_ENV_FILE` |

Use Docker for the easiest full-system run. Use local Python when actively editing backend code.

## Requirements

- Windows PowerShell
- Python 3.10
- Docker Desktop
- Ollama with `qwen3:4b`
- PostgreSQL and Redis only when running the local Python profile
- spaCy English model `en_core_web_sm` for local Presidio detection

Install the required Ollama model:

```powershell
ollama pull qwen3:4b
```

Larger Qwen models are not used by this project.

## Docker Quick Start

Start the complete stack:

```powershell
cd E:\Office\DocShield-AI
.\scripts\docker-up.ps1
```

Check status:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml ps
```

Expected Docker Desktop group:

```text
docshield-ai-live
  api        8001:8000
  worker
  migrate   exited 0 is OK
  postgres  5433:5432 healthy
  redis     6380:6379 healthy
```

Open the app:

```text
http://localhost:8001/ui/
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8001/health/
```

Watch logs:

```powershell
.\scripts\docker-logs.ps1
```

Stop Docker:

```powershell
.\scripts\docker-down.ps1
```

## Test Through UI

Open:

```text
http://localhost:8001/ui/
```

Upload a `.txt` file with sample content:

```text
Patient Name: Jane Patient
Email: jane.patient@example.com
Phone: 9876543210
Hospital: Farmington Medical Center
Diagnosis: E11.9
Medication: Metformin
```

Expected result:

- Upload succeeds.
- Document status moves through processing.
- Extracted text appears.
- Detected entities appear in review results.
- Low-confidence results are sent to human review.
- Redaction and report artifacts are created.

## pgAdmin

For Docker, register this server:

```text
Name: DocShield Docker
Host name/address: 127.0.0.1
Port: 5433
Maintenance database: pii_phi_document_intelligence_poc
Username: postgres
Password: postgres
```

For local Python, use port `5432` and the password from `.env.local`.

Expected tables under `public`:

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

## RedisInsight

For Docker Redis:

```text
Name: DocShield Docker Redis
Host: 127.0.0.1
Port: 6380
Username: empty
Password: empty
```

Queue key:

```text
document_processing
```

The queue can be empty during normal operation because the worker consumes jobs quickly.

## Local Python Setup

Initialize local files and virtual environment:

```powershell
cd E:\Office\DocShield-AI
.\scripts\local-init.ps1
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Edit `.env.local` and make sure the PostgreSQL password is correct in both:

```text
POSTGRES_PASSWORD=...
DATABASE_URL=postgresql+psycopg2://postgres:...@127.0.0.1:5432/pii_phi_document_intelligence_poc
```

Check local dependencies:

```powershell
.\scripts\local-check.ps1
```

Run migrations:

```powershell
.\scripts\local-migrate.ps1
```

Run the API:

```powershell
.\scripts\local-api.ps1
```

Run the worker in a second terminal:

```powershell
cd E:\Office\DocShield-AI
.\.venv\Scripts\Activate.ps1
.\scripts\local-worker.ps1
```

Local UI:

```text
http://localhost:8000/ui/
```

## Detection Pipeline

Generic, financial, corporate, and legal documents:

```text
Regex -> Presidio -> GLiNER -> Qwen3:4b -> Human Review if still low confidence
```

Healthcare and mixed documents:

```text
Regex -> Presidio -> MedSpaCy -> GLiNER -> Qwen3:4b -> Human Review if still low confidence
```

Confidence rule:

```text
Detector confidence >= 80% -> keep result and do not escalate that span
Detector confidence < 80%  -> route unresolved/low-confidence span to next detector
Qwen3:4b confidence < 80%  -> send to human review
```

LLM validation is not used. Human review is the validation step.

## Main API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Root status |
| GET | `/health/` | Service health |
| POST | `/upload/` | Upload one document |
| POST | `/upload/bulk` | Upload multiple documents |
| GET | `/documents/{document_id}/status` | Document and job status |
| GET | `/documents/{document_id}/text` | Extracted text |
| GET | `/documents/{document_id}/reviews` | Review records |
| PATCH | `/reviews/{review_id}` | Approve/reject review item |
| GET | `/documents/{document_id}/redactions` | Redaction records |
| GET | `/redactions/{redaction_id}/file` | Download redacted file |
| GET | `/documents/{document_id}/reports` | Report list |
| GET | `/reports/{report_id}` | Report metadata and JSON |
| GET | `/reports/{report_id}/file` | Download report file |

## Project Structure

```text
DocShield-AI/
|-- api/                  FastAPI routes and schemas
|-- core/                 App settings and shared infrastructure
|-- database/             SQLAlchemy models, repositories, Alembic migrations
|-- frontend/             Static UI served at /ui/
|-- modules/              Upload, extraction, classification, detection logic
|-- orchestration/        End-to-end document workflow
|-- redis_queue/          Redis producer/consumer and worker
|-- scripts/              Local and Docker helper scripts
|-- docs/                 Extra runbooks
|-- tests/                Pytest suite
|-- storage/              Runtime artifacts, ignored by git
|-- app.py                FastAPI entrypoint
|-- docker-compose.yml
|-- docker-compose.local-gui.yml
|-- Dockerfile
|-- requirements.txt
```

## Tests

Run locally:

```powershell
python -m pytest -q
```

Run inside Docker API container:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml exec api pytest -q
```

## Troubleshooting

If Docker containers are not grouped correctly in Docker Desktop, always start with:

```powershell
.\scripts\docker-up.ps1
```

If pgAdmin cannot connect to Docker Postgres:

```powershell
Test-NetConnection 127.0.0.1 -Port 5433
```

If RedisInsight cannot connect to Docker Redis:

```powershell
Test-NetConnection 127.0.0.1 -Port 6380
```

If local Python check fails on Redis `6379`, start a local Redis instance or point `.env.local` to a running Redis service.

If the worker restarts after dependency changes, rebuild Docker:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml build --no-cache
```

## More Detail

Read `doc.md` for the detailed developer runbook and `docs/run_profiles.md` for the runtime-profile rules.