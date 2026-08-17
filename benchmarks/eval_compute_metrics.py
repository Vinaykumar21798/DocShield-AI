"""Compute per-detector metrics against the manual gold set.

Reuses modules/detection/metrics.py:evaluate_predictions unchanged.
Detector raw types are mapped to the shared gold vocabulary ONLY for
scoring (canonical_type); raw types are preserved on every error row.

Usage:
    python -m benchmarks.eval_compute_metrics
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eval_common import (  # noqa: E402
    CONTENT_PATH,
    OUTPUT_DIR,
    PREDICTIONS_DIR,
    canonical_type_for,
    load_content,
    write_json,
)
from eval_gold_annotations import resolve_gold  # noqa: E402
from modules.detection.metrics import evaluate_predictions  # noqa: E402

THRESHOLDS = {"all": 0.0, "high_0.80": 0.80}


def _load_predictions(detector: str) -> dict:
    path = Path(f"{PREDICTIONS_DIR}/{detector}.json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _scored_predictions(predictions: list[dict]) -> list[dict]:
    scored = []
    for prediction in predictions:
        item = dict(prediction)
        item["canonical_type"] = canonical_type_for(item.get("entity_type", ""))
        scored.append(item)
    return scored


def _build_detector_report(detector: str, text: str, gold: list[dict]) -> dict:
    payload = _load_predictions(detector)
    predictions = payload.get("predictions", [])
    scored = _scored_predictions(predictions)

    report: dict = {
        "detector": detector,
        "label": payload.get("label", detector),
        "mode": payload.get("mode"),
        "availability_error": payload.get("availability_error"),
        "run_error": payload.get("error"),
        "elapsed_sec": payload.get("elapsed_sec"),
        "predictions_count": len(scored),
        "thresholds": {},
    }

    for threshold_name, threshold in THRESHOLDS.items():
        metrics = evaluate_predictions(
            predictions=scored,
            ground_truth=gold,
            source_text=text,
            confidence_threshold=threshold,
            min_overlap_ratio=0.5,
        )
        report["thresholds"][threshold_name] = metrics.to_dict()

    return report


def _fmt_fp(item: dict) -> dict:
    return {
        "value": item.get("entity_value"),
        "raw_type": item.get("entity_type"),
        "canonical_type": item.get("canonical_type"),
        "page": item.get("page_number"),
        "confidence": item.get("confidence_score"),
        "start_char": item.get("start_char"),
        "end_char": item.get("end_char"),
    }


def _fmt_fn(item: dict) -> dict:
    return {
        "value": item.get("entity_value"),
        "type": item.get("entity_type"),
        "page": item.get("page_number"),
        "start_char": item.get("start_char"),
        "end_char": item.get("end_char"),
    }


def main() -> None:
    text = load_content()
    gold = resolve_gold(text)
    print(f"gold annotations: {len(gold)}")

    detector_order = ["regex", "presidio", "medspacy", "gliner", "qwen"]
    full_report: dict = {"gold_count": len(gold), "detectors": {}}

    for detector in detector_order:
        try:
            report = _build_detector_report(detector, text, gold)
        except FileNotFoundError:
            print(f"[{detector}] no predictions file; skipping")
            continue

        full_report["detectors"][detector] = report

        metrics = report["thresholds"]["all"]
        summary = report["thresholds"]["all"]
        print(
            f"[{detector}] preds={report['predictions_count']} "
            f"TP={summary['global']['true_positives']} "
            f"FP={summary['global']['false_positives']} "
            f"FN={summary['global']['false_negatives']} "
            f"P={summary['global']['precision']:.3f} "
            f"R={summary['global']['recall']:.3f} "
            f"F1={summary['global']['f1_score']:.3f}"
        )

    write_json(f"{OUTPUT_DIR}/detector_eval_report.json", full_report)
    write_markdown(f"{OUTPUT_DIR}/detector_eval_report.md", full_report)
    print("wrote", f"{OUTPUT_DIR}/detector_eval_report.json/.md")


def write_markdown(path: str, report: dict) -> None:
    lines: list[str] = []
    lines.append("# Isolated per-detector evaluation report")
    lines.append("")
    lines.append(f"- Gold annotations: **{report['gold_count']}** (manual, from content.txt)")
    lines.append(f"- Source text: `{CONTENT_PATH}`")
    lines.append("")

    for detector, det in report["detectors"].items():
        lines.append(f"## {det.get('label', detector)}")
        lines.append("")
        lines.append(f"- Mode: `{det.get('mode')}` | predictions: {det['predictions_count']}")
        lines.append(f"- Availability error: {det.get('availability_error')}")
        lines.append(f"- Run error: {det.get('run_error')}")
        lines.append("")

        all_t = det["thresholds"]["all"]["global"]
        high_t = det["thresholds"]["high_0.80"]["global"]
        lines.append("| Metric | All conf | >= 0.80 |")
        lines.append("| :--- | :--- | :--- |")
        lines.append(f"| True positives | {all_t['true_positives']} | {high_t['true_positives']} |")
        lines.append(f"| False positives | {all_t['false_positives']} | {high_t['false_positives']} |")
        lines.append(f"| False negatives | {all_t['false_negatives']} | {high_t['false_negatives']} |")
        lines.append(f"| Precision | {all_t['precision']:.3f} | {high_t['precision']:.3f} |")
        lines.append(f"| Recall | {all_t['recall']:.3f} | {high_t['recall']:.3f} |")
        lines.append(f"| F1 | {all_t['f1_score']:.3f} | {high_t['f1_score']:.3f} |")
        lines.append("")

        fns = det["thresholds"]["all"]["false_negative_annotations"]
        fns_sorted = sorted(
            fns, key=lambda item: (item.get("page_number") or 1, item.get("start_char") or 0)
        )
        lines.append(f"### False negatives ({len(fns)})")
        lines.append("")
        lines.append("| # | value | type | page |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for index, item in enumerate(fns_sorted, start=1):
            lines.append(f"| {index} | `{item.get('entity_value')}` | {item.get('entity_type')} | {item.get('page_number')} |")
        lines.append("")

        fps = det["thresholds"]["all"]["false_positive_predictions"]
        fps_sorted = sorted(
            fps, key=lambda item: (item.get("page_number") or 1, item.get("start_char") or 0)
        )
        lines.append(f"### False positives ({len(fps)})")
        lines.append("")
        lines.append("| # | value | raw type | canonical | page | conf |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for index, item in enumerate(fps_sorted, start=1):
            lines.append(
                f"| {index} | `{item.get('entity_value')}` | {item.get('entity_type')} "
                f"| {item.get('canonical_type')} | {item.get('page_number')} "
                f"| {item.get('confidence_score')} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


if __name__ == "__main__":
    main()
