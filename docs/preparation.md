# DocShield-AI Presentation and Demo Preparation

This guide is a factual presentation companion for the current DocShield-AI proof of concept. It intentionally avoids unverified accuracy, latency, cost, and compliance claims.

## 1. One-sentence explanation

DocShield-AI is a functional PII/PHI redaction PoC that combines deterministic detection, clinical and statistical NLP, bounded LLM validation, human-review records, extracted-text redaction, and a JSON audit trail.

## 2. Opening statement

> Sensitive data in healthcare and enterprise documents appears in both structured fields and unstructured prose. DocShield-AI uses a layered pipeline so deterministic patterns handle known identifiers, specialized NLP handles names and clinical concepts, and a bounded LLM reviews unresolved contexts. The workflow then calibrates confidence, creates review records, redacts extracted text, and fails closed when deterministic residual PII remains.

## 3. Recommended presentation flow

### Slide 1: Problem and scope

- Documents contain mixed PII, PHI, identifiers, prose, tables, and OCR noise.
- A single detector is not reliable across every representation.
- The current deliverable is a functional PoC, not a certified production system.
- Output is redacted extracted text plus a JSON report; it is not a redacted source PDF.

### Slide 2: Architecture

```text
Client -> FastAPI -> Upload/Storage -> Redis -> Worker
       -> Classification -> Extraction/OCR -> Detection
       -> Validation/Confidence -> Review records
       -> Redaction/Verification -> Report
```

Explain that the API and worker are separate processes. PostgreSQL stores workflow metadata; Redis transports jobs; local storage contains document artifacts.

### Slide 3: Hybrid detection

- Regex: deterministic identifiers and labeled fields.
- MedSpaCy: clinical entities in healthcare routes.
- Presidio and GLiNER: general and contextual NER.
- Azure OpenAI or Gemma: residual discovery and validation only when enabled.
- `EntityValidator`: structural checks, label trimming, and noise rejection.

Use the exact route order:

```text
healthcare: Regex -> MedSpaCy -> Presidio -> GLiNER -> LLM
generic:    Regex -> Presidio -> GLiNER -> LLM
```

Do not say the detectors run in parallel; the current implementation runs them sequentially.

### Slide 4: Bounded LLM design

- LLM processing can be disabled with `BYPASS_LLM=true`.
- Contexts are approximately 80 characters around unresolved candidates.
- At most three contexts are selected, with high-risk identifier cues prioritized.
- Decisions are `CONFIRM`, `RECLASSIFY`, or `REJECT`.
- Accepted/rejected decisions are written to the report audit.

Reason for this design: reduce unnecessary data exposure, latency, and token usage while preserving a residual semantic layer. Do not quote a percentage reduction unless measured in a documented benchmark.

### Slide 5: Confidence and human review

- High confidence: `>= 0.80`.
- Medium: `>= 0.60` and `< 0.80`.
- Low: `< 0.60`.
- Review records are created when final confidence is below `0.80`.
- MedSpaCy is capped at `0.95` to prevent perfect-confidence assumptions.

Important limitation: human review does not currently pause artifact creation or enforce an approve/block release gate.

### Slide 6: Redaction safety

1. Expand boundary-safe repeat occurrences.
2. Merge overlapping spans.
3. Replace spans from right to left.
4. Run bounded deterministic cleanup passes.
5. Verify span/value consistency and residual deterministic PII.
6. Raise `RedactionVerificationError` when verification fails.

The worker does not retry deterministic redaction-verification failures.

### Slide 7: Audit and access control

- Bearer-session authentication.
- `USER`, `REVIEWER`, and `ADMIN` roles.
- Document ownership/access checks.
- Entity, confidence, review, redaction, and report records.
- LLM candidate audit in report metadata and JSON output.
- Download paths confined to configured storage.

### Slide 8: Evidence and limitations

Evidence from the August 23, 2026 repository audit:

- `303 passed, 1 skipped` in the full pytest suite.
- Python compilation passed.
- Frontend JavaScript syntax passed.
- Dependency consistency passed with `pip check`.
- Alembic clean upgrade and downgrade round-trip passed on SQLite.

These results show regression health, not production precision or recall.

Explicit limitations:

- extracted-text redaction only;
- no encryption at rest;
- no release gate after review;
- limited handwriting and complex-table evaluation;
- no production monitoring or compliance certification.

## 4. Live demo sequence

### Before the demo

```powershell
.\scripts\local-check.ps1
.\scripts\local-migrate.ps1
```

Start the API and worker in separate terminals:

```powershell
.\scripts\local-api.ps1
.\scripts\local-worker.ps1
```

Open `http://localhost:8000/ui/`.

Checklist:

- PostgreSQL is reachable on `5432`.
- Redis is reachable on `6379`.
- `.env.local` contains no placeholder password.
- Ollama is running when `LLM_PROVIDER=gemma` and `BYPASS_LLM=false`.
- The migration head is applied.
- Use only synthetic demo documents.
- Do not display `.env.local`, tokens, database URLs, or raw production documents.

### Demo narration

1. Sign in and explain role-based access.
2. Upload one clearly synthetic document.
3. Show the generated run and asynchronous status.
4. Explain extraction mode and document classification.
5. Show detected entities, type, detector, confidence, and page/span metadata.
6. Show review records when the fixture produces a sub-`0.80` result.
7. Download the redacted text artifact.
8. Open the report and show detector usage plus LLM candidate audit.
9. State that the original PDF is not modified in the current PoC.

Do not run destructive database or storage reset commands during a presentation.

## 5. Failure recovery

| Failure | Safe response |
|---|---|
| API cannot start | Run `local-check.ps1`, verify `.env.local`, database, and port `8000` |
| Worker cannot start | Verify Redis, database access, and the selected environment file |
| Ollama/Azure unavailable | Set `BYPASS_LLM=true`, restart the worker, and explain deterministic fallback mode |
| Processing fails | Show status/error metadata; do not claim a successful artifact |
| Redaction verification blocks | Explain fail-closed behavior and inspect entity spans without exposing real PII |
| Demo is slow | Use a small synthetic fixture and a previously generated synthetic report |

## 6. Likely technical questions

### Why use multiple detectors?

Structured identifiers, clinical concepts, names, and contextual entities have different error modes. A hybrid pipeline uses deterministic rules where formats are stable, specialized NLP where domain language matters, and an LLM only for unresolved context.

### Why not send the whole document to an LLM?

The project deliberately bounds LLM context to reduce data exposure, latency, and token use. It also keeps deterministic and statistical detectors responsible for the entities they handle well.

### How are overlapping entities resolved?

After validation and normalization, overlapping spans are ranked with:

```text
(is_authoritative, type_rank, detector_priority, confidence, span_length)
```

This behavior is regression-tested because small priority changes can alter precision and recall across the pipeline.

### What prevents an LLM hallucination from becoming a redaction?

Returned values must align to text spans in the original context. Candidates also pass validation, mapping, confidence, deduplication, and overlap resolution. A hallucinated value that cannot be located is discarded.

### Does human review block output?

No. The current PoC creates review records but does not enforce a release gate. A production design should add an explicit approve/block state before artifact release.

### What happens when redaction verification fails?

The workflow raises a deterministic verification error and the worker does not retry it. The document remains failed/blocked for investigation rather than silently releasing an artifact.

### Is the system HIPAA compliant?

Do not claim compliance. Say:

> The PoC is designed around PII/PHI redaction concerns, but it is not certified or production-hardened. Authentication and auditability exist, while encryption at rest, deployment controls, monitoring, formal validation, and compliance assessment remain required.

### How do you measure accuracy?

Use labeled evaluation data and `metrics.py` to calculate precision and recall. Passing tests protect known behavior but do not establish performance on real-world populations.

## 7. Safe claims and claims to avoid

Safe statements:

- The full test suite passed during the documented audit.
- The workflow fails closed on deterministic residual-PII verification.
- LLM contexts are bounded and capped.
- The system supports local and Docker profiles.
- The current artifact is redacted extracted text.

Avoid unless separately measured and documented:

- `100% accuracy`, `zero false negatives`, or `100% masking`;
- fixed cost or token-savings percentages;
- fixed milliseconds-per-page or seconds-per-document figures;
- production scalability claims;
- HIPAA/GDPR/CCPA certification claims;
- statements that human review blocks release;
- statements that the source PDF is redacted.

## 8. Final pre-presentation check

```powershell
python -m pytest -q
git status --short
```

- Confirm only intended synthetic fixtures are present.
- Confirm `.env` and `.env.local` are ignored.
- Confirm no secrets or storage artifacts are staged.
- Confirm the latest migration is staged.
- Confirm the API and worker use the same environment profile.
- Keep `../README.md` and `doc.md` open for reference.

## 9. Closing statement

> DocShield-AI demonstrates a defense-in-depth approach to document redaction: layered detection, deterministic validation, bounded semantic review, confidence-based human-review records, and fail-closed verification. The PoC establishes a testable architecture while making its production gaps explicit, which gives the next phase a clear engineering roadmap.
