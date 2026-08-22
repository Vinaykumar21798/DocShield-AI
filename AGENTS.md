# AGENTS.md — DocShield-AI

This file gives AI coding agents (and human contributors) the context needed to work safely and effectively in this repository. Read this before making changes.

## 1. What This Project Is

DocShield-AI is a **PII/PHI redaction system** for healthcare and enterprise documents. It is currently a **Functional PoC** (not production-hardened) that takes uploaded documents, extracts text (via native parsing or OCR), detects sensitive entities using a hybrid rules + ML + LLM pipeline, scores confidence, optionally routes low-confidence entities to human review, and produces a redacted text file plus a JSON audit report.

**Core flow:**
`Upload → Classification → OCR/Extraction → Dynamic Detection Orchestration → Entity Merging/Validation → Confidence Scoring → Human Review Trigger → Text Redaction → Audit Report Generation`

Because this system handles real PII/PHI, **treat correctness and data-handling discipline as first-class concerns**, even in PoC code.

## 2. Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **OCR**: PaddleOCR, PyMuPDF (`fitz`)
- **Detection**: Regex, Microsoft Presidio, GLiNER, MedSpaCy, Gemma4:e4b (via Ollama)
- **Infra**: Redis (queue), PostgreSQL (database), local filesystem (storage)
- **Frontend**: Vanilla JS/HTML/CSS dashboard

## 3. Repository Structure

```
api/                 # FastAPI routes and Pydantic schemas
core/                # Global configuration and DB session management
database/            # SQLAlchemy models and Repository pattern implementations
docs/                # Documentation and run profiles
frontend/            # Vanilla JS/HTML/CSS dashboard
modules/
  classification/    # Document type classification (rules-based)
  detection/         # NER pipeline (detectors, validators, orchestrator)
  extraction/        # OCR and text extraction engines
  upload/            # File ingestion and validation
orchestration/       # Workflow engine (state machine/execution plan)
redis_queue/         # Async background worker implementation
scripts/             # Local environment and Docker utility scripts
storage/             # Local filesystem for uploads, extracted text, redacted files
tests/               # Unit, integration, and regression tests
```

Follow this structure for new code. Don't introduce a parallel structure (e.g. a new top-level module) unless the task explicitly calls for it — extend an existing module first.

## 4. System Architecture (high level)

```
Client → API Layer (FastAPI) → Upload Module → Redis Queue (async)
   → Orchestration Workflow (DocumentProcessingWorkflow)
       → Classification (DocumentClassificationService)
       → Extraction (OCRDecisionEngine → PaddleOCR / Native)
       → Detection Pipeline (DetectionService)
           - Regex (deterministic)
           - Presidio, GLiNER (statistical)
           - MedSpaCy (clinical)
           - Gemma4:e4b (semantic, bounded-context)
       → Entity Post-Processing (EntityValidator → Deduplicator → Overlap Resolver)
       → Confidence/Risk Scoring (ConfidenceCalculator)
       → Human Review Trigger (Review Repository)
       → Redaction Engine (text replacement)
       → Output: redacted .txt + JSON audit report
```

## 5. Critical Files & Classes

| Component | File | Class/Function | Responsibility |
|---|---|---|---|
| Orchestrator | `orchestration/workflow.py` | `DocumentProcessingWorkflow` | Main state machine |
| Detection | `modules/detection/service.py` | `DetectionService` | Pipeline orchestration |
| Router | `modules/detection/analyzer/detector_selector.py` | `DetectorSelector` | Domain-based detector routing |
| LLM Detector | `modules/detection/detectors/gemma_detector.py` | `Gemma4E4BDetector` | Semantic extraction |
| OCR Engine | `modules/extraction/ocr.py` | `OCRDecisionEngine` | Engine selection (native/PaddleOCR/mixed) |
| Validation | `modules/detection/validators/entity_validator.py` | `EntityValidator` | Filtering & reclassification |
| Classification | `modules/classification/service.py` | `DocumentClassificationService` | Document type identification |
| Entity Mapping | `modules/detection/entity_mapper.py` | `PrivacyMapper` | PII vs PHI categorization |
| Run Tracking | `database/repositories/run_repository.py` | `RunRepository` | Run creation, sequence IDs, status aggregation |
| Run Model | `database/models/run.py` | `Run`, `RunSequence` | Bulk-upload run aggregation & ID counter |
| Redaction | `orchestration/workflow.py` (`_apply_redactions`, ~line 909) | — | Text span replacement |
| Storage | `modules/upload/storage.py` | — | UUID-tree file layout |

**Before touching any of these files, read them in full and trace their callers/callees — don't assume behavior from this table alone; it's a summary, not a spec.**

## 6. Data Model Essentials

- **Run**: One upload request (single or bulk, max 100 files) creates one `Run` (`RUN-000001` style ID via `RunSequence` with `with_for_update()` for atomicity). Tracks `total_files` / `completed_files` / `failed_files`; auto-transitions to `COMPLETED`/`FAILED` when counters match.
- **Document**: Belongs to a `Run` via `run_id` FK (nullable, indexed — legacy documents may have no run).
- **Storage layout**: `{STORAGE_DIR}/runs/{run_id}/documents/{document_id}/{original,extracted,redacted}/` + `report.json`. Legacy fallback: `storage/uploads/` (flat UUID filenames) when `run_id`/`document_id` are absent — **don't break this fallback** without explicit approval.
- **Other models**: `Document`, `ProcessingJob`, `OCRResult`, `Entity`, `ConfidenceScore`, `Redaction`, `Report`, `Review`.

## 7. Detection Pipeline Conventions

- Detectors run **sequentially** per a domain-based route selected by `DetectorSelector`:
  - `healthcare` → regex → medspacy → presidio → gliner → gemma4e4b
  - `generic` → regex → presidio → gliner → gemma4e4b
- Confidence thresholds: **HIGH ≥ 0.80**, **MEDIUM ≥ 0.60**, **LOW < 0.60**. Human review triggers when `confidence < 0.80`.
- Entity post-processing order matters: `EntityValidator` → `Deduplicator` → overlap resolution (`DetectionService._resolve_overlapping_spans`, priority key: `is_authoritative, type_rank, detector_priority, confidence, length`).
- If you add or modify a detector, confidence calibration, or the overlap-resolution priority key, **explain the change and its expected effect on precision/recall before implementing** — this pipeline has known fragility (see §9).

## 8. Known Constraints — Do Not "Fix" Silently

These are deliberate PoC limitations, not bugs to casually patch:

- **Redaction targets extracted `.txt`, not the original PDF.** PDF-native (coordinate-based) redaction is a known gap and a planned next step, not an oversight — don't quietly change the redaction target without discussion.
- **No automated post-redaction verification.** The system relies on pipeline confidence; there's no APPROVE/BLOCK release gate.
- **No authentication/authorization.** The API is currently open. Don't add auth as a side effect of an unrelated task — treat it as its own explicit change with approval.
- **No encryption at rest** for stored documents.
- **MedSpaCy over-confidence**: it returns ~1.0 for most entities and is deliberately capped at 0.95 in `ConfidenceCalculator` — don't remove the cap without justification.
- **Gemma context is bounded** (~80 chars around unresolved/low-confidence candidates, max 3 contexts per page) for latency reasons — expanding context size has real performance implications.

## 9. Known Accuracy Issues

- **OCR line breaks**: entities split across lines (e.g. phone numbers) are handled via fragile special-case regex.
- **Label collision**: risk of masking literal labels (e.g. `"Name:"`) as entities — mitigated but not eliminated by `EntityValidator`.
- **Context ambiguity**: short tokens like "PPO" or "Level 4" can be misflagged as organizations without surrounding context.
- **Untested territory**: handwritten notes, highly structured tables without layout analysis.

When working on detection code, check `tests/test_detection_quality_regressions.py` for known hard cases (e.g. EOBs) before and after your change.

## 10. Testing

- **Unit tests**: broad per-detector coverage (e.g. `test_regex_detector.py`).
- **Integration tests**: `test_api_e2e.py`, `test_document_workflow.py`.
- **Regression tests**: `test_detection_quality_regressions.py` — guards against reintroducing known detection failures.
- **Evaluation**: `metrics.py` computes precision/recall on test sets (no real-time production monitoring exists).

**Run the relevant test suite after any change** to detection, extraction, classification, redaction, or run/document tracking code. For detection changes specifically, run the regression suite even if it seems unrelated — overlap resolution and confidence scoring changes have cross-detector effects.

## 11. Configuration & Environment

Environment variables in use: `OLLAMA_HOST`, `BYPASS_LLM`, `DATABASE_URL`, `REDIS_HOST`, `REDIS_PORT`, `DETECTION_HIGH_CONFIDENCE_THRESHOLD`, `DETECTION_MIN_CANDIDATE_CHARS`.

**Do not modify configuration, environment variables, or deployment settings unless the task explicitly requires it.** If a task seems to need a config change, propose it and explain why before implementing.

## 12. Security & Privacy Rules (non-negotiable)

- **Never** expose secrets, API keys, credentials, or connection strings in code, logs, commits, or generated output.
- **Never** log or print raw PII/PHI content, including in debug statements. This system's entire purpose is redacting sensitive data — leaking it via a stray `print()` or log line is a critical failure.
- Be extra cautious with test fixtures containing sample PII/PHI — don't add new real-looking sensitive data to the repo; use clearly synthetic examples.
- Don't weaken the PII/PHI entity taxonomy, confidence thresholds, or the human-review trigger threshold without explicit approval — these are precision/recall-affecting and directly impact compliance posture.

## 13. General Working Rules

1. Inspect relevant files first — this doc is a map, not a substitute for reading the actual code.
2. Understand dependencies and existing behavior before changing anything.
3. Propose the change and explain the reasoning, especially for anything touching detection, confidence scoring, redaction, or run/document tracking.
4. Implement the smallest change that satisfies the task.
5. Run relevant tests (§10).
6. Report what changed and what was tested — call out any known limitation (§8/§9) your change interacts with.

Do not:
- Make unnecessary architectural changes.
- Delete existing functionality without explicit approval.
- Change existing API contracts (request/response shapes in `api/routes/*`) unless the task requires it.
- Reorganize the repo structure (§3) without approval.