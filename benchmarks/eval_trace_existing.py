"""Trace the previous report's entities back to raw per-detector output.

Goal: determine whether a suspicious existing detection originates in the
detector itself (same value+span+type in raw output), in a later
reclassification (value matches but type differs), or only appears in the
report (downstream artifact - validator/dedup/merge/overlap/safety-net).

Raw predictions come from benchmarks/output/detector_predictions/*.json
(produced by eval_run_detectors.py, before any downstream processing).

Usage:
    python -m benchmarks.eval_trace_existing
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eval_common import (  # noqa: E402
    REPORT_PATH,
    OUTPUT_DIR,
    PREDICTIONS_DIR,
    canonical_type_for,
    normalize_value,
    overlap_ratio,
    write_json,
)

SUSPICIOUS_VALUES = [
    "Social Security",
    "Spouse\t09/22/1980",
    "Noah Smith\tChild",
    "Cancer",
    "\u2022 Primary",
    "\u2022 Urgent",
    "\u2022 Outpatient",
    "\u2022 Diagnostic",
    "\u2022 Advanced",
    "\u2022 Durable",
    "\u2022 Home",
    "\u2022 Cosmetic",
    "\u2022 Services",
    "CT",
    "PET",
    "02/28/2022",
    "EXCLUSIONS",
    "Submit",
    "APPEALS",
    "GRIEVANCES",
    "First Level Appeal",
    "Privacy Practices",
    "the United States",
    "P.O. Box 45678",
    "8:00 AM",
    "XXX-XX-1357",
]


def _load_report() -> list[dict]:
    with open(REPORT_PATH, "r", encoding="utf-8") as handle:
        report = json.load(handle)
    entities = []
    for entity in report.get("entities", []):
        entities.append(
            {
                "entity_type": entity.get("entity_type"),
                "entity_value": entity.get("entity_value"),
                "detector_field": entity.get("detector"),
                "confidence_score": entity.get("confidence_score"),
                "page_number": int(entity.get("page_number") or 1),
                "start_char": int(entity.get("start_char") or 0),
                "end_char": int(entity.get("end_char") or 0),
            }
        )
    return entities


def _load_raw_predictions() -> dict[str, list[dict]]:
    raw: dict[str, list[dict]] = {}
    for path in sorted(Path(PREDICTIONS_DIR).glob("*.json")):
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        raw[path.stem] = payload.get("predictions", [])
    return raw


def _best_raw_match(
    report_entity: dict,
    raw: dict[str, list[dict]],
) -> tuple[dict | None, dict | None]:
    best = None
    best_score = 0.0
    for detector, predictions in raw.items():
        for prediction in predictions:
            if prediction.get("page_number") != report_entity["page_number"]:
                continue
            overlap = overlap_ratio(
                report_entity["start_char"],
                report_entity["end_char"],
                prediction.get("start_char") or 0,
                prediction.get("end_char") or 0,
            )
            value_eq = normalize_value(report_entity["entity_value"]) == normalize_value(
                prediction.get("entity_value")
            )
            type_eq = canonical_type_for(report_entity["entity_type"]) == canonical_type_for(
                prediction.get("entity_type")
            )
            if overlap < 0.5 and not value_eq:
                continue
            score = overlap + (1.0 if value_eq else 0.0) + (1.0 if type_eq else 0.0)
            if score > best_score:
                best_score = score
                best = {
                    "detector": detector,
                    "entity_type": prediction.get("entity_type"),
                    "entity_value": prediction.get("entity_value"),
                    "confidence_score": prediction.get("confidence_score"),
                    "start_char": prediction.get("start_char"),
                    "end_char": prediction.get("end_char"),
                    "overlap_ratio": round(overlap, 3),
                    "value_match": value_eq,
                    "type_match": type_eq,
                }
    return best, best_score


def _classify(best: dict | None) -> str:
    if best is None:
        return "downstream_artifact"
    if best["type_match"] and (best["value_match"] or best["overlap_ratio"] >= 0.5):
        return "detector_origin"
    if best["value_match"] and not best["type_match"]:
        return "reclass_origin"
    return "partial_span"


def main() -> None:
    report_entities = _load_report()
    raw = _load_raw_predictions()

    traced: list[dict] = []
    for entity in report_entities:
        best, _ = _best_raw_match(entity, raw)
        entry = {
            "report_entity": entity,
            "canonical_type": canonical_type_for(entity["entity_type"]),
            "suspicious": any(
                token in (entity.get("entity_value") or "")
                for token in SUSPICIOUS_VALUES
            ),
            "attribution": _classify(best),
            "matched_raw": best,
        }
        traced.append(entry)

    report_detector_names = sorted(
        {entry["report_entity"]["detector_field"] for entry in traced}
    )
    raw_detector_names = sorted(raw.keys())

    # Raw predictions that do not overlap any report entity (dropped downstream).
    dropped: list[dict] = []
    for detector, predictions in raw.items():
        for prediction in predictions:
            page = prediction.get("page_number")
            start = prediction.get("start_char") or 0
            end = prediction.get("end_char") or 0
            consumed = any(
                entry["report_entity"]["page_number"] == page
                and overlap_ratio(
                    start, end,
                    entry["report_entity"]["start_char"],
                    entry["report_entity"]["end_char"],
                ) >= 0.5
                for entry in traced
            )
            if not consumed:
                dropped.append(
                    {
                        "detector": detector,
                        "entity_type": prediction.get("entity_type"),
                        "entity_value": prediction.get("entity_value"),
                        "confidence_score": prediction.get("confidence_score"),
                        "page_number": page,
                        "start_char": start,
                        "end_char": end,
                    }
                )

    summary = {
        "report_entities_count": len(report_entities),
        "report_detector_field_values": report_detector_names,
        "raw_detector_keys": raw_detector_names,
        "attribution_counts": {},
        "suspicious_attribution_counts": {},
        "dropped_raw_predictions_count": len(dropped),
    }
    for entry in traced:
        key = entry["attribution"]
        summary["attribution_counts"][key] = summary["attribution_counts"].get(key, 0) + 1
        if entry["suspicious"]:
            skey = entry["attribution"]
            summary["suspicious_attribution_counts"][skey] = (
                summary["suspicious_attribution_counts"].get(skey, 0) + 1
            )

    payload = {
        "summary": summary,
        "traced": traced,
        "dropped_raw_predictions": dropped,
    }
    write_json(f"{OUTPUT_DIR}/detector_trace_report.json", payload)
    write_markdown(f"{OUTPUT_DIR}/detector_trace_report.md", payload)
    print("summary:", json.dumps(summary, indent=2))
    print("wrote", f"{OUTPUT_DIR}/detector_trace_report.json/.md")


def write_markdown(path: str, payload: dict) -> None:
    lines: list[str] = []
    lines.append("# Trace: previous report entities -> raw detector output")
    lines.append("")
    lines.append("| Attribution | All report entities | Suspicious only |")
    lines.append("| :--- | :--- | :--- |")
    counts = payload["summary"]["attribution_counts"]
    suspicious = payload["summary"]["suspicious_attribution_counts"]
    for key in ["detector_origin", "reclass_origin", "partial_span", "downstream_artifact"]:
        lines.append(
            f"| {key} | {counts.get(key, 0)} | {suspicious.get(key, 0)} |"
        )
    lines.append("")
    lines.append(f"Raw predictions dropped downstream: **{payload['summary']['dropped_raw_predictions_count']}**")
    lines.append("")

    lines.append("## Suspicious entities detail")
    lines.append("")
    for entry in payload["traced"]:
        if not entry["suspicious"]:
            continue
        entity = entry["report_entity"]
        best = entry["matched_raw"]
        lines.append(
            f"- **{entity['entity_value']!r}** "
            f"(report {entity['entity_type']}, p{entity['page_number']}, "
            f"detector_field={entity['detector_field']}) -> "
            f"**{entry['attribution']}**"
        )
        if best:
            lines.append(
                f"  - raw: {best['detector']} {best['entity_type']} "
                f"{best['entity_value']!r} conf={best['confidence_score']} "
                f"overlap={best['overlap_ratio']} value_match={best['value_match']} "
                f"type_match={best['type_match']}"
            )
        else:
            lines.append("  - raw: no match in any independent detector run")
    lines.append("")

    lines.append("## Dropped raw predictions (present raw, absent in report)")
    lines.append("")
    lines.append("| # | detector | raw type | value | page | conf |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for index, item in enumerate(payload["dropped_raw_predictions"], start=1):
        lines.append(
            f"| {index} | {item['detector']} | {item['entity_type']} "
            f"| `{item['entity_value']}` | {item['page_number']} | {item['confidence_score']} |"
        )
    lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


if __name__ == "__main__":
    main()