# DocShield-AI

DocShield-AI is a FastAPI backend for document ingestion, OCR/text extraction, PII/PHI detection, human-review records, redaction artifacts, and audit reports.

This repo includes the FastAPI backend and a lightweight static PoC UI served at `/ui/` by the same API process.

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
- Provide a static PoC workspace for uploads, status polling, review actions, extracted-text preview, and artifact downloads.

## Tech Stack

| Area | Technology |
| --- | --- |
| API | FastAPI |
| Database | PostgreSQL |
| ORM/Migrations | SQLAlchemy, Alembic |
| Queue | Redis |
| Worker | Python worker process |
| OCR | PyMuPDF, PaddleOCR |
| Detection | Dynamic orchestrator over Regex, Presidio, MedSpaCy, GLiNER, optional Qwen/Ollama validation |
| Storage | Local filesystem or Docker volume |
| Frontend | Static HTML/CSS/JavaScript mounted by FastAPI at `/ui` |
| Tests | Pytest |

## Dynamic Detection Orchestrator

The detection pipeline is dynamically routed inside `modules/detection` without changing API contracts, database tables, or workflow steps.

Core behavior:

- Routes detectors by document domain: financial, healthcare, corporate/legal, or generic.
- Runs one detector at a time on remaining unmasked candidate spans.
- If a detector finds no entities, the orchestrator continues to the next appropriate detector when candidates remain.
- Passes each detector an `orchestration_context` containing remaining text, previous entities, remaining candidates, and executed/skipped detectors.
- Stops on remaining entity candidates, not just leftover text, so labels or harmless prose do not trigger unnecessary model work.
- Uses Qwen/Ollama only for unresolved candidate snippets or low-confidence entity snippets. It never sends the full document.
- Final output is normalized, confidence-calibrated, deduplicated, overlap-resolved, and compatible with existing APIs and DB models.
- Regex detection now extracts clean value spans from labeled fields such as patient/provider/doctor names, organizations, addresses, employment IDs, government IDs, financial IDs, insurance fields, dates, and clinical fields.
- Placeholder or generic labeled values are rejected, and bank account values are kept separate from credit-card matches.
- Deduplication is span-aware: the same value at different document positions is preserved as separate redaction targets, while duplicate detector hits on the same span are merged.
- Presidio includes supplemental person detection for employment-verification prose.

Default knobs are in `.env.example`:

```env
DETECTION_HIGH_CONFIDENCE_THRESHOLD=0.85
DETECTION_MEDIUM_CONFIDENCE_THRESHOLD=0.60
DETECTION_LLM_VALIDATION_THRESHOLD=0.60
DETECTION_SEMANTIC_REASONING_THRESHOLD=0.80
DETECTION_STOPPING_CANDIDATE_THRESHOLD=0
DETECTION_MIN_CANDIDATE_CHARS=3
DETECTION_LLM_CONTEXT_WINDOW=160
DETECTION_MAX_UNRESOLVED_LLM_CONTEXTS=8
DETECTION_UNRESOLVED_LLM_ENABLED=True
```

Docker Compose currently keeps `BYPASS_LLM=True`, so Qwen/Ollama paths are skipped unless you explicitly enable and provide Ollama.

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
|-- frontend/
|   |-- index.html
|   |-- app.js
|   |-- styles.css
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
| PoC UI | `http://localhost:8001/ui/` |
| Swagger UI | `http://localhost:8001/docs` |
| PostgreSQL | `127.0.0.1:5433` |
| Redis | `127.0.0.1:6380` |

Health check:

```powershell
Invoke-RestMethod http://localhost:8001/health/
```

Open the static UI:

```text
http://localhost:8001/ui/
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
@"
Patient Name: Jane Patient
Email: jane.patient@example.com
Phone: 9876543210
Diagnosis: Hypertension
Medication: Metformin
"@ | Set-Content -Path .\docshield-smoke.txt

$response = Invoke-RestMethod `
  -Uri http://localhost:8001/upload/ `
  -Method Post `
  -Form @{ file = Get-Item .\docshield-smoke.txt }

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

## Check In Docker

After Docker is running, verify the orchestrator from inside the API container:

```powershell
docker exec docshield-ai-live-api pytest tests/test_detection.py -q
docker exec docshield-ai-live-api pytest tests/test_regex_detector.py -q
docker exec docshield-ai-live-api pytest -q
```

Run a live API/worker smoke test with a local sample file:

```powershell
@"
Patient Name: Jane Patient
Email: jane.patient@example.com
Phone: 9876543210
Diagnosis: Hypertension
Medication: Metformin
"@ | Set-Content -Path .\docker-detection-smoke.txt

$response = Invoke-RestMethod `
  -Uri http://localhost:8001/upload/ `
  -Method Post `
  -Form @{ file = Get-Item .\docker-detection-smoke.txt }

$documentId = $response.document.document_id
$documentId
```

Poll until the worker completes:

```powershell
for ($i = 0; $i -lt 30; $i++) {
  $status = Invoke-RestMethod "http://localhost:8001/documents/$documentId/status"
  if ($status.document_status -in @("COMPLETED", "FAILED")) { $status; break }
  Start-Sleep -Seconds 2
}
```

Inspect outputs:

```powershell
Invoke-RestMethod "http://localhost:8001/documents/$documentId/text"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/reviews"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/redactions"
Invoke-RestMethod "http://localhost:8001/documents/$documentId/reports"
```

Check worker logs for detector routing:

```powershell
docker logs docshield-ai-live-worker --tail 200 | Select-String -Pattern "Dynamic detection|Executing detector|remaining_candidates|Qwen"
```

Check stored entities in PostgreSQL:

```powershell
docker exec docshield-ai-live-postgres psql -U postgres -d pii_phi_document_intelligence_poc -c "select document_id, entity_type, entity_value, detector, confidence_score from entities order by created_at desc limit 20;"
```

Check generated artifacts:

```powershell
docker exec docshield-ai-live-api sh -lc "find /app/storage -maxdepth 3 -type f | sort"
```

## Main APIs

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/` | Root status payload |
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

Bulk upload accepts up to 100 files per request. The current validator enforces a 20 MB per-file limit in `modules/upload/validator.py`; `MAX_FILE_SIZE_MB` is present in environment config but is not yet wired into upload validation.

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
