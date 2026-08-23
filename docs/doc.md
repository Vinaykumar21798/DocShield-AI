# DocShield-AI Technical Architecture

## 1. Scope and status

DocShield-AI is a functional proof of concept for PII/PHI detection and redaction in healthcare and enterprise documents. It accepts uploaded files, extracts text, detects sensitive spans, creates review records for low-confidence findings, redacts extracted text, and writes an audit report.

The current release is not production-hardened. In particular:

- redaction targets extracted text rather than the source PDF;
- stored files are not encrypted at rest;
- human review does not act as an approve/block release gate;
- there is no formal compliance certification or production accuracy monitor.

These boundaries are deliberate PoC constraints, not hidden implementation details.

## 2. System context

```text
Browser or API client
        |
        v
FastAPI routes and bearer-session authorization
        |
        +--> PostgreSQL: users, runs, documents, jobs, entities, reviews,
        |                redactions, reports, and audit metadata
        |
        +--> Local storage: original, extracted, redacted, report.json
        |
        +--> Redis queue --> background Worker
                                |
                                v
                      DocumentProcessingWorkflow
```

The API process handles authentication, upload, status, review, and artifact access. The worker consumes document jobs from Redis and executes the workflow. PostgreSQL is the source of record for workflow and audit metadata.

## 3. Main components

| Component | Primary file | Responsibility |
|---|---|---|
| FastAPI application | `app.py` | App startup, router registration, UI mounting |
| Authentication and authorization | `api/routes/auth.py`, `api/dependencies.py`, `core/security.py` | Bearer sessions and role/document access checks |
| Upload service | `modules/upload/service.py` | Run creation, file validation, hashing, persistence, enqueue |
| Storage service | `modules/upload/storage.py` | Run/document directory layout and legacy fallback |
| Worker | `redis_queue/worker.py` | Redis consumption, retry policy, workflow invocation |
| Workflow | `orchestration/workflow.py` | Checkpointed document-processing state machine |
| Classification | `modules/classification/service.py` | Document-type classification |
| Extraction | `modules/extraction/` | Native, OCR, and mixed-PDF extraction |
| Detection orchestration | `modules/detection/service.py` | Detector routing, candidate state, LLM phases, finalization |
| Detector selection | `modules/detection/analyzer/detector_selector.py` | Domain classification and route order |
| Validation | `modules/detection/validators/entity_validator.py` | Structural validation, label trimming, noise rejection |
| Confidence | `modules/detection/confidence_calculator.py` | Confidence calibration and levels |
| Entity mapping | `modules/detection/entity_mapper.py` | Canonical entity and privacy-category mapping |
| Reporting | `database/repositories/report_repository.py` | Report metadata and LLM audit normalization |

## 4. Data and storage model

One upload request creates a `Run`. Each uploaded file creates a `Document` linked to that run. The run uses a human-readable sequence such as `RUN-000001` and aggregates completed and failed file counts.

Primary storage layout:

```text
storage/
  runs/{run_id}/documents/{document_id}/
    original/
    extracted/
    redacted/
    report.json
```

Legacy paths under `storage/uploads/` remain supported when run/document context is unavailable.

Important database records include:

- `Run` and `RunSequence`
- `Document` and `ProcessingJob`
- `OCRResult`
- `Entity` and `ConfidenceScore`
- `Review`
- `Redaction`
- `Report`, including LLM candidate audit metadata
- `User` and `AuthSession`

The latest entity schema includes nullable AI decision/reasoning fields. Deterministic detections do not receive invented AI decisions; those fields are populated only when validation metadata exists.

## 5. Workflow execution

`DocumentProcessingWorkflow` executes checkpointed steps:

1. Load document context.
2. Mark processing status.
3. Classify the document.
4. Select an extraction strategy.
5. Execute native extraction, OCR, or mixed-PDF extraction.
6. Persist OCR/extraction results.
7. Execute the detection pipeline.
8. Persist accepted detection results and confidence records.
9. Create human-review records when final confidence is below `0.80`.
10. Redact extracted text and verify the result.
11. Generate the JSON report.
12. Mark workflow completion.

The worker retries recoverable failures according to `PROCESSING_JOB_MAX_RETRIES`. A deterministic `RedactionVerificationError` is not retried because running the same inputs again would produce the same blocked result.

## 6. Extraction strategy

The extraction layer supports:

- text files;
- DOCX text extraction;
- searchable PDFs through PyMuPDF;
- image and scanned-PDF OCR through PaddleOCR;
- mixed PDFs containing both searchable and scanned pages.

The OCR decision engine considers file type and PDF searchability. Extracted text and structured extraction metadata are stored in `OCRResult`.

The upload validator currently accepts `.pdf`, `.txt`, `.docx`, `.png`, `.jpg`, `.jpeg`, `.tiff`, and `.bmp`, with a hard 20 MB per-file limit in `UploadValidator`. Bulk upload is limited to 100 files.

## 7. Detection orchestration

### 7.1 Domain routes

`DetectorSelector` chooses a route from document type and content cues.

```text
healthcare: Regex -> MedSpaCy -> Presidio -> GLiNER -> LLM
generic:    Regex -> Presidio -> GLiNER -> LLM
financial:  Regex -> Presidio -> GLiNER -> LLM
corporate:  Regex -> Presidio -> GLiNER -> LLM
legal:      Regex -> Presidio -> GLiNER -> LLM
mixed:      Regex -> MedSpaCy -> Presidio -> GLiNER -> LLM
```

Detectors run sequentially. `PipelineState` tracks resolved spans, authoritative locks, pending low-confidence candidates, skipped/executed detectors, and audit telemetry.

### 7.2 Detector responsibilities

- Regex: deterministic identifiers and labeled structured values.
- Presidio: general PII recognition.
- GLiNER: configurable statistical entity recognition.
- MedSpaCy: clinical problems, medications, procedures, and related entities.
- Azure OpenAI or Gemma: residual discovery and candidate validation when LLM use is enabled.

### 7.3 Candidate processing

The finalization order is significant:

1. `EntityValidator`
2. span and offset checks
3. canonical entity mapping
4. taxonomy filtering
5. minimum-confidence filtering
6. confidence calibration
7. deduplication
8. overlap resolution
9. multiline-address and adjacent-person handling
10. deterministic high-risk safety net
11. contextual reclassification

Overlap priority uses:

```text
(is_authoritative, type_rank, detector_priority, confidence, span_length)
```

Changing this order affects precision and recall across detectors and requires regression testing.

## 8. Bounded LLM processing

The active provider is selected with `LLM_PROVIDER`:

- `azure` uses `AzureOpenAIDetector`;
- other/default values use `Gemma4E4BDetector` through Ollama.

`BYPASS_LLM=true` disables LLM execution.

LLM work has two bounded phases:

1. Residual discovery over unresolved contexts.
2. Validation of the combined pending candidate pool with `CONFIRM`, `RECLASSIFY`, or `REJECT` decisions.

Candidate windows use approximately 80 characters of surrounding context and are capped at three contexts. High-risk cues such as account, routing, SSN, policy, MRN, tax, card, and CVV are prioritized before the cap is applied. The full document is not intentionally sent to the LLM as one prompt.

Accepted and rejected decisions are recorded in `llm_candidate_audit` for the report/UI. Raw document content must not be written to application logs.

## 9. Confidence and review

Current thresholds:

| Level | Range | Workflow effect |
|---|---|---|
| High | `>= 0.80` | No review record required |
| Medium | `>= 0.60` and `< 0.80` | Human-review record created |
| Low | `< 0.60` | Normally removed by final minimum-confidence filtering unless validated/recalibrated |

MedSpaCy confidence is capped at `0.95` to avoid treating heuristic clinical output as perfectly certain.

Reviewers can approve, confirm, correct, reject, or skip findings through the review API. In the current PoC, creation of a review record does not pause redaction or enforce an artifact release gate.

## 10. Redaction and verification

Redaction operates on extracted text.

1. Accepted entity values are expanded to other exact, boundary-safe occurrences.
2. Overlapping spans are merged so the entire sensitive region is covered.
3. Spans are replaced from right to left with markers such as `[REDACTED_SSN]`.
4. A bounded fixed-point safety pass reruns deterministic high-risk detection on the partially redacted text.
5. Verification checks span/value integrity, detected values remaining in output, and deterministic residual PII.

If verification reports an issue, the workflow raises `RedactionVerificationError` and does not produce a successful release result.

This is defense in depth, not proof of perfect recall. There is no automated coordinate-based verification against the original PDF.

## 11. API security model

Authentication uses bearer session tokens. Passwords and tokens are stored as hashes. Roles are:

- `USER`: upload and access owned documents/artifacts;
- `REVIEWER`: review document entities and submit decisions;
- `ADMIN`: reviewer access plus user and aggregate administration.

Document routes apply ownership/access checks. Artifact resolution confines downloads to the configured storage root and sends `no-store`/`nosniff` response headers.

Secrets belong in process environment variables or ignored environment files. `.env` and `.env.local` must never be committed.

## 12. Configuration profiles

Local scripts set `DOCSHIELD_ENV_FILE=.env.local`. Configuration loading preserves process-environment precedence. With the default profile, `.env.local` is loaded before `.env`; a custom `DOCSHIELD_ENV_FILE` does not also load `.env.local`.

Important variables include:

- `DATABASE_URL`, `REDIS_URL`
- `PROCESSING_JOB_MAX_RETRIES`
- `LLM_PROVIDER`, `BYPASS_LLM`
- `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- `DETECTION_HIGH_CONFIDENCE_THRESHOLD`
- `DETECTION_MEDIUM_CONFIDENCE_THRESHOLD`
- `DETECTION_STOPPING_CANDIDATE_THRESHOLD`
- `DETECTION_MIN_CANDIDATE_CHARS`
- `STORAGE_DIR`, `UPLOAD_DIR`

See [run_profiles.md](run_profiles.md) for profile-specific commands.

## 13. Migrations

Alembic migrations live under `database/migrations/versions/`. Historical document-table alterations use batch mode so the complete chain works on PostgreSQL and SQLite.

Apply migrations:

```powershell
.\scripts\local-migrate.ps1
```

The August 23, 2026 audit verified:

- a clean upgrade from base to `b264116667a1`;
- downgrade from head back to base;
- isolated upgrade/downgrade of the AI entity fields.

## 14. Testing

Run everything:

```powershell
python -m pytest -q
```

Important suites include:

- `tests/test_document_workflow.py`
- `tests/test_detection.py`
- `tests/test_detection_quality_regressions.py`
- `tests/test_api_e2e.py`
- `tests/test_auth_rbac.py`
- `tests/test_worker_retry.py`

Current audited result: `303 passed, 1 skipped`. Test counts are not a product accuracy metric. Use `metrics.py` and representative labeled data to measure precision and recall.

## 15. Known accuracy risks

- OCR can split phone numbers and addresses across lines.
- Short tokens can be ambiguous without context.
- Complex tables lack complete layout-aware interpretation.
- Handwritten notes are not adequately evaluated.
- Detector confidence is not equivalent to calibrated production probability.
- Regression fixtures are mostly synthetic and cannot establish production compliance performance.

## 16. Safe contribution checklist

Before committing:

```powershell
python -m pytest -q
python -m compileall -q api core database modules orchestration redis_queue tests
git diff --check
git status --short
```

Also verify that:

- the new Alembic revision is included;
- `.env`, `.env.local`, storage artifacts, and logs are not tracked;
- no raw PII/PHI, tokens, credentials, or connection strings appear in changes;
- detection changes include regression coverage;
- API contracts and storage legacy fallback remain intact.
