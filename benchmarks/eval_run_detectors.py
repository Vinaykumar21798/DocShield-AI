"""Run each detector independently on the full extracted text.

- Every detector receives the SAME text (full content.txt, page_number=1).
- No DetectionService, no masking, no known-entities, no cross-detector state.
- Raw detector output is captured BEFORE any downstream mapping/dedup/redaction.
- Real page numbers are derived from form-feed boundaries after the run.
- If a detector is unavailable, its reason is recorded instead of silently
  skipping it.

Usage:
    python -m benchmarks.eval_run_detectors   # or run from repo root
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eval_common import (  # noqa: E402
    CONTENT_PATH,
    PREDICTIONS_DIR,
    OUTPUT_DIR,
    asdict,
    load_content,
    page_boundaries,
    page_of,
    write_json,
)
from eval_detector_profiles import DETECTOR_PROFILES, availability_report  # noqa: E402


def main() -> None:
    text = load_content()
    boundaries = page_boundaries(text)

    availability = availability_report()
    write_json(
        f"{OUTPUT_DIR}/detector_availability.json",
        {
            "document": CONTENT_PATH,
            "text_length": len(text),
            "pages": len(boundaries),
            "detectors": availability,
        },
    )
    print("== detector availability ==")
    for key, info in availability.items():
        print(f"  {key:10s} available={info['available']!s:5s} mode={info['mode']}")

    for key, profile in DETECTOR_PROFILES.items():
        info = availability[key]
        meta = {
            "detector": key,
            "label": profile.label,
            "mode": info["mode"],
            "availability_error": info.get("error"),
            "input": CONTENT_PATH,
            "input_length": len(text),
            "page_number_passed": 1,
        }

        if not info["available"]:
            meta["error"] = info.get("error")
            meta["predictions"] = []
            write_json(f"{PREDICTIONS_DIR}/{key}.json", meta)
            print(f"[{key}] NOT RUN: {info.get('error')}")
            continue

        try:
            instance = profile.factory()
        except Exception as exc:
            meta["error"] = f"instantiation failed: {exc}"
            meta["predictions"] = []
            write_json(f"{PREDICTIONS_DIR}/{key}.json", meta)
            print(f"[{key}] INSTANTIATION FAILED: {exc}")
            continue

        start = time.perf_counter()
        try:
            raw = instance.detect(text, 1)
            elapsed = time.perf_counter() - start
        except Exception as exc:
            elapsed = time.perf_counter() - start
            meta["error"] = f"{type(exc).__name__}: {exc}"
            meta["elapsed_sec"] = round(elapsed, 3)
            meta["predictions"] = []
            write_json(f"{PREDICTIONS_DIR}/{key}.json", meta)
            print(f"[{key}] DETECT FAILED after {elapsed:.1f}s: {exc}")
            continue

        detections = []
        for entity in raw:
            item = asdict(entity)
            start_char = item.get("start_char")
            if isinstance(start_char, int):
                item["page_number"] = page_of(start_char, boundaries)
            detections.append(item)

        meta["elapsed_sec"] = round(elapsed, 3)
        meta["predictions"] = detections
        write_json(f"{PREDICTIONS_DIR}/{key}.json", meta)
        print(f"[{key}] done in {elapsed:.1f}s predictions={len(detections)}")

    print("\nRaw predictions written under", PREDICTIONS_DIR)


if __name__ == "__main__":
    main()
