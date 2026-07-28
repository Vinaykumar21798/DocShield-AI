# DocShield-AI

DocShield-AI is a FastAPI backend for document ingestion, OCR/text extraction, PII/PHI detection, human-review records, redaction artifacts, and audit reports.

This repo is API-only right now. The frontend was removed for the current phase.

## What It Does

- Upload single or multiple documents.
- Store document metadata in PostgreSQL.
- Push processing jobs to Redis.
- Run background processing through the worker.
- Extract text from TXT, DOCX, searchable PDFs, scanned PDFs, and images.
- Preserve optional layout metadata for PaddleOCR outputs.
- Detect sensitive entities and persist confidence scores.
- Create review, redaction, and report records.
- Save generated artifacts under `storage/`.
- Expose REST APIs through FastAPI and Swagger/OpenAPI.

## Tech Stack

| Area | Technology |
| --- | --- |
| API | FastAPI |
| Database | PostgreSQL |
| ORM/Migrations | SQLAlchemy, Alembic |
| Queue | Redis |
| Worker | Python worker process |
| OCR | PyMuPDF, PaddleOCR |
| Detection | Regex, Presidio, MedSpaCy, GLiNER, optional Ollama validation |
| Storage | Local filesystem or Docker volume |
| Tests | Pytest |

## Project Structure

```text
DocShield-AI/
|-- api/
|   |-- routes/
|   |-- schemas/
|   |-- dependencies.py
|-- core/
|-- database/
|   |-- migrations/
|   |-- models/
|   |-- repositories/
|-- modules/
|   |-- classification/
|   |-- detection/
|   |-- extraction/
|   |-- upload/
|-- orchestration/
|-- redis_queue/
|-- storage/
|-- tests/
|-- app.py
|-- docker-compose.yml
|-- docker-compose.local-gui.yml
|-- Dockerfile
|-- requirements.txt
|-- README.md
|-- doc.md
```

## Docker Quick Start

Use this path when testing with Docker Desktop, pgAdmin4, and RedisInsight.

```powershell
cd E:\Office\DocShield-AI

docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml up -d --build

docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml ps
```

Expected exposed ports:

| Service | Host URL / Port |
| --- | --- |
| API | `http://localhost:8001` |
| Swagger UI | `http://localhost:8001/docs` |
| PostgreSQL | `127.0.0.1:5433` |
| Redis | `127.0.0.1:6380` |

Health check:

```powershell
Invoke-RestMethod http://localhost:8001/health/
```

## pgAdmin4 Connection

Register a new server in pgAdmin4 with:

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

## RedisInsight Connection

Add a Redis database in RedisInsight with:

```text
Name: DocShield Live Redis
Host: 127.0.0.1
Port: 6380
Username: leave empty
Password: leave empty
```

The queue key is:

```text
document_processing
```

The queue may be empty during normal operation because the worker consumes jobs quickly.

## Storage

With `docker-compose.local-gui.yml`, API and worker both bind mount local storage:

```yaml
./storage:/app/storage
```

Generated files should appear locally under:

```text
storage/uploads/
storage/extracted_text/
storage/redacted/
storage/reports/
```

If you run only `docker-compose.yml`, files are stored in the Docker named volume `app_storage` instead of the local repo folder.

## Test Upload

```powershell
$response = Invoke-RestMethod `
  -Uri http://localhost:8001/upload/ `
  -Method Post `
  -Form @{ file = Get-Item .\sample-invoice.txt }

$documentId = $response.document.document_id
$documentId
```

Check status and outputs:

```powershell
Invoke-RestMethod "http://localhost:8001/documents/$documentId/status"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/text"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/reviews"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/redactions"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/reports"
```

Check worker logs if processing does not complete:

```powershell
docker logs docshield-ai-live-worker --tail 100
```

## Main APIs

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health/` | Health check |
| POST | `/upload/` | Upload one document |
| POST | `/upload/bulk` | Upload multiple documents |
| GET | `/documents/{document_id}/status` | Document and processing status |
| GET | `/documents/{document_id}/text` | Extracted text and OCR metadata |
| GET | `/documents/{document_id}/reviews` | Review records for detected entities |
| PATCH | `/reviews/{review_id}` | Submit reviewer decision/corrections |
| GET | `/documents/{document_id}/redactions` | Redaction metadata |
| GET | `/redactions/{redaction_id}/file` | Download redacted artifact |
| GET | `/documents/{document_id}/reports` | Report metadata list |
| GET | `/reports/{report_id}` | Report metadata and JSON payload |
| GET | `/reports/{report_id}/file` | Download report artifact |

## Supported Upload Types

- PDF
- PNG
- JPG/JPEG
- TIFF
- BMP
- DOCX
- TXT

## Local Python Development

A virtual environment is needed only when running Python outside Docker.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

Run API and worker locally:

```powershell
python -m alembic upgrade head
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
python redis_queue/worker.py
```

## Troubleshooting

If pgAdmin cannot connect, verify you are using port `5433`, not `5432`:

```powershell
Test-NetConnection 127.0.0.1 -Port 5433
```

If RedisInsight cannot connect, verify port `6380`:

```powershell
Test-NetConnection 127.0.0.1 -Port 6380
```

If Docker reports container-name conflicts, use the live project command with both compose files:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml up -d
```

If worker logs show a NumPy/spaCy binary error, keep `numpy==1.26.4` in `requirements.txt` and rebuild:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml build --no-cache
```
