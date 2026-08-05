# Solved Pipeline Issues: DocShield-AI

This document catalogs the technical bugs, architectural issues, and heuristics limitations resolved in the DocShield-AI dynamic detection pipeline.

---

## 1. Ollama/Qwen Detector Token Starvation
- **Issue**: The Qwen 3B reasoning model (`qwen3:4b`) printed extensive thinking process logs enclosed inside `<think>...</think>` tags. The thinking process consumed the entire `num_predict: 256` token allocation, starving the generation phase. This resulted in empty JSON payloads and caused Pydantic parsing errors (`Invalid JSON: EOF while parsing`).
- **Fix**: Increased `num_predict` in the Ollama option dictionary to `1024` to accommodate thinking logs. Additionally, wrapped Pydantic `model_validate_json()` in a warning try-except block to gracefully return `[]` on malformed outputs instead of crashing the pipeline.
- **Files**: [modules/detection/detectors/qwen_detector.py](file:///c:/Users/lenovo/Desktop/Data%20Factz%20Projects/DocShield-AI/modules/detection/detectors/qwen_detector.py)

---

## 2. Case-Sensitive Bypass (`BYPASS_LLM`)
- **Issue**: The `BYPASS_LLM` environment variable check inside `should_run()` used a case-sensitive string comparison. If `BYPASS_LLM` was set to `"True"`, the check `"true"` failed, causing the orchestrator to bypass LLM detection in some phases while running it in others.
- **Fix**: Re-coded `should_run()` to parse string settings case-insensitively, handling `"True"`, `"true"`, and `"1"` as valid bypass triggers.
- **Files**: [modules/detection/detectors/qwen_detector.py](file:///c:/Users/lenovo/Desktop/Data%20Factz%20Projects/DocShield-AI/modules/detection/detectors/qwen_detector.py)

---

## 3. Ollama Validator Timeout and Model Configuration
- **Issue**: The Ollama Validator was hardcoded to use `qwen2.5:8b`. If that model was not pulled locally, Ollama returned a `404 Not Found` response. Additionally, the validator's `REQUEST_TIMEOUT` was set to `30` seconds. On CPU-only local machines, loading and running the validator took longer than 30 seconds, causing persistent HTTP timeouts.
- **Fix**: 
  - Changed the default validator model to `qwen3:4b` (which is already pulled and active on the local machine).
  - Assigned class-level validator properties in `__init__` to check environment overrides `OAMA_VALIDATOR_MODEL` and `OAMA_REQUEST_TIMEOUT`.
  - Increased the default HTTP request timeout to `120` seconds.
- **Files**: [modules/detection/detectors/ollama_validator.py](file:///c:/Users/lenovo/Desktop/Data%20Factz%20Projects/DocShield-AI/modules/detection/detectors/ollama_validator.py)

---

## 4. Candidate Generation Field Label Leakage
- **Issue**: Standard field labels (e.g., `"Amount Billed"`, `"Patient Name"`) and standalone headers (e.g., `"Clinical Notes"`, `"Explanation of Benefits"`) matched the generic capitalized proper noun matcher (`PROPER_NOUN_PATTERN`). Since these labels were not blacklisted in `CANDIDATE_LABEL_WORDS`, they were added as candidates and sent to the Ollama/Qwen detector.
- **Fix**:
  - Implemented structured key-value parsing at line-level using colons and single dashes.
  - Extracted label offsets and registered them as exclusion zones. Proper noun matchers are now instructed to skip any match falling inside these exclusions.
  - Implemented `_is_title_or_header_line()`, which detects lines containing only capitalized title-style words and filters them out.
- **Files**: [modules/detection/pipeline_state.py](file:///c:/Users/lenovo/Desktop/Data%20Factz%20Projects/DocShield-AI/modules/detection/pipeline_state.py)
