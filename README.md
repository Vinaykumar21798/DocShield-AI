# DocShield-AI

DocShield-AI is a functional proof of concept for detecting and redacting PII and PHI in healthcare and enterprise documents. It combines deterministic rules, statistical and clinical NLP, and an optional bounded-context LLM pass. Processing runs asynchronously through Redis, persists workflow state in PostgreSQL, and produces a redacted text artifact plus a JSON audit report.

> This repository is not production-hardened. Redaction currently targets extracted text, not the original PDF, and the PoC does not provide encryption at rest or a post-review release gate.

## Capabilities

- Upload one file or up to 100 files per run.
- Accept PDF, TXT, DOCX, PNG, JPG/JPEG, TIFF, and BMP files; the current validator enforces a 20 MB per-file limit.
- Extract searchable PDF text with PyMuPDF and route scanned or mixed PDFs through OCR.
- Classify document type and select a domain-aware detector route.
- Detect sensitive spans with Regex, Presidio, GLiNER, MedSpaCy, and an optional Azure OpenAI or Ollama detector.
- Validate, normalize, deduplicate, and resolve overlapping spans.
- Create human-review records for entities with final confidence below `0.80`.
- Expand repeat occurrences before redaction.
- Run bounded deterministic safety passes and fail closed if residual deterministic PII remains.
- Store redacted `.txt` output and a JSON report with detector and LLM decision audit data.
- Authenticate users with bearer sessions and role checks for `USER`, `REVIEWER`, and `ADMIN`.

## Processing flow

```text
Upload
  -> Run/document creation and Redis enqueue
  -> Classification
  -> Native extraction, OCR, or mixed-PDF extraction
  -> Domain detector route
       healthcare: Regex -> MedSpaCy -> Presidio -> GLiNER -> LLM
       generic:    Regex -> Presidio -> GLiNER -> LLM
  -> EntityValidator -> normalization -> deduplication -> overlap resolution
  -> Confidence calibration and human-review creation
  -> Occurrence expansion and text redaction
  -> Deterministic residual-PII cleanup and fail-closed verification
  -> Redacted text and JSON audit report
```

The LLM stage is optional. Candidate contexts are bounded to approximately 80 characters around unresolved candidates and limited to three prioritized contexts per page/document pass. High-risk account, identity, policy, medical-record, and card cues are prioritized within that limit.

## Technology

- Python 3.10, FastAPI, Pydantic
- PostgreSQL, SQLAlchemy, Alembic
- Redis and a custom Redis worker
- PyMuPDF and PaddleOCR
- Presidio, GLiNER, MedSpaCy
- Azure OpenAI or Ollama (`gemma4:e4b` by default)
- Vanilla JavaScript, HTML, and CSS

## Local setup on Windows

Prerequisites:

- Python 3.10
- PostgreSQL 15 or newer on `127.0.0.1:5432`
- Redis 7 or newer on `127.0.0.1:6379`
- PowerShell
- Ollama only when using the local LLM profile

Initialize the environment:

```powershell
cd <path-to-repo>
.\scripts\local-init.ps1
```

The script creates `.venv`, copies `.env.example` to `.env.local` when needed, installs Python dependencies, and installs the spaCy English model. Edit `.env.local` before continuing. Do not commit `.env` or `.env.local`.

For Ollama:

```powershell
ollama pull gemma4:e4b
```

Example LLM settings:

```ini
# Local Ollama
LLM_PROVIDER=gemma
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma4:e4b
BYPASS_LLM=false

# Or Azure OpenAI
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=replace_me
AZURE_OPENAI_DEPLOYMENT=gpt-5.4-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
BYPASS_LLM=false
```

Check dependencies and services, migrate the database, and start both processes:

```powershell
.\scripts\local-check.ps1
.\scripts\local-migrate.ps1
```

```powershell
# Terminal 1
.\scripts\local-api.ps1

# Terminal 2
.\scripts\local-worker.ps1
```

Open `http://localhost:8000/ui/`.

Configuration precedence is: process environment, then the explicitly selected `DOCSHIELD_ENV_FILE`; for the default profile, `.env.local` is loaded before `.env`. The local scripts explicitly select `.env.local`.

## Docker setup

```powershell
.\scripts\docker-up.ps1
```

Open `http://localhost:8001/ui/`. Docker publishes PostgreSQL on `5433` and Redis on `6380` while containers use their internal service ports. Stop the stack with:

```powershell
.\scripts\docker-down.ps1
```

Docker defaults are defined in `docker-compose.yml`; review them before any non-local deployment.

## API overview

Most endpoints require `Authorization: Bearer <token>`.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/auth/signup` | Public | Create a user and session |
| `POST` | `/auth/login` | Public | Create a session |
| `POST` | `/auth/logout` | Authenticated | Invalidate the current session |
| `GET` | `/health/` | Public | Health check |
| `POST` | `/upload/` | User, Reviewer, Admin | Upload one document |
| `POST` | `/upload/bulk` | User, Reviewer, Admin | Upload up to 100 documents |
| `GET` | `/documents/runs/{run_id}` | User, Reviewer, Admin | Run progress |
| `GET` | `/documents/{id}/status` | Authorized owner/role | Processing status |
| `GET` | `/documents/{id}/text` | Authorized owner/role | Extracted text and OCR metadata |
| `GET` | `/documents/{id}/entities` | Reviewer, Admin | Detected entities |
| `GET` | `/documents/{id}/reviews` | Reviewer, Admin | Review records |
| `PATCH` | `/reviews/{review_id}` | Reviewer, Admin | Submit a review decision |
| `GET` | `/documents/{id}/redactions` | Authorized owner/role | Redaction metadata |
| `GET` | `/redactions/{id}/file` | Authorized owner/role | Download redacted text |
| `GET` | `/documents/{id}/reports` | Authorized owner/role | List audit reports |
| `GET` | `/reports/{id}` | Authorized owner/role | Report metadata and optional payload |

Interactive API documentation is available at `/docs` when the application is running.

## Tests and validation

Run the full suite:

```powershell
python -m pytest -q
```

Current repository audit on August 23, 2026:

- `303 passed, 1 skipped`
- Python compilation passed
- Frontend JavaScript syntax passed
- `pip check` passed
- Alembic fresh-database upgrade and downgrade round-trip passed on SQLite

The skipped test depends on the optional PyMuPDF import in that environment. Test counts will change as coverage grows; use the command output as the source of truth.

## Repository layout

```text
api/                 FastAPI routes and schemas
core/                Configuration, database engine, and security
database/            Models, repositories, and Alembic migrations
docs/                Architecture and runtime documentation
frontend/            Browser dashboard
modules/              Classification, detection, extraction, and upload
orchestration/        Document workflow and redaction
redis_queue/          Producer, consumer, and worker
scripts/              Local and Docker helper scripts
storage/              Local runtime artifacts; sensitive content is ignored by Git
tests/                Unit, integration, and regression tests
```

## Current limitations

- Redaction output is extracted text, not a coordinate-redacted PDF.
- No encryption at rest is implemented for stored documents.
- Human-review records are created, but the PoC does not enforce a separate approve/block release gate.
- OCR line breaks and complex tables remain difficult cases.
- Handwriting and highly structured layouts require additional evaluation.
- No production monitoring or formal compliance certification is included.

## Documentation

- [Technical architecture](docs/doc.md)
- [Run profiles](docs/run_profiles.md)
- [Presentation preparation](docs/preparation.md)
- [Current PoC context](docs/current-poc-context.md)
- [PII/PHI entity reference](docs/pii-phi-entities.md)
