# DocShield-AI

**DocShield-AI** is an enterprise-grade **PII/PHI Document Intelligence & Automated Redaction Engine** built with FastAPI, PostgreSQL, Redis, and a 5-layer hybrid detection pipeline. It ingests healthcare records, medical summaries, EOBs, and financial documents, extracts text (via native parsing or OCR), detects sensitive entities, calibrates confidence, routes low-confidence entities to human review, and produces redacted output text files alongside JSON audit reports.

---

## Key Capabilities

* **Multi-Format Document Ingestion**: Supports `.pdf` (native vector & scanned), `.txt`, `.docx`, and images (`.png`, `.jpg`).
* **5-Layer Hybrid Detection Pipeline**:
  1. **Deterministic Regex Engine**: Mathematical precision for SSNs, Phone Numbers, ICD-10 Codes, CPT Codes, Dates, Zip Codes, and Insurance IDs.
  2. **Clinical NLP Engine (MedSpaCy)**: Extraction of diseases, symptoms, lab tests (`Lipid Panel`, `HbA1c`), medications, and procedures.
  3. **Statistical NER Engine (GLiNER & Presidio)**: Extraction of patient names, doctor names, facility locations, and healthcare organizations.
  4. **Semantic LLM Layer (`gpt-5.4-mini` or `gemma4:e4b`)**: Contextual residual entity discovery and candidate validation.
  5. **Central Quality Gate (`EntityValidator`)**: Form prefix label trimming (`"SSN: 123-45-6789"` $\rightarrow$ `"123-45-6789"`), mandatory phone digit validation ($\ge 7$ digits), and audit verb/sentence filtering.
* **Confidence-Calibrated Human Review**: Entities with confidence $< 80\%$ (or flagged by risk heuristics) enter the Human Review queue for approval/rejection.
* **Occurrence Expansion & Safety Verifier**: Expands confirmed entity occurrences across multi-page text and blocks file release if any un-redacted PII remains.
* **Dual Runtime Profiles**: Supports both Local Python (`.env.local`, API `:8000`) and Docker Compose (`:8001`).

---

## System Architecture & Pipeline Flow

```text
Upload → Classification → OCR/Extraction → Dynamic Detection Orchestration
  ├── 1. Regex (Deterministic)
  ├── 2. MedSpaCy (Clinical)
  ├── 3. Presidio & GLiNER (Statistical NER)
  └── 4. Azure OpenAI (gpt-5.4-mini) / Ollama (gemma4:e4b) (Semantic Residual)
→ Quality Validation & Prefix Trimming (EntityValidator)
→ Span Deduplication & Overlap Resolution
→ Confidence Scoring & Calibration (ConfidenceCalculator)
→ Human Review Trigger (Review Repository)
→ Occurrence Expansion & Text Redaction
→ Post-Redaction Verification Safety Check
→ Output: Redacted .txt + JSON Audit Report
```

---

## Runtime Separation

Docker and local Python environments are deliberately separated to prevent port collisions and credential leaks.

| Profile | API URL | Web UI | PostgreSQL | Redis | Configuration Source |
|---|---|---|---|---|---|
| **Local Python** | `http://localhost:8000` | `http://localhost:8000/ui/` | `127.0.0.1:5432` | `127.0.0.1:6379` | `.env.local` |
| **Docker** | `http://localhost:8001` | `http://localhost:8001/ui/` | `127.0.0.1:5433` | `127.0.0.1:6380` | `docker-compose.yml` |

---

## Quick Start (Local Python Profile)

### 1. Prerequisites
- **Python 3.10**
- **PowerShell** (Windows)
- **PostgreSQL 15+** (running on port `5432`)
- **Redis 7+** (running on port `6379`)
- **Ollama** (if using local LLM provider):
  ```powershell
  ollama pull gemma4:e4b
  ```

### 2. Initialization & Setup
Run the local environment initialization script:

```powershell
cd E:\Office\DocShield-AI
.\scripts\local-init.ps1
```

Edit `.env.local` to configure your database and LLM provider:

```ini
# Database & Redis Settings
DATABASE_URL=postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/pii_phi_document_intelligence_poc
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# LLM Provider Configuration (azure -> gpt-5.4-mini | gemma -> gemma4:e4b)
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.4-mini
```

### 3. Run Database Migrations
```powershell
.\scripts\local-migrate.ps1
```

### 4. Start the Application

**Terminal 1 (API Server):**
```powershell
.\scripts\local-api.ps1
```

**Terminal 2 (Background Worker):**
```powershell
.\scripts\local-worker.ps1
```

Open the web interface: **`http://localhost:8000/ui/`**

---

## Docker Quick Start

Start the complete containerized stack:

```powershell
.\scripts\docker-up.ps1
```

Access the Docker UI: **`http://localhost:8001/ui/`**

Stop Docker containers:
```powershell
.\scripts\docker-down.ps1
```

---

## Core API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health/` | Health check & system status |
| `POST` | `/upload/` | Upload single document for processing |
| `POST` | `/upload/bulk` | Upload bulk zip/folder of documents (max 100) |
| `GET` | `/documents/{id}/status` | Check document & job execution status |
| `GET` | `/documents/{id}/text` | Retrieve extracted raw/OCR text |
| `GET` | `/documents/{id}/reviews` | Fetch pending/completed human review items |
| `PATCH` | `/reviews/{id}` | Approve or reject an entity review finding |
| `GET` | `/documents/{id}/redactions` | List entity redaction records |
| `GET` | `/redactions/{id}/file` | Download redacted output file |
| `GET` | `/documents/{id}/reports` | Retrieve JSON audit report |

---

## Repository Structure

```text
DocShield-AI/
├── api/                  FastAPI endpoints, Pydantic schemas, and middleware
├── core/                 App config, DB session setup, and security utilities
├── database/             SQLAlchemy models, repository patterns, Alembic migrations
├── docs/                 Technical Master Book (docs/doc.md) and developer runbooks
├── frontend/             Vanilla JS/HTML/CSS dashboard served at /ui/
├── modules/
│   ├── classification/   Document domain classifier (healthcare vs generic)
│   ├── detection/        Hybrid NER pipeline, LLM detectors, and EntityValidator
│   ├── extraction/       PaddleOCR and PyMuPDF PDF extractors
│   └── upload/           File validation, hashing, and storage layout
├── orchestration/        Workflow state machine (DocumentProcessingWorkflow)
├── redis_queue/          Async background worker and task queue
├── scripts/              Local & Docker lifecycle management scripts
├── storage/              Local uploads, extracted text, redacted files, and logs
└── tests/                Pytest unit, integration, and regression suites
```

---

## Automated Testing & Reset Commands

### Run Automated Pytest Suite
Run the 30 unit, workflow, and quality regression tests:

```powershell
python -m pytest tests/test_document_workflow.py tests/test_detection_quality_regressions.py -v
```

### Full Database & Storage Truncation (Fresh Start)
Reset database tables and clear local storage artifacts:

```powershell
python -c "import os, shutil, glob, sys; sys.path.insert(0, r'E:\Office\DocShield-AI'); import core.config; from database.session import engine; from sqlalchemy import text; conn = engine.connect(); tx = conn.begin(); conn.execute(text('TRUNCATE TABLE confidence_scores, reviews, reports, redactions, entities, ocr_results, processing_jobs, documents, runs RESTART IDENTITY CASCADE;')); tx.commit(); conn.close(); print('DB TRUNCATED'); [shutil.rmtree(os.path.join('storage/runs', d), ignore_errors=True) for d in os.listdir('storage/runs') if os.path.isdir(os.path.join('storage/runs', d))]; [os.remove(os.path.join('storage/uploads', f)) for f in os.listdir('storage/uploads') if os.path.isfile(os.path.join('storage/uploads', f)) and not f.endswith('.gitkeep')]; [open(log_f, 'w').close() for log_f in glob.glob('storage/logs/*.log')]; print('STORAGE CLEARED')"
```

---

## Documentation

For full end-to-end technical details, pipeline specifications, and challenge resolutions, see the **[Master Book Documentation (`docs/doc.md`)](file:///E:/Office/DocShield-AI/docs/doc.md)**.
