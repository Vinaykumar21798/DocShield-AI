# DocShield-AI

DocShield-AI is a FastAPI-based Document Intelligence Proof of Concept (PoC) for document ingestion, OCR, document classification, and extracted text generation. The extracted text is exposed through APIs for downstream PII/PHI detection and compliance workflows.

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
- Layout-preserving OCR output for scanned PDFs and images
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
DocShield-AI/
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
git clone https://github.com/Vinaykumar21798/DocShield-AI.git
cd DocShield-AI
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
| GET | `/documents/{document_id}/text` | Extracted Text with optional structured OCR layout |

---

## OCR Engines

| Engine | Purpose |
|---------|---------|
| Native PDF | Searchable PDFs |
| PaddleOCR | Images & Scanned PDFs |
| Native Text | TXT / DOCX |

---

## Layout-Preserving OCR

PaddleOCR extraction now returns both plain extracted text and optional structured layout output. The plain `extracted_text` field remains the downstream processing input, while `structured_output` contains page, block, line, bounding box, and table metadata when available.

When `PADDLEOCR_LAYOUT_ANALYSIS_ENABLED=True`, the PaddleOCR extractor attempts PP-Structure/Layout (`PPStructure` or `PPStructureV3`) lazily during scanned PDF/image OCR. If PP-Structure is unavailable or fails for a page, extraction falls back to OCR bounding box reconstruction.

Fallback reconstruction works by normalizing OCR boxes, grouping lines by vertical position, sorting each row left-to-right, inserting tabs for large horizontal gaps, inserting blank lines for larger vertical gaps, and marking repeated multi-fragment rows as table-like blocks. Multi-page scanned PDFs use a form-feed page break (`\f`) between page texts.

Structured output is stored in `ocr_results.structured_output` and returned by `GET /documents/{document_id}/text`. Existing fields such as `extracted_text`, `extracted_text_path`, `page_count`, `confidence_score`, and `processing_time` are unchanged. OCR confidence still uses the existing line-score average and confidence evaluator.

Current limitations:

- Layout reconstruction is heuristic when PP-Structure is not available.
- Complex nested tables, merged cells, rotated text, handwritten text, and heavily skewed scans may still need provider-specific post-processing.
- Multi-column reading order is inferred from coordinates and may be imperfect when columns overlap vertically or have inconsistent gutters.
- Table output from fallback OCR preserves visual rows with tabs but does not infer semantic column names beyond recognized text.

Dependencies and configuration:

- No new package is required beyond the existing `paddleocr`, `paddlepaddle`, `Pillow`, and `pymupdf` dependencies.
- PP-Structure support depends on the installed PaddleOCR package exposing `PPStructure` or `PPStructureV3`.
- Set `PADDLEOCR_LAYOUT_ANALYSIS_ENABLED=False` to skip PP-Structure attempts and use bounding-box reconstruction only.

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
