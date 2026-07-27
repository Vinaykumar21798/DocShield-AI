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
- Layout-preserving OCR output for scanned PDFs and images.
- Optional structured OCR output persisted with OCR results.
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
Extract Text + Structured Layout
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
- Preserve scanned document layout using PP-Structure/Layout when available.
- Reconstruct page, block, row, line, bounding box, and table-like structure from OCR coordinates when PP-Structure is unavailable.
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

The current production path is still PaddleOCR. GLM OCR and Baidu Unlimited-OCR are candidate engines for future routing when a document needs stronger layout, table, or long-document understanding.

| Feature | PaddleOCR (Current) | GLM OCR via Ollama (Candidate) | Baidu Unlimited-OCR via Hugging Face (Candidate) |
|---------|----------------------|---------------------------------|--------------------------------------------------|
| Type | OCR toolkit | Multimodal OCR model | Image-text-to-text vision-language OCR model |
| Primary fit | Fast OCR for images and scanned PDFs | Local complex document OCR, tables, figures, forms | Long-horizon document parsing, complex tables, multi-page documents |
| Deployment | In-process Python dependency | Local Ollama service using `glm-ocr` | Transformers, vLLM, or SGLang self-hosting |
| Offline support | Yes | Yes, after model pull | Yes, if model is self-hosted |
| Model size | PaddleOCR model dependent | 0.9B parameters; Ollama tags include `latest`, `q8_0`, and `bf16` | 3B parameters, BF16 safetensors |
| Context / long document handling | Basic text extraction; structure must be rebuilt downstream | 128K context window in Ollama model metadata | Supports single-image and multi-page/PDF-style parsing workflows |
| Printed text | Excellent on clean scans | Excellent | Excellent |
| Scanned documents | Excellent on clean scans | Excellent | Excellent |
| Table extraction | Text plus optional PP-Structure or bounding-box table-like reconstruction | Strong candidate for table recognition | Strong candidate for table and long-layout parsing |
| Form/layout understanding | Coordinates are post-processed; PP-Structure used when available | Advanced document understanding | Advanced long-horizon layout parsing |
| Integration effort | Already implemented | Medium: add Ollama client/provider and prompt templates | Medium/high: add model-serving path and GPU deployment plan |
| Main risk | Plain-text output loses visual table structure | Requires local model runtime capacity and prompt control | Requires GPU/server capacity, `trust_remote_code` review, and model-serving operations |

Current choice:

The implementation uses **PaddleOCR** because it:

- Is already integrated with the FastAPI workflow.
- Supports offline processing.
- Provides fast and accurate OCR for clean scanned PDFs and images.
- Has low operational complexity for the PoC.

Future provider candidates:

### GLM OCR

Source: <https://ollama.com/library/glm-ocr>

GLM OCR is a local multimodal OCR option available through Ollama. It is designed for complex document understanding and supports text/image inputs. The Ollama library page lists `glm-ocr:latest`, `glm-ocr:q8_0`, and `glm-ocr:bf16` variants with a 128K context window.

Recommended PoC usage pattern:

```powershell
ollama pull glm-ocr
ollama run glm-ocr "Text Recognition: ./image.png"
ollama run glm-ocr "Table Recognition: ./image.png"
ollama run glm-ocr "Figure Recognition: ./image.png"
```

Integration direction:

- Add a new extraction provider named `GLM_OCR`.
- Run Ollama locally or on an internal OCR node.
- Use text-recognition prompts for normal pages.
- Use table-recognition prompts for invoices, statements, tabular medical reports, and claim forms.
- Store the raw OCR response plus a normalized JSON/table representation when available.

Best fit:

- Complex tables.
- Forms where labels and values are visually separated.
- Documents where PaddleOCR text is correct but row/column structure is weak.
- Local/private deployment where cloud OCR is not allowed.

### Baidu Unlimited-OCR

Source: <https://huggingface.co/baidu/Unlimited-OCR>

Baidu Unlimited-OCR is a Hugging Face image-text-to-text model released under the MIT license. The model card lists it as a 3B-parameter BF16 model and provides Transformers, vLLM, and SGLang inference paths. It supports single-image parsing and multi-page parsing where PDFs are first converted to page images.

Recommended PoC usage pattern:

```python
from transformers import AutoModel, AutoTokenizer

model_name = "baidu/Unlimited-OCR"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModel.from_pretrained(
    model_name,
    trust_remote_code=True,
    use_safetensors=True,
    device_map="auto",
)

model.infer(
    tokenizer,
    prompt="<image>document parsing.",
    image_file="invoice.jpg",
    output_path="ocr_output",
    base_size=1024,
    image_size=640,
    crop_mode=True,
    max_length=32768,
    save_results=True,
)
```

Integration direction:

- Add a new extraction provider named `BAIDU_UNLIMITED_OCR`.
- Prefer a model-serving boundary such as vLLM or SGLang instead of loading the model inside the API process.
- Convert PDFs to images at 300 DPI before multi-page parsing.
- Review any remote model code before enabling `trust_remote_code=True` in a controlled environment.
- Keep PaddleOCR as the default path and route only complex/failed documents to this engine until benchmarked.

Best fit:

- Long invoices or statements.
- Multi-page documents.
- Complex tables that need row/column reconstruction.
- Documents where one-shot page-level parsing is more valuable than simple line OCR.

Recommended future routing:

| Document Type / Condition | Recommended Engine |
|---------------------------|--------------------|
| Searchable PDF | Native PDF Extraction |
| Clean image or scanned PDF | PaddleOCR |
| PaddleOCR text is good but table structure is weak | GLM OCR or Baidu Unlimited-OCR |
| Complex forms with separated labels and values | GLM OCR |
| Long multi-page invoices/statements | Baidu Unlimited-OCR |
| Handwritten or low-quality images | Benchmark GLM OCR and Baidu Unlimited-OCR before production use |

## 8.2 Current PaddleOCR Issues Observed

Sample file:

```text
batch1-0001.jpg
```

Visible document:

- Invoice no: `51109338`
- Date of issue: `04/13/2013`
- Seller: `Andrews, Kirby and Valdez`
- Client: `Becker Ltd`
- Seller Tax Id: `945-82-2137`
- Client Tax Id: `942-80-0517`
- IBAN: `GB75MCRL06841367619257`
- Summary total gross worth: `$ 6 204,19`

Observed PaddleOCR quality:

- Core text recognition is strong for this sample. The invoice number, date, seller/client names, addresses, tax IDs, IBAN, line-item descriptions, quantities, VAT values, and totals are present.
- Estimated extraction quality is approximately 95-98% for plain text because the image is high resolution, straight, high contrast, and printed in standard fonts.
- The main gap is not character recognition. The main gap is layout preservation and table structure.

Known document-shape issues now partially addressed by layout-preserving OCR, with remaining normalization left to downstream/domain post-processing:

1. Label/value line breaks.
   Example: `Date of issue:` appears on one line and `04/13/2013` appears on the next line. This should be normalized to `Date of issue: 04/13/2013`.

2. Two-column party layout flattening.
   Seller and client blocks are visually side by side, but plain OCR text serializes them into a single stream. Downstream parsers should preserve separate `seller` and `client` blocks.

3. Table row reconstruction.
   PaddleOCR extracts item text and numbers, but the visual table becomes plain text. Multi-line product descriptions and numeric columns need to be grouped into structured rows.

4. Split table headers.
   Headers such as `Gross worth` can appear as `Gross` and `worth` on separate lines. Header normalization should merge these before table parsing.

5. Locale-specific numeric formats.
   Values use comma decimals and spaces as thousands separators, for example `1 394,67` and `6 204,19`. Post-processing must preserve the original value and optionally normalize to machine-readable decimals.

6. Product punctuation and spacing.
   Product descriptions such as `TESTED!!READ BELOW!!` may need whitespace cleanup, but should not be treated as an OCR failure.

Recommended downstream PaddleOCR post-processing remains:

- Normalize whitespace and repeated blank lines.
- Join label/value pairs when a label line is followed by a value line.
- Use `structured_output` OCR bounding boxes, when available, to separate seller/client regions and rebuild table rows.
- Convert invoice item rows into structured fields: `no`, `description`, `qty`, `um`, `net_price`, `net_worth`, `vat_rate`, and `gross_worth`.
- Preserve original extracted text for audit/debugging and store normalized structured output separately.
- Keep PII/financial identifiers such as `Tax Id` and `IBAN` unchanged so Dev2 can detect them reliably.

## 8.3 Layout-Preserving PaddleOCR Output

PaddleOCR extraction now produces two outputs for scanned PDFs and images:

- `extracted_text`: plain text for the existing downstream workflow.
- `structured_output`: optional layout metadata for consumers that need page, block, line, table, or coordinate context.

The `TextExtractionResult` dataclass remains backward compatible because `structured_output` is optional and all existing required fields are unchanged. The workflow still evaluates OCR confidence after extraction using the existing evaluator and stores the same plain extracted text file under `storage/extracted_text`.

Storage/API behavior:

- `ocr_results.structured_output` stores the structured OCR payload as nullable JSON.
- `GET /documents/{document_id}/text` returns `structured_output` when it exists.
- Existing consumers can continue reading `extracted_text`, `confidence_score`, `page_count`, and processing status without changes.

PP-Structure path:

1. The PaddleOCR extractor runs the normal OCR call first so raw OCR confidence scoring remains unchanged.
2. When `PADDLEOCR_LAYOUT_ANALYSIS_ENABLED=True`, it lazily attempts to construct `PPStructure` or `PPStructureV3` from the installed `paddleocr` package.
3. If PP-Structure returns layout blocks, those blocks are normalized into `pages[].blocks[]` with `block_type`, `bbox`, `text`, `lines`, and `source=pp_structure`.
4. Table HTML returned by PP-Structure is parsed into `block.table.rows` and also rendered to plain text using tab-separated cells.

Bounding-box fallback path:

1. OCR lines are collected from PaddleOCR legacy outputs and newer dict-style outputs such as `rec_texts`, `rec_scores`, `rec_boxes`, and `rec_polys`.
2. Bounding boxes are normalized to `[left, top, right, bottom]`. Polygon boxes are reduced to their enclosing rectangle.
3. Lines are grouped into visual rows using vertical center proximity, then sorted left-to-right inside each row.
4. Large horizontal gaps are rendered as tabs so multi-column regions and tables retain visible separation in plain text.
5. Larger vertical gaps create separate text blocks/paragraphs.
6. Repeated rows with three or more fragments are marked as table-like blocks.
7. Multi-page scanned PDFs are merged with a form-feed page break (`\f`) between page texts.

Current limitations:

- PP-Structure availability depends on the installed PaddleOCR package and model support.
- Bounding-box reconstruction is heuristic and cannot perfectly recover all reading order decisions.
- Complex nested tables, merged cells, rotated text, overlapping columns, handwriting, and poor scans may still lose structure.
- Fallback table detection preserves rows and visible column separation but does not infer semantic schemas.
- Native PDF, TXT, and DOCX extraction paths continue to return plain text only unless separate layout support is added later.

Dependencies and configuration:

- No new dependency was added. The feature uses existing `paddleocr`, `paddlepaddle`, `Pillow`, and `pymupdf` dependencies.
- Optional PP-Structure support is used only when `PPStructure` or `PPStructureV3` is available in the installed PaddleOCR package.
- Set `PADDLEOCR_LAYOUT_ANALYSIS_ENABLED=False` to skip PP-Structure attempts and rely on OCR bounding-box reconstruction.

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
- `structured_output`
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
- `structured_output`



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
- `structured_output`
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

