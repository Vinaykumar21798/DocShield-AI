"""Isolated OCR engine benchmark (OCR-only).

Compares OCR engines on the sample documents already present under
storage/runs/ WITHOUT touching production code. No detection pipeline runs
(no regex/presidio/medspacy/gliner/qwen).

Engines:
  1. PaddleOCR  - the current implementation (PaddleOCRExtractionService),
                 the baseline.
  2. Surya      - reported NOT_AVAILABLE when the ``surya`` package is absent.
  3. GLM-OCR    - reported NOT_AVAILABLE when the ``glmocr`` package is absent.

Each document is extracted inside a spawned child process guarded by a
per-document wall-clock timeout, so a single hung page cannot stall the whole
benchmark. On timeout the document is marked TIMEOUT and the benchmark moves
on; the report is still generated.

For every available engine and document we capture:
  - extracted text
  - CER/WER where a native text-layer ground truth exists
  - page count
  - reading order score
  - table detection (blocks / rows / multi-column rows / cells / avg columns)
  - bounding-box coverage of text lines
  - structured output summary
  - processing time and seconds/page

No production code is modified and no models are downloaded. PP-Structure
layout analysis is intentionally disabled for PaddleOCR because its models are
not cached locally and downloading weights is out of scope for this benchmark;
the coordinate-block fallback (the path that produced the existing content.txt
baseline) is used instead.

Usage:
    python -m benchmarks.eval_ocr_engines

Environment:
    OCR_EVAL_DOC_TIMEOUT   per-document timeout in seconds (default 900)
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import logging
import multiprocessing as mp
import os
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH_DIR))

# No detection runs in this benchmark, but keep the log noise suppressed
# (loguru defaults to DEBUG; extraction libraries can also emit warnings).
logging.disable(logging.WARNING)

from loguru import logger  # noqa: E402

logger.remove()
logger.add(sys.stderr, level="ERROR")

OUTPUT_DIR = Path("benchmarks/output")
ENGINE_JSON = OUTPUT_DIR / "ocr_engine_eval.json"
ENGINE_MD = OUTPUT_DIR / "ocr_engine_eval.md"

DOC_TIMEOUT = int(os.environ.get("OCR_EVAL_DOC_TIMEOUT", "900"))

from benchmarks.ocr_quality import calculate_cer, calculate_wer  # noqa: E402
from eval_common import write_json  # noqa: E402


# ---------------------------------------------------------------------------
# Sample documents (paths verified to exist).
# ---------------------------------------------------------------------------
SAMPLE_DOCUMENTS: list[dict[str, Any]] = [
    {
        "key": "insurance_policy",
        "label": "Insurance Policy Document",
        "pages": 6,
        "original": (
            "storage/runs/03b21b46-ea02-4d21-9429-331a9ca7456a/documents/"
            "3148c6b8-7198-45d1-951f-2a1dbde6e623/original/Insurance Policy Document.pdf"
        ),
    },
    {
        "key": "claims_form",
        "label": "Claims Form (CMS-1500/UB-04)",
        "pages": 4,
        "original": (
            "storage/runs/d09df4d9-5f92-4ecc-954d-c32ef4dda562/documents/"
            "2530dd8b-91a1-4325-b33c-178d1e420af9/original/"
            "Claims Form (CMS-1500_UB-04)_02.pdf"
        ),
    },
]


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _native_ground_truth(original_path: str) -> Optional[str]:
    """Return the PDF text layer as reference ground truth (or None)."""
    try:
        import fitz
    except ImportError:
        return None
    try:
        with fitz.open(original_path) as pdf:
            return "\n".join(
                page.get_text("text") for page in pdf
            ).strip()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Text / structure metrics
# ---------------------------------------------------------------------------
def text_stats(text: str) -> dict[str, Any]:
    return {
        "chars": len(text),
        "non_whitespace_chars": len(re.sub(r"\s", "", text)),
        "lines": len([line for line in text.splitlines() if line.strip()]),
    }


def summarize_structured(structured_output: Optional[dict]) -> dict[str, Any]:
    """Summarize an engine structured_output for cross-engine comparison."""
    if not structured_output:
        return {"present": False}

    pages = structured_output.get("pages") or []
    blocks_by_type: dict[str, int] = {}
    total_blocks = 0
    total_lines = 0
    lines_with_bbox = 0
    table_blocks = 0
    table_rows = 0
    table_cells = 0
    multi_col_rows = 0
    col_counts: list[int] = []
    order_pairs = 0
    order_ok = 0

    for page in pages:
        for block in page.get("blocks") or []:
            block_type = block.get("block_type") or "text"
            blocks_by_type[block_type] = blocks_by_type.get(block_type, 0) + 1
            total_blocks += 1

            for line in block.get("lines") or []:
                total_lines += 1
                if line.get("bbox"):
                    lines_with_bbox += 1

            if block_type == "table":
                table_blocks += 1
                table = block.get("table") or {}
                for row in table.get("rows") or []:
                    non_empty = [cell for cell in row if str(cell).strip()]
                    table_rows += 1
                    table_cells += len(non_empty)
                    col_counts.append(len(non_empty))
                    if len(non_empty) >= 2:
                        multi_col_rows += 1

        # reading order: consecutive blocks must be top-left ordered
        prev_top: Optional[float] = None
        for block in page.get("blocks") or []:
            bbox = block.get("bbox")
            top = float(bbox[1]) if bbox else None
            if top is None:
                continue
            if prev_top is not None:
                order_pairs += 1
                if top >= prev_top - 2.0:
                    order_ok += 1
            prev_top = top

    table_score = (multi_col_rows / table_rows) if table_rows else 0.0
    avg_cols = (sum(col_counts) / len(col_counts)) if col_counts else 0.0

    return {
        "present": True,
        "layout_sources": structured_output.get("layout_sources")
        or sorted(
            {
                page.get("layout_source")
                for page in pages
                if page.get("layout_source")
            }
        ),
        "layout_analysis_used": bool(
            structured_output.get("layout_analysis_used")
        ),
        "pages": len(pages),
        "total_blocks": total_blocks,
        "blocks_by_type": blocks_by_type,
        "total_lines": total_lines,
        "lines_with_bbox": lines_with_bbox,
        "bbox_coverage": (
            round(lines_with_bbox / total_lines, 4) if total_lines else None
        ),
        "table_blocks": table_blocks,
        "table_rows": table_rows,
        "table_cells": table_cells,
        "multi_col_rows": multi_col_rows,
        "avg_columns_per_row": round(avg_cols, 3),
        "table_score": round(table_score, 4),
        "reading_order_score": (
            round(order_ok / order_pairs, 4) if order_pairs else None
        ),
    }


# ---------------------------------------------------------------------------
# Child-process extraction (runs in a spawned worker per document).
# ---------------------------------------------------------------------------
def _fake_document(key: str, original: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"bench-{key}",
        storage_path=str(original),
        stored_filename=Path(original).name,
        filename=Path(original).name,
    )


def _serialize_result(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_output", None)
    if hasattr(structured, "model_dump"):
        structured = structured.model_dump()
    return {
        "extracted_text": str(getattr(result, "extracted_text", "") or ""),
        "page_count": int(getattr(result, "page_count", 0) or 0),
        "confidence_score": float(getattr(result, "confidence_score", 0.0) or 0.0),
        "processing_time": float(getattr(result, "processing_time", 0.0) or 0.0),
        "structured_output": structured,
    }


def _extract_paddle_doc(doc: dict[str, Any]) -> dict[str, Any]:
    from modules.extraction.paddle import PaddleOCRExtractionService

    service = PaddleOCRExtractionService(
        language="en",
        render_scale=2.0,
        use_layout_analysis=False,
    )
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        result = service.extract(_fake_document(doc["key"], doc["original"]))
    return _serialize_result(result)


def _extract_surya_doc(doc: dict[str, Any]) -> dict[str, Any]:
    import fitz
    from PIL import Image
    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor

    manager = SuryaInferenceManager()
    rec = RecognitionPredictor(manager)
    images = []
    with fitz.open(doc["original"]) as pdf:
        for page in pdf:
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            images.append(
                Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            )
    predictions = rec(images)
    texts = []
    for prediction in predictions:
        if hasattr(prediction, "blocks"):
            texts.append(
                "\n".join(
                    str(block.get("html") or block.get("text") or "")
                    for block in prediction.blocks
                    if isinstance(block, dict)
                )
            )
        elif hasattr(prediction, "text_lines"):
            texts.append(
                "\n".join(str(line.text) for line in prediction.text_lines)
            )
        else:
            texts.append(str(prediction))
    return {
        "extracted_text": "\n\n".join(texts).strip(),
        "page_count": len(images),
        "confidence_score": 0.0,
        "processing_time": 0.0,
        "structured_output": {"engine": "SURYA"},
    }


def _extract_glm_doc(doc: dict[str, Any]) -> dict[str, Any]:
    if importlib.util.find_spec("glmocr") is not None:
        from glmocr import GlmOcr
    else:
        from glm_ocr import GlmOcr

    with GlmOcr() as parser:
        result = parser.parse(str(doc["original"]))
    text = getattr(result, "text", None) or str(result)
    return {
        "extracted_text": text,
        "page_count": 1,
        "confidence_score": 0.0,
        "processing_time": 0.0,
        "structured_output": {"engine": "GLM_OCR"},
    }


def _child_runner(engine_key: str, doc: dict[str, Any], queue: Any) -> None:
    """Worker entry point; runs in a spawned child process."""
    try:
        if engine_key == "paddleocr":
            out = _extract_paddle_doc(doc)
        elif engine_key == "surya":
            out = _extract_surya_doc(doc)
        else:
            out = _extract_glm_doc(doc)
        queue.put(("ok", out))
    except Exception as exc:  # noqa: BLE001
        queue.put(("error", f"{type(exc).__name__}: {exc}"))


def _run_document_in_worker(engine_key: str, doc: dict[str, Any]) -> dict[str, Any]:
    """Extract one document in a child process with a wall-clock timeout."""
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(target=_child_runner, args=(engine_key, doc, queue))
    start = time.perf_counter()
    proc.start()
    proc.join(timeout=DOC_TIMEOUT)
    elapsed = round(time.perf_counter() - start, 3)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=10)
        return {
            "status": "TIMEOUT",
            "elapsed_sec": elapsed,
            "reason": f"TIMEOUT after {DOC_TIMEOUT}s (per-document limit)",
        }

    try:
        status, payload = queue.get(timeout=10)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "ERROR",
            "elapsed_sec": elapsed,
            "reason": f"no worker result: {type(exc).__name__}: {exc}",
        }

    if status == "error":
        return {
            "status": "ERROR",
            "elapsed_sec": elapsed,
            "reason": payload,
        }
    return {"status": "OK", "elapsed_sec": elapsed, "data": payload}


# ---------------------------------------------------------------------------
# Engine runners (availability gates + per-document worker dispatch).
# ---------------------------------------------------------------------------
def run_paddleocr(documents: list[dict[str, Any]]) -> dict[str, Any]:
    if not _module_available("paddleocr"):
        return {
            "available": False,
            "reason": (
                "NOT_AVAILABLE - the 'paddleocr' package is not installed."
            ),
        }
    return _run_engine(
        engine_key="paddleocr",
        documents=documents,
        config={
            "service": "PaddleOCRExtractionService",
            "device": "cpu",
            "render_scale": 2.0,
            "use_layout_analysis": False,
            "per_document_timeout_sec": DOC_TIMEOUT,
            "note": (
                "PP-Structure layout models are not cached locally and model "
                "downloads are out of scope; coordinate-block fallback used."
            ),
        },
    )


def run_surya(documents: list[dict[str, Any]]) -> dict[str, Any]:
    if not _module_available("surya"):
        return {
            "available": False,
            "reason": (
                "NOT_AVAILABLE - the 'surya' package is not installed. "
                "Install 'surya-ocr' and provide a vllm (GPU) or llama.cpp "
                "(CPU/Apple) backend, then re-run this benchmark."
            ),
        }
    return _run_engine(
        engine_key="surya",
        documents=documents,
        config={"runtime": "vllm (GPU) or llama.cpp (CPU/Apple)"},
    )


def run_glm_ocr(documents: list[dict[str, Any]]) -> dict[str, Any]:
    if not (_module_available("glmocr") or _module_available("glm_ocr")):
        return {
            "available": False,
            "reason": (
                "NOT_AVAILABLE - the 'glmocr' package is not installed. "
                "Install 'glmocr' and provide a GPU (vLLM/SGLang) or the "
                "Zhipu MaaS endpoint, then re-run this benchmark."
            ),
        }
    return _run_engine(
        engine_key="glm_ocr",
        documents=documents,
        config={"runtime": "vLLM/SGLang GPU or Zhipu MaaS"},
    )


def _run_engine(
    engine_key: str,
    documents: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": True,
        "config": config,
        "documents": {},
    }
    total_pages = 0
    total_elapsed = 0.0
    cer_values: list[float] = []
    wer_values: list[float] = []
    table_scores: list[float] = []
    reading_order_values: list[float] = []
    bbox_coverage_values: list[float] = []

    for doc in documents:
        key = doc["key"]
        entry: dict[str, Any] = {
            "label": doc["label"],
            "pages_expected": doc["pages"],
        }
        worker = _run_document_in_worker(engine_key, doc)
        entry["status"] = worker["status"]
        entry["elapsed_sec"] = worker["elapsed_sec"]

        if worker["status"] != "OK":
            entry["reason"] = worker["reason"]
            result["documents"][key] = entry
            continue

        data = worker["data"]
        text = str(data.get("extracted_text", "") or "")
        page_count = int(data.get("page_count", 0) or 0)
        total_pages += page_count
        total_elapsed += worker["elapsed_sec"]
        entry.update(
            {
                "extracted_text": text,
                "page_count": page_count,
                "confidence_score": float(data.get("confidence_score", 0.0) or 0.0),
                "processing_time_sec": round(
                    float(data.get("processing_time", 0.0) or 0.0), 3
                ),
                "text_stats": text_stats(text),
            }
        )

        structured = data.get("structured_output")
        entry["structured_summary"] = summarize_structured(structured)
        entry["structured_output"] = structured

        # Ground-truth based text fidelity (native text layer docs only).
        native_gt = _native_ground_truth(doc["original"])
        if native_gt:
            entry["cer"] = round(calculate_cer(native_gt, text), 4)
            entry["wer"] = round(calculate_wer(native_gt, text), 4)
            cer_values.append(entry["cer"])
            wer_values.append(entry["wer"])
        else:
            entry["cer"] = None
            entry["wer"] = None

        table_score = entry["structured_summary"].get("table_score") or 0.0
        table_scores.append(table_score)

        reading_order = entry["structured_summary"].get("reading_order_score")
        if reading_order is not None:
            reading_order_values.append(reading_order)

        bbox_coverage = entry["structured_summary"].get("bbox_coverage")
        if bbox_coverage is not None:
            bbox_coverage_values.append(bbox_coverage)

        result["documents"][key] = entry

    result["aggregate"] = {
        "total_pages": total_pages,
        "total_extraction_elapsed_sec": round(total_elapsed, 3),
        "seconds_per_page": (
            round(total_elapsed / total_pages, 3) if total_pages else None
        ),
        "pages_per_second": (
            round(total_pages / total_elapsed, 3) if total_elapsed else None
        ),
        "cer_mean": round(sum(cer_values) / len(cer_values), 4) if cer_values else None,
        "wer_mean": round(sum(wer_values) / len(wer_values), 4) if wer_values else None,
        "table_score_mean": (
            round(sum(table_scores) / len(table_scores), 4) if table_scores else None
        ),
        "reading_order_mean": (
            round(sum(reading_order_values) / len(reading_order_values), 4)
            if reading_order_values
            else None
        ),
        "bbox_coverage_mean": (
            round(sum(bbox_coverage_values) / len(bbox_coverage_values), 4)
            if bbox_coverage_values
            else None
        ),
    }
    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_summary_row(engine: str, result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("available"):
        return {
            "engine": engine,
            "availability": "NOT_AVAILABLE",
            "reason": result.get("reason", ""),
        }
    agg = result.get("aggregate", {})
    return {
        "engine": engine,
        "availability": "AVAILABLE",
        "cer": agg.get("cer_mean"),
        "wer": agg.get("wer_mean"),
        "table_score": agg.get("table_score_mean"),
        "reading_order": agg.get("reading_order_mean"),
        "bbox_coverage": agg.get("bbox_coverage_mean"),
        "seconds_per_page": agg.get("seconds_per_page"),
        "pages_per_second": agg.get("pages_per_second"),
    }


def build_markdown(report: dict[str, Any]) -> str:
    rows = report["summary"]
    lines: list[str] = []
    lines.append("# OCR engine evaluation report")
    lines.append("")
    lines.append(f"- Generated: `{report['generated_at']}`")
    lines.append(
        "- Scope: isolated benchmark - no production code modified, no model downloads."
    )
    lines.append(
        "- Mode: OCR-only (no detection pipeline - no regex/presidio/medspacy/gliner/qwen)."
    )
    lines.append(
        f"- Per-document timeout: {DOC_TIMEOUT}s. Timed-out documents are marked "
        "TIMEOUT and skipped."
    )
    lines.append(
        "- Documents: "
        + ", ".join(f"{d['key']} ({d['pages']}p)" for d in SAMPLE_DOCUMENTS)
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| Engine | Availability | CER | WER | Table Score | Reading Order | "
        "BBox Coverage | Sec/Page | Pages/Sec |"
    )
    lines.append(
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    )
    for row in rows:
        if row["availability"] == "NOT_AVAILABLE":
            lines.append(
                f"| {row['engine']} | NOT_AVAILABLE | - | - | - | - | - | - | - |"
            )
        else:
            lines.append(
                f"| {row['engine']} | AVAILABLE | {_fmt(row['cer'])} | {_fmt(row['wer'])} "
                f"| {_fmt(row['table_score'])} | {_fmt(row['reading_order'])} "
                f"| {_fmt(row['bbox_coverage'])} "
                f"| {_fmt(row['seconds_per_page'])} | {_fmt(row['pages_per_second'])} |"
            )
    lines.append("")

    for engine, result in report["engines"].items():
        lines.append(f"## {engine}")
        lines.append("")
        if not result.get("available"):
            lines.append(f"- **Availability:** NOT_AVAILABLE")
            lines.append(f"- **Reason:** {result.get('reason')}")
            lines.append("")
            continue
        lines.append(f"- **Availability:** AVAILABLE")
        lines.append(f"- **Config:** {json.dumps(result.get('config', {}))}")
        agg = result.get("aggregate", {})
        lines.append(
            f"- **Aggregate:** sec/page={_fmt(agg.get('seconds_per_page'))} "
            f"pages/sec={_fmt(agg.get('pages_per_second'))} "
            f"CER={_fmt(agg.get('cer_mean'))} WER={_fmt(agg.get('wer_mean'))} "
            f"table_score={_fmt(agg.get('table_score_mean'))} "
            f"reading_order={_fmt(agg.get('reading_order_mean'))} "
            f"bbox_coverage={_fmt(agg.get('bbox_coverage_mean'))}"
        )
        lines.append("")

        lines.append(
            "| Doc | Pages | Chars | CER | WER | Blocks | Table blocks | "
            "Table rows | Cells | Avg cols | BBox cov | Read order | Sec | Status |"
        )
        lines.append(
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | "
            ":--- | :--- | :--- | :--- | :--- |"
        )
        for key, doc in result["documents"].items():
            if doc.get("status") != "OK":
                lines.append(
                    f"| {key} | - | - | - | - | - | - | - | - | - | - | "
                    f"{_fmt(doc.get('elapsed_sec'), 1)} | "
                    f"{doc.get('status')} ({doc.get('reason', '')}) |"
                )
                continue
            stats = doc.get("text_stats", {})
            structured = doc.get("structured_summary", {})
            lines.append(
                f"| {key} | {doc.get('page_count')} | {stats.get('chars', 0)} "
                f"| {_fmt(doc.get('cer'))} | {_fmt(doc.get('wer'))} "
                f"| {structured.get('total_blocks', 0)} "
                f"| {structured.get('table_blocks', 0)} "
                f"| {structured.get('table_rows', 0)} "
                f"| {structured.get('table_cells', 0)} "
                f"| {_fmt(structured.get('avg_columns_per_row'), 1)} "
                f"| {_fmt(structured.get('bbox_coverage'))} "
                f"| {_fmt(structured.get('reading_order_score'))} "
                f"| {_fmt(doc.get('elapsed_sec'), 1)} | {doc.get('status')} |"
            )
        lines.append("")

    lines.append("## Engine notes")
    lines.append("")
    notes = {
        "paddleocr": (
            "Baseline = current PaddleOCRExtractionService. Layout analysis "
            "(PP-Structure) disabled because its models are not cached and "
            "downloads are out of scope; coordinate-block fallback used. "
            "CPU-only (device=cpu, 4 threads)."
        ),
        "surya": (
            "Not installed -> NOT_AVAILABLE. No conclusion about Surya quality "
            "can be drawn from this run."
        ),
        "glm_ocr": (
            "Not installed -> NOT_AVAILABLE. No conclusion about GLM-OCR "
            "quality can be drawn from this run."
        ),
    }
    for engine, note in notes.items():
        lines.append(f"- **{engine}:** {note}")
    lines.append("")

    lines.append("## Best engine by metric")
    lines.append("")
    available = {
        engine: result
        for engine, result in report["engines"].items()
        if result.get("available")
    }
    if len(available) == 0:
        lines.append("No engine was available to run.")
    else:
        names = ", ".join(sorted(available))
        lines.append(
            f"- **Best engine for plain text:** {names} (only engine actually tested; "
            "Surya/GLM-OCR NOT_AVAILABLE)."
        )
        lines.append(
            f"- **Best engine for tables:** {names} (only engine actually tested; "
            "no comparative table data yet)."
        )
        lines.append(
            f"- **Processing time:** see Sec/Page above ({names}, CPU)."
        )
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append(
        "- Keep PaddleOCR as the baseline; do not replace it. PaddleOCR alone "
        "provides a CER/WER/table/reading-order/bbox baseline, but there is "
        "**no comparative evidence yet** for Surya or GLM-OCR."
    )
    lines.append(
        "- To make an evidence-based engine decision, install `surya-ocr` (+ a "
        "llama.cpp/vllm backend) and/or `glmocr`, then re-run this benchmark "
        "unmodified. Only adopt a new engine if its measured CER/WER, table "
        "score, reading order, and bbox coverage beat PaddleOCR on these same "
        "sample documents."
    )
    lines.append("")
    return "\n".join(lines)


def _print_summary(report: dict[str, Any]) -> None:
    """Print only: engine, document, page count, status, elapsed, reason."""
    for engine, result in report["engines"].items():
        if not result.get("available"):
            print(
                f"[{engine}] | status=NOT_AVAILABLE | "
                f"reason={result.get('reason', '')}"
            )
            continue
        for key, doc in result["documents"].items():
            print(
                f"[{engine}] document={key} | pages={doc.get('page_count', '-')} "
                f"| status={doc.get('status')} | elapsed={doc.get('elapsed_sec')}s "
                f"| reason={doc.get('reason', '')}"
            )
        agg = result.get("aggregate", {})
        print(
            f"[{engine}] summary | pages={agg.get('total_pages')} "
            f"| seconds_per_page={agg.get('seconds_per_page')} "
            f"| cer_mean={agg.get('cer_mean')} wer_mean={agg.get('wer_mean')} "
            f"| table_score_mean={agg.get('table_score_mean')}"
        )


def main() -> None:
    missing = [
        d["original"] for d in SAMPLE_DOCUMENTS if not Path(d["original"]).exists()
    ]
    if missing:
        raise SystemExit(f"Missing sample documents: {missing}")

    engines: dict[str, Any] = {
        "paddleocr": run_paddleocr(SAMPLE_DOCUMENTS),
        "surya": run_surya(SAMPLE_DOCUMENTS),
        "glm_ocr": run_glm_ocr(SAMPLE_DOCUMENTS),
    }

    report: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "per_document_timeout_sec": DOC_TIMEOUT,
        "engines": engines,
        "summary": [
            build_summary_row(engine, result)
            for engine, result in engines.items()
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(str(ENGINE_JSON), report)
    ENGINE_MD.write_text(build_markdown(report), encoding="utf-8")

    _print_summary(report)
    print("report_json=" + str(ENGINE_JSON))
    print("report_md=" + str(ENGINE_MD))


if __name__ == "__main__":
    main()