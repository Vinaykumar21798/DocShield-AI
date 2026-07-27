# PII/PHI Document Intelligence PoC

A FastAPI-based Document Intelligence Proof of Concept (PoC) for document ingestion, OCR, document classification, and extracted text generation. The extracted text is exposed through APIs for downstream PII/PHI detection and compliance workflows.

## Features

- Document upload (Single & Bulk)
- File validation
- Local file storage
- PostgreSQL metadata management
- Redis-based asynchronous processing
- Rule-based document classification
- OCR Decision Engine
- Native PDF text extraction (PyMuPDF)
- PaddleOCR for scanned PDFs and images
- Native text extraction for `.txt` and `.docx`
- OCR confidence evaluation
- Extracted text storage
- REST APIs for document status and extracted text
- Retry mechanism for failed jobs

---

## Technology Stack

| Layer | Technology |
|--------|------------|
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Queue | Redis |
| OCR | PaddleOCR |
| PDF Parser | PyMuPDF |
| Validation | Pydantic |
| Storage | Local File System |
| API Docs | Swagger / OpenAPI |

---

## Project Structure

```text
PII-PHI-Document-Intelligence-PoC/
├── api/
├── core/
├── database/
├── modules/
├── orchestration/
├── redis_queue/
├── shared/
├── storage/
├── tests/
├── app.py
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── README.md
└── doc.md
```

---

## Processing Workflow

```text
Upload Document
        │
        ▼
File Validation
        │
        ▼
Store File
        │
        ▼
Create Database Records
        │
        ▼
Push Job to Redis Queue
        │
        ▼
Background Worker
        │
        ▼
Document Classification
        │
        ▼
OCR Decision Engine
        │
        ├── Native PDF
        ├── PaddleOCR
        └── Native Text
        │
        ▼
OCR Confidence Evaluation
        │
        ▼
Store OCR Results
        │
        ▼
Extracted Text API
```

---

## Supported File Types

- PDF
- PNG
- JPG
- JPEG
- TIFF
- BMP
- DOCX
- TXT

---

## Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd PII-PHI-Document-Intelligence-PoC
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

Activate:

Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Docker Services

```bash
docker compose up -d
```

### 5. Run Database Migrations

```bash
python -m alembic upgrade head
```

### 6. Start FastAPI

```bash
python -m uvicorn app:app --reload
```

### 7. Start Redis Worker

```bash
python redis_queue/worker.py
```

---

## API Documentation

Swagger UI

```
http://localhost:8000/docs
```

---

## Main APIs

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health/` | Health Check |
| POST | `/upload/` | Upload Single Document |
| POST | `/upload/bulk` | Upload Multiple Documents |
| GET | `/documents/{document_id}/status` | Document Status |
| GET | `/documents/{document_id}/text` | Extracted Text |

---

## OCR Engines

| Engine | Purpose |
|---------|---------|
| Native PDF | Searchable PDFs |
| PaddleOCR | Images & Scanned PDFs |
| Native Text | TXT / DOCX |

---

## Future Enhancements

- GLM OCR integration
- Baidu OCR integration
- Cloud storage support (S3/MinIO)
- Dev2 PII/PHI detection
- Human review workflow
- Audit logging
- Production monitoring

---

## Documentation

Detailed project documentation is available in:

```
doc.md
```

---

## License

This project is developed as a Proof of Concept (PoC) for document intelligence and OCR workflow evaluation.