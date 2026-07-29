# DocShield-AI PoC Interview Preparation

## 1. Purpose Of This Document

This document prepares the team for a PoC demo with a Director and Senior Architect. It explains how to present the solution, how Dev 1 and Dev 2 should split the explanation, what questions may be asked, and how to answer client-facing and architecture-facing concerns.

Target audience:

- Director / business stakeholder
- Senior architect / technical evaluator
- Client security / compliance reviewer
- Internal engineering team

Core message:

> DocShield-AI is an API-first document intelligence PoC that uploads documents, extracts text using native parsing or OCR, detects PII/PHI, creates review records, generates redacted output, and produces audit reports through an async worker pipeline.

---

## 2. One-Minute Opening Pitch

Use this at the beginning of the demo.

```text
DocShield-AI is a document intelligence PoC for identifying and redacting sensitive information from enterprise documents.

A user uploads a document through the UI. The FastAPI backend validates and stores the file, creates metadata in PostgreSQL, and pushes a job to Redis. A background worker consumes that job and runs the full processing workflow: document classification, OCR/native text extraction, OCR confidence evaluation, PII/PHI detection, human review preparation, redaction, and audit report generation.

The PoC is intentionally modular. OCR, storage, detection engines, review workflow, and reporting can be upgraded independently for production.
```

---

## 3. Demo URL And Runtime

Local Docker demo:

```text
PoC UI:     http://localhost:8001/ui/
Swagger:    http://localhost:8001/docs
Health API: http://localhost:8001/health/
PostgreSQL: 127.0.0.1:5433
Redis:      127.0.0.1:6380
```

Docker command:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml up -d --build
```

Useful validation commands:

```powershell
Invoke-RestMethod http://localhost:8001/health/
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml ps
docker logs docshield-ai-live-worker --tail 100
```

---

## 4. Clean End-To-End Demo Script

### Step 1 - Start With The Problem

Explain:

```text
Enterprises receive invoices, medical records, tax forms, insurance documents, bank statements, contracts, and identity documents. These documents often contain PII or PHI. Manually identifying and redacting sensitive information is slow, inconsistent, and hard to audit.
```

### Step 2 - Show The UI

Open:

```text
http://localhost:8001/ui/
```

Explain:

```text
The UI is intentionally simple for the PoC. It is a static HTML/CSS/JS frontend served directly by FastAPI at /ui/. It lets the user upload files, track processing status, preview extracted text, review findings, and download redacted and audit artifacts.
```

### Step 3 - Upload A Document

Use a sample invoice, medical note, or scanned image.

Explain:

```text
The upload API validates the file, stores it in local storage, writes document metadata to PostgreSQL, creates a processing job, and pushes a lightweight job message to Redis.
```

API involved:

```text
POST /upload/
POST /upload/bulk
```

### Step 4 - Explain Redis

Explain clearly:

```text
Redis is not only for OCR. Redis is the async job queue for the entire document processing workflow. OCR is only one step inside the worker workflow.
```

Redis queue:

```text
document_processing
```

Payload:

```text
document_id
```

### Step 5 - Show Processing Status

API involved:

```text
GET /documents/{document_id}/status
```

Explain:

```text
The UI polls status from the backend. The workflow stage and processing status are stored in PostgreSQL, so the UI can show where the document is in the pipeline.
```

### Step 6 - Explain Workflow Steps

Worker flow:

```text
LOAD_DOCUMENT
UPDATE_PROCESSING_STATUS
DOCUMENT_CLASSIFICATION
OCR_DECISION
OCR_EXECUTION
STORE_OCR_RESULTS
DETECTION_EXECUTION
STORE_DETECTION_RESULTS
HUMAN_REVIEW
REDACTION
REPORT_GENERATION
COMPLETE_WORKFLOW
```

### Step 7 - Show Extracted Text

API involved:

```text
GET /documents/{document_id}/text
```

Explain:

```text
The extraction path is selected dynamically. Searchable PDFs use native extraction. TXT and DOCX use native text extraction. Scanned PDFs and images use PaddleOCR.
```

### Step 8 - Show PII/PHI Findings

API involved:

```text
GET /documents/{document_id}/reviews
```

Explain:

```text
The detection orchestrator runs detectors sequentially. Regex runs first for structured high-confidence patterns. Other detectors run only when useful candidates remain. Accepted spans are masked so later detectors do not duplicate already resolved entities.
```

### Step 9 - Show Human Review

API involved:

```text
PATCH /reviews/{review_id}
```

Explain:

```text
Entities below the review threshold are sent to human review. In this PoC, confidence below 0.80 creates a pending review record.
```

### Step 10 - Show Redaction And Report

APIs involved:

```text
GET /documents/{document_id}/redactions
GET /redactions/{redaction_id}/file
GET /documents/{document_id}/reports
GET /reports/{report_id}/file
```

Explain:

```text
The worker generates a redacted text artifact and an audit report JSON. The report contains document ID, OCR result ID, total entities, PII count, PHI count, review count, detectors used, and redaction status.
```

---

## 5. Recommended Team Split

## Dev 1 - Platform, API, OCR, Workflow

Dev 1 should explain the foundation and end-to-end processing flow.

Topics:

- Business problem and PoC scope
- FastAPI backend and static UI
- API endpoints and Swagger
- Upload validation and storage
- PostgreSQL schema and repositories
- Redis job queue
- Worker and retry behavior
- Workflow planner and workflow stages
- OCR decision engine
- Native extraction and PaddleOCR
- OCR confidence calculation
- Docker setup and model cache volume
- Demo runbook and troubleshooting

Dev 1 opening lines:

```text
I will explain how the document enters the system, how we queue it for async processing, how the worker executes the full workflow, and how OCR confidence and persisted artifacts are generated.
```

Dev 1 should own these questions:

- Why Redis?
- Is Redis only for OCR?
- How does the worker process documents?
- How are files stored?
- How is OCR selected?
- How is OCR confidence calculated?
- What happens if the worker fails?
- How do we run it in Docker?

## Dev 2 - Detection, PII/PHI, Review, Redaction, Reporting

Dev 2 should explain the intelligence layer and governance outputs.

Topics:

- PII/PHI detection strategy
- Dynamic detection orchestrator
- Domain-based detector routing
- Regex, Presidio, GLiNER, MedSpaCy, optional Qwen/Ollama
- PipelineState and MaskManager
- Candidate-based stopping
- Deduplication and overlap resolution
- Entity confidence calibration
- PII vs PHI classification
- Human review threshold
- Redaction generation
- Audit report JSON
- Edge cases and false positives
- Future production hardening

Dev 2 opening lines:

```text
I will explain how extracted text is analyzed for PII and PHI, why the orchestrator runs detectors sequentially, how we avoid duplicate detections, and how review, redaction, and audit outputs are generated.
```

Dev 2 should own these questions:

- Why Regex first?
- Why does GLiNER run after Regex in some documents?
- How are PII and PHI classified?
- What happens with low confidence entities?
- How are duplicate and overlapping detections handled?
- How are false positives managed?
- Why is Qwen/Ollama optional?
- How is sensitive data protected from LLM exposure?

---

## 6. Architecture Explanation

Use this explanation when showing the technical architecture diagram.

```text
The PoC has seven logical layers.

The UI layer is a static frontend served by FastAPI. The application layer exposes upload, document, review, redaction, report, and health APIs. The async layer uses Redis to decouple upload latency from heavy document processing. The worker layer executes the ordered document workflow. The extraction layer chooses native parsing or PaddleOCR depending on file type and searchability. The AI detection layer runs a dynamic orchestrator over Regex, Presidio, GLiNER, MedSpaCy, and optional Qwen/Ollama. The storage layer persists metadata in PostgreSQL and artifacts under local storage.
```

Main runtime components:

| Component | Responsibility |
| --- | --- |
| `app.py` | FastAPI app, route registration, Swagger customization, static UI mount |
| `frontend/` | Static PoC UI served at `/ui/` |
| `api/routes` | Upload, document status/text, reviews, redactions, reports, health |
| `modules/upload` | File validation, storage, DB records, Redis publish |
| `redis_queue` | Producer, consumer, worker, job schema |
| `orchestration/workflow.py` | End-to-end document processing workflow |
| `modules/extraction` | Native text/PDF extraction, PaddleOCR, OCR confidence |
| `modules/classification` | Rules-based document classification |
| `modules/detection` | Dynamic PII/PHI detection orchestration |
| `database` | SQLAlchemy models, repositories, Alembic migrations |
| `storage/` | Uploaded files, extracted text, redacted files, reports |

---

## 7. OCR Confidence Explanation

Short answer:

```text
OCR confidence is a weighted score made from OCR engine confidence, text quality, and text coverage.
```

Formula:

```text
final_ocr_confidence =
  raw_engine_confidence * 0.70
  + text_quality_score * 0.20
  + coverage_score * 0.10
```

Where:

```text
raw_engine_confidence = average line confidence returned by PaddleOCR
text_quality_score = valid characters + meaningful words - noise penalty
coverage_score = extracted characters per page
```

Coverage bands:

```text
>= 500 chars/page  -> 1.00
>= 200 chars/page  -> 0.85
>= 75 chars/page   -> 0.70
>= 25 chars/page   -> 0.45
< 25 chars/page    -> 0.20
```

Quality caps:

```text
text_quality < 0.30 -> final score capped at 0.45
text_quality < 0.50 -> final score capped at 0.65
very low coverage with weaker quality -> final score capped at 0.75
```

---

## 8. Detection Orchestrator Explanation

Short answer:

```text
The orchestrator is designed to maximize precision first, then recall. Regex handles structured high-confidence fields first. Later detectors run only on remaining unmasked text when candidate spans remain.
```

Detection route examples:

```text
financial       Regex -> GLiNER
healthcare      Regex -> MedSpaCy -> GLiNER
corporate/legal Regex -> GLiNER -> Presidio
generic/mixed   Regex -> Presidio -> GLiNER -> MedSpaCy
```

Why Regex first:

```text
Regex is fast, deterministic, explainable, and high precision for structured values like email, phone, bank account, tax ID, SSN, invoice number, dates, labeled diagnosis, medication, and addresses.
```

Why masking is used:

```text
Once a detector accepts an entity span, that span is masked. Later detectors only see unresolved text. This avoids duplicate detections and reduces unnecessary model calls.
```

Why Qwen/Ollama is optional:

```text
The PoC keeps LLM usage bounded. It never sends the full document. It only validates unresolved or low-confidence snippets when enabled. Docker currently bypasses LLM by default for predictable local demos.
```

---

## 9. Business / Director Questions And Answers

### Q1. What problem does this PoC solve?

Answer:

```text
It automates sensitive-data discovery and redaction from enterprise documents. Instead of manually reviewing each file, the system extracts text, detects PII/PHI, creates review tasks, redacts sensitive values, and generates an audit report.
```

### Q2. What is the business value?

Answer:

```text
The value is faster document review, lower manual effort, improved consistency, and better auditability. It also gives us a foundation for compliance workflows around privacy, security, and document governance.
```

### Q3. Is this production ready?

Answer:

```text
This is a PoC, not a production deployment. The core processing flow is implemented, but production would need authentication, authorization, encryption, object storage, monitoring, audit dashboards, access controls, deployment hardening, and model performance benchmarking.
```

### Q4. How do we measure success?

Answer:

```text
Success should be measured by extraction accuracy, entity precision/recall, false positive rate, false negative rate, processing time per document, review workload reduction, and audit completeness.
```

### Q5. Can this support multiple document types?

Answer:

```text
Yes. The classifier currently supports invoices, receipts, medical records, lab reports, prescriptions, insurance documents, bank statements, tax forms, identity documents, contracts, and unknown documents. The rules are modular and can be extended.
```

### Q6. What happens when confidence is low?

Answer:

```text
Low-confidence entities are not blindly accepted. They are flagged for human review. In this PoC, entity confidence below 0.80 creates a pending review record.
```

### Q7. How does the client verify what happened?

Answer:

```text
The system stores document status, OCR output, detected entities, confidence scores, review records, redaction metadata, and audit reports. The client can inspect both database records and generated artifacts.
```

### Q8. What is the roadmap after PoC?

Answer:

```text
The roadmap is authentication, role-based review workflow, production object storage, encryption, monitoring, model benchmarking, improved dashboarding, stronger document classification, bulk processing controls, and enterprise deployment automation.
```

---

## 10. Senior Architect Questions And Answers

### Q1. Why did you use Redis?

Answer:

```text
OCR and detection can be slow, especially for scanned PDFs and images. Redis lets upload return quickly while a worker processes the document asynchronously. It also gives us retry handling and a clear separation between request handling and heavy processing.
```

### Q2. Does Redis perform only OCR?

Answer:

```text
No. Redis queues the entire document processing job. The job payload contains the document ID. The worker consumes that job and runs classification, OCR, detection, review preparation, redaction, reporting, and completion.
```

### Q3. Why not process synchronously in the upload API?

Answer:

```text
Synchronous processing would make uploads slow and fragile. A scanned PDF could take much longer than a normal HTTP request should wait. Async processing improves responsiveness, failure isolation, retry capability, and horizontal scalability.
```

### Q4. How does the worker know what to process?

Answer:

```text
The upload API creates a document row and processing job row in PostgreSQL, then pushes a DocumentJob with the document_id to Redis. The worker consumes the ID, loads the document context from PostgreSQL, and executes the workflow.
```

### Q5. How is the workflow ordered?

Answer:

```text
WorkflowPlanner returns a fixed ordered plan: load document, update status, classify, OCR decision, OCR execution, store OCR, detection, store detections, human review, redaction, report generation, and completion.
```

### Q6. How do you handle failure and retry?

Answer:

```text
The worker catches workflow failures, updates the processing job, and requeues when retry count is below the configured limit. The processing job tracks retry_count, workflow_stage, status, and error_message.
```

### Q7. Why local storage instead of S3 or MinIO?

Answer:

```text
Local storage keeps the PoC lightweight and easy to run. The storage logic is isolated, so production can replace it with S3, Azure Blob, MinIO, or another object storage provider.
```

### Q8. How do you prevent PaddleOCR downloading models every time?

Answer:

```text
We added a Docker volume named paddle_models mounted at /root/.paddlex for API and worker containers. After the first download, Paddle model files persist across container recreation.
```

### Q9. Why use multiple detectors?

Answer:

```text
Different entity types require different methods. Regex is best for structured IDs and labeled fields. Presidio is useful for common PII. MedSpaCy targets clinical entities. GLiNER helps with semantic entity detection. Optional Qwen/Ollama can validate unresolved snippets.
```

### Q10. How do you avoid duplicate detections?

Answer:

```text
The pipeline masks accepted spans after each detector. Later detectors only run on remaining unmasked text. Deduplication also merges exact same type/value/page/span detections while preserving repeated values at different document positions.
```

### Q11. How are overlaps resolved?

Answer:

```text
Overlapping detections are ranked using authoritative owner, specialized type priority, detector priority, confidence score, and span length. The stronger candidate is kept.
```

### Q12. How do you avoid sending full documents to LLMs?

Answer:

```text
The LLM path is optional and bounded. It only receives small unresolved candidate snippets or low-confidence contexts. Docker has BYPASS_LLM=True by default, so demos do not require LLM calls.
```

### Q13. How does the UI connect to the backend?

Answer:

```text
The UI is served by the same FastAPI process at /ui/. It calls same-origin APIs, so no CORS configuration is required for the PoC.
```

### Q14. How would this scale?

Answer:

```text
Scale API containers horizontally for upload and read traffic. Scale worker containers horizontally for OCR/detection throughput. Move storage to object storage. Use managed PostgreSQL and managed Redis. Add queue visibility, dead-letter handling, metrics, and autoscaling.
```

### Q15. What are the main production gaps?

Answer:

```text
Authentication, authorization, encryption, secrets management, audit dashboard, object storage, virus scanning, rate limiting, tenant isolation, document retention policies, monitoring, alerting, structured observability, and formal accuracy evaluation.
```

---

## 11. Client Perspective Questions And Answers

### Q1. Can it detect all PII and PHI globally?

Answer:

```text
No system should claim 100 percent global coverage. The PoC supports a broad generic PII/PHI catalog and can be extended. Final coverage depends on jurisdiction, document type, language, scan quality, and business policy.
```

### Q2. Why did it detect Tax ID as SSN?

Answer:

```text
The value format matches SSN-style XXX-XX-XXXX, but the label says Tax Id. For production, we should prefer contextual labels and classify it as TAX_ID when the field label is Tax Id.
```

### Q3. Is a company name PII?

Answer:

```text
Usually no, because PII applies to natural persons. A company name can become personal data when it identifies a sole proprietor, individual customer, employee, or account holder.
```

### Q4. Is ZIP code PII?

Answer:

```text
A ZIP code alone is weak identifier. In address context, especially with name or street, it can be personal data. The PoC treats ZIP as review-required PII when it appears in address-like context.
```

### Q5. Why is PHI zero for an invoice?

Answer:

```text
PHI requires health-related context. A normal computer invoice with tax ID, IBAN, addresses, and ZIP codes contains PII but not PHI. A medical bill, diagnosis note, prescription, or lab report could contain PHI.
```

### Q6. Can the user approve or reject detections?

Answer:

```text
Yes. The review API supports reviewer decisions. The UI provides approve and reject actions for review records.
```

### Q7. Can it process scanned documents?

Answer:

```text
Yes. Scanned PDFs and images are routed to PaddleOCR. Searchable PDFs and native text files use native extraction.
```

### Q8. What if OCR is wrong?

Answer:

```text
OCR confidence and text quality are calculated. Low-quality extraction can be flagged. In production, poor OCR confidence should trigger manual review or reprocessing with a better OCR/model provider.
```

### Q9. Can the client define custom entities?

Answer:

```text
Yes. Regex patterns, entity mapping, document classification rules, and detector routes are modular. We can add client-specific IDs, business fields, or policy-based redaction rules.
```

### Q10. Can it redact PDFs directly?

Answer:

```text
The current PoC generates redacted text artifacts. Production PDF-native redaction would be a future enhancement requiring coordinate-based redaction and visual verification.
```

---

## 12. Real-Time Demo Problems And How To Answer

### Problem 1 - UI opens but upload fails

Likely cause:

```text
API dependencies are not fully running, or PostgreSQL/Redis connection failed.
```

Response:

```text
The UI is served by FastAPI, but upload requires PostgreSQL and Redis. We will check /health, Docker service status, and worker logs.
```

Commands:

```powershell
docker compose -p docshield-ai-live -f docker-compose.yml -f docker-compose.local-gui.yml ps
docker logs docshield-ai-live-api --tail 100
docker logs docshield-ai-live-worker --tail 100
```

### Problem 2 - Redis queue looks empty

Answer:

```text
That can be normal. The worker consumes jobs quickly, so Redis may appear empty between uploads. The processing history is stored in PostgreSQL processing_jobs.
```

### Problem 3 - PaddleOCR downloads model during demo

Answer:

```text
PaddleOCR downloads official models on first use. We persist /root/.paddlex using the paddle_models Docker volume, so after the first download it should reuse the cached model.
```

### Problem 4 - Worker stuck or document remains PROCESSING

Likely checks:

```text
worker logs
processing_jobs.error_message
Redis connection
PaddleOCR model download/status
file path availability between API and worker
```

Response:

```text
The workflow stage stored in processing_jobs tells us where it stopped. The worker has retry handling, and failed jobs can be diagnosed from error_message and logs.
```

### Problem 5 - False positive entity

Example:

```text
Tax Id detected as SSN
```

Response:

```text
This is expected in early PoC pattern matching when value format resembles SSN. The fix is contextual classification: label Tax Id as TAX_ID when field label says Tax Id, even if the number format resembles SSN.
```

### Problem 6 - Missed entity

Response:

```text
Misses can happen due to OCR quality, unsupported pattern, or detector routing. The PoC exposes extracted text and report output so we can diagnose whether the issue is extraction or detection. We can then add a regex rule, adjust the route, or add a client-specific entity.
```

### Problem 7 - GLiNER or MedSpaCy behavior questioned

Response:

```text
Detector order depends on document domain. Healthcare routes run Regex -> MedSpaCy -> GLiNER. Generic or mixed routes run Regex -> Presidio -> GLiNER -> MedSpaCy. Also, once Regex accepts a span, it is masked, so later detectors do not reprocess it.
```

### Problem 8 - Report total differs from expected

Response:

```text
The report counts persisted entities after deduplication and overlap resolution. Repeated same value at different positions is preserved because each occurrence needs its own redaction span.
```

---

## 13. Edge Cases To Be Ready For

| Edge Case | Expected Handling / Talking Point |
| --- | --- |
| Scanned PDF | Routed to PaddleOCR |
| Searchable PDF | Routed to native PDF extraction |
| TXT/DOCX | Routed to native text extraction |
| Image upload | Routed to PaddleOCR |
| Poor image quality | OCR confidence may be lower; should trigger review in production |
| Rotated/skewed scan | PaddleOCR options can help; production may need stronger preprocessing |
| Handwriting | Current PoC may not handle well; future OCR/model enhancement |
| Multi-page PDF | Pages are processed and merged with page break markers |
| Table-heavy invoice | OCR extracts text and optional layout metadata; table structure may need production tuning |
| Same entity appears multiple times | Preserved as separate redaction targets if spans differ |
| Duplicate detector hit on same span | Deduplicated |
| Overlapping entity spans | Stronger detection kept using priority/confidence rules |
| No entities found | Report can show zero findings; workflow still completes |
| Empty OCR output | OCR confidence becomes 0.0 |
| Large files | Upload validator enforces max size; production can add async chunking |
| Password-protected PDF | Current PoC likely fails; production needs protected-file handling |
| Non-English document | Current detection is English-first; production needs multilingual strategy |
| LLM unavailable | BYPASS_LLM=True allows deterministic demo without LLM |
| Redis down | Upload may fail at job publish or worker cannot consume |
| PostgreSQL down | Metadata and workflow persistence fail |
| API restarts | Persisted DB/storage state remains; in-flight queue behavior depends on Redis state |
| Container recreated | Paddle model cache persists through paddle_models volume |
| Address ZIP false positive | Review-required confidence allows human validation |
| Business entity vs personal entity | Classification depends on natural-person context |

---

## 14. Key Technical Decisions And Reasoning

| Decision | Reason |
| --- | --- |
| FastAPI | Simple API-first backend, automatic OpenAPI docs, Pydantic contracts |
| Static UI served by FastAPI | Avoids extra frontend build/runtime for PoC, no CORS issue |
| PostgreSQL | Reliable metadata, workflow status, audit records |
| Redis | Async queue for full document processing pipeline |
| Worker process | Isolates heavy OCR/detection from upload API |
| Local storage | Simple PoC artifact persistence, replaceable later |
| PaddleOCR | Handles scanned PDFs and images |
| PyMuPDF/native extraction | Faster for searchable PDFs |
| Regex first | Fast, explainable, high precision for structured fields |
| Dynamic detector routing | Avoids running every detector on every document |
| Masking accepted spans | Prevents duplicate detections and reduces later detector noise |
| Human review threshold | Keeps low-confidence results auditable |
| Audit report JSON | Provides traceability for compliance/demo review |

---

## 15. What To Say If Asked About Production Readiness

Recommended answer:

```text
The PoC proves the processing architecture and detection workflow. For production, we would add authentication, role-based access control, encryption at rest and in transit, object storage, audit dashboards, structured observability, dead-letter queues, virus scanning, tenant isolation, retention policies, and formal model accuracy benchmarking.
```

Do not say:

```text
This is already production ready.
```

Say instead:

```text
The architecture is production-extensible, but production hardening is intentionally separate from the PoC.
```

---

## 16. Security And Compliance Talking Points

Current PoC:

```text
- Stores metadata in PostgreSQL.
- Stores artifacts in local storage.
- Generates redacted text and audit report.
- Avoids full-document LLM calls by default.
- Uses review records for low-confidence detections.
```

Production hardening needed:

```text
- Authentication and authorization
- Role-based reviewer access
- Encryption at rest and in transit
- Secrets management
- Object storage access policies
- Data retention and purge rules
- Tenant isolation
- Audit dashboards
- Virus/malware scanning before processing
- Redaction verification workflow
- PDF-native redaction with visual validation
- Logging without leaking sensitive values
```

---

## 17. Accuracy And Evaluation Talking Points

Current validation approach:

```text
- Unit tests for regex detector
- Tests for detection orchestration
- Tests for worker retry behavior
- Tests for API E2E behavior
- Tests for PaddleOCR layout parsing
- Tests for workflow behavior
```

For production evaluation:

```text
- Create labeled test set by document type
- Measure precision, recall, F1 by entity type
- Track false positives and false negatives
- Separate OCR accuracy from detection accuracy
- Benchmark OCR providers on scanned documents
- Maintain client-specific regression test sets
- Add review feedback loop for model/rule improvement
```

---

## 18. Strong Answers For Common Deep-Dive Questions

### Why do we store both DB rows and files?

```text
The database stores searchable metadata, status, entities, reviews, and report references. The file system stores larger artifacts like uploads, extracted text, redacted files, and JSON reports. This keeps database rows manageable and artifact storage replaceable.
```

### Why does the report only show Regex for some documents?

```text
If Regex resolves all candidate spans and no unresolved candidates remain, the orchestrator stops early. That is intentional to avoid unnecessary model calls. For structured invoices, Regex may be enough.
```

### Why did GLiNER run instead of MedSpaCy?

```text
Detector order depends on document domain. Healthcare route prioritizes MedSpaCy before GLiNER. Generic and mixed routes put GLiNER before MedSpaCy. Also, any Regex-detected diagnosis span is masked and not reprocessed by MedSpaCy.
```

### How do we classify PII vs PHI?

```text
The entity mapper assigns privacy_category based on entity type and health context. PII identifies a natural person directly or indirectly. PHI is identifiable health-related information such as diagnosis, medication, procedure, MRN, lab results, or healthcare payment context.
```

### Is business data PII?

```text
Not always. Company name, company address, invoice number, and business amount are usually not PII unless they identify or link to a natural person, sole proprietor, patient, employee, or individual account holder.
```

### How is human review connected to confidence?

```text
When persisted entity confidence is below 0.80, the workflow creates a pending review record. The reviewer can approve or reject from the UI through PATCH /reviews/{review_id}.
```

### What does redaction currently produce?

```text
The PoC produces redacted text artifacts under storage/redacted. PDF-native visual redaction is a future production enhancement.
```

### How do we handle duplicate uploads?

```text
Currently each upload creates a new document and job. Production can add checksum-based duplicate detection if required.
```

### Can multiple workers run?

```text
Yes, the design supports horizontal worker scaling because jobs are pulled from Redis. Production should add stronger locking/idempotency and dead-letter handling.
```

### Why use Alembic?

```text
Alembic gives controlled schema migrations for PostgreSQL. The Docker migrate service runs alembic upgrade head before API and worker startup.
```

---

## 19. Demo Checklist

Before the meeting:

```text
[ ] Docker Desktop running
[ ] Containers built and running
[ ] API health returns healthy
[ ] UI opens at /ui/
[ ] Swagger opens at /docs
[ ] Worker logs clean
[ ] PostgreSQL accessible through pgAdmin or psql
[ ] Redis accessible through RedisInsight
[ ] Sample documents ready: invoice, medical text, scanned image/PDF
[ ] Paddle model already downloaded or explain first-time download
[ ] Browser zoom set to readable level
[ ] Architecture and workflow diagrams ready
```

During the demo:

```text
[ ] Start with business problem
[ ] Show UI
[ ] Upload one sample document
[ ] Show status polling
[ ] Show extracted text
[ ] Show review queue
[ ] Show redacted artifact
[ ] Show audit report
[ ] Show database tables if architect asks
[ ] Show worker logs only if needed
[ ] End with production roadmap
```

After the demo:

```text
[ ] Capture feedback
[ ] Capture missed entities or false positives
[ ] Capture requested document types
[ ] Capture security/compliance requirements
[ ] Capture production deployment expectations
```

---

## 20. Final Closing Statement

Use this to close the demo.

```text
This PoC demonstrates a complete document processing path: upload, async workflow, OCR/native extraction, PII/PHI detection, review, redaction, and audit reporting. The design is modular, so we can replace local storage with object storage, scale workers independently, add client-specific entities, and harden the platform for production security and compliance.
```