"""Core gold annotation set for the Insurance Policy Document.

Ground truth is defined by hand from the extracted text (the PDF is a
scanned image with no text layer; the OCR content.txt is the exact input
every detector receives). Types below are CANONICAL (see eval_common
CANONICAL_ALIASES) so per-detector labels map cleanly for scoring.

Entity offsets are NOT hardcoded: they are resolved against content.txt at
load time by locating each value inside its page slice (reading order),
so they stay correct if the document text is re-generated identically.
"""

from __future__ import annotations

import re
from typing import Any

from eval_common import load_content, page_boundaries, write_json

# (canonical_type, entity_value, page_number)
GOLD_CORE: list[tuple[str, str, int]] = [
    # ---- Page 1: policyholder + dependents + policy details ----
    ("POLICY_NUMBER", "HIP-2024-45871239", 1),
    ("PERSON", "Jane R. Smith", 1),
    ("DATE_OF_BIRTH", "04/18/1982", 1),
    ("SSN", "XXX-XX-7890", 1),
    ("ADDRESS", "123 Maple Avenue, Apt 4B", 1),
    ("LOCATION", "Westfield", 1),
    ("LOCATION", "MI", 1),
    ("ZIP_CODE", "48185", 1),
    ("US_PHONE_NUMBER", "(313) 555-7842", 1),
    ("EMAIL", "jsmith@emailexample.com", 1),
    ("ORGANIZATION", "Horizon Technologies Inc.", 1),
    ("GROUP_NUMBER", "HTI-24680", 1),
    ("PERSON", "Robert Smith", 1),
    ("DATE_OF_BIRTH", "09/22/1980", 1),
    ("SSN", "XXX-XX-2468", 1),
    ("PERSON", "Emma Smith", 1),
    ("DATE_OF_BIRTH", "06/12/2012", 1),
    ("SSN", "XXX-XX-3579", 1),
    ("PERSON", "Noah Smith", 1),
    ("DATE_OF_BIRTH", "11/04/2015", 1),
    ("SSN", "XXX-XX-1357", 1),
    ("DATE", "06/01/2024", 1),
    ("DATE", "05/31/2025", 1),
    # ---- Page 3: medical history ----
    ("DISEASE", "Hypertension", 3),
    ("DATE", "03/15/2019", 3),
    ("DISEASE", "Type 2 Diabetes", 3),
    ("DATE", "07/10/2021", 3),
    ("ALLERGY", "Seasonal allergies", 3),
    # ---- Page 4: medications, procedures, claims info ----
    ("ORGANIZATION", "HealthGuard Insurance Company", 4),
    ("MEDICATION", "Lisinopril", 4),
    ("DOSAGE", "10mg", 4),
    ("MEDICATION", "Metformin", 4),
    ("DOSAGE", "500mg", 4),
    ("MEDICATION", "Cetirizine", 4),
    ("DOSAGE", "10mg", 4),
    ("PROCEDURE", "Colonoscopy", 4),
    ("DATE", "10/12/2023", 4),
    ("PROCEDURE", "Right knee arthroscopy", 4),
    ("DATE", "02/28/2022", 4),
    # ---- Page 5: claims, appeals, plan administrator ----
    ("ADDRESS", "P.O. Box 45678", 5),
    ("LOCATION", "Grand Rapids", 5),
    ("LOCATION", "MI", 5),
    ("ZIP_CODE", "49501", 5),
    ("US_PHONE_NUMBER", "(800) 555-2468", 5),
    ("US_PHONE_NUMBER", "(800) 555-3579", 5),
    ("URL", "www.healthguardinsurance.com/claims", 5),
    ("ORGANIZATION", "HealthGuard Insurance Company", 5),
    ("ADDRESS", "P.O. Box 87654", 5),
    ("LOCATION", "Grand Rapids", 5),
    ("LOCATION", "MI", 5),
    ("ZIP_CODE", "49501", 5),
    ("US_PHONE_NUMBER", "(800) 555-9876", 5),
    ("US_PHONE_NUMBER", "(800) 555-8765", 5),
    ("URL", "www.healthguardinsurance.com/appeals", 5),
    ("ORGANIZATION", "HealthGuard Insurance Company", 5),
    ("ADDRESS", "789 Insurance Avenue", 5),
    ("LOCATION", "Grand Rapids", 5),
    ("LOCATION", "MI", 5),
    ("ZIP_CODE", "49503", 5),
    ("US_PHONE_NUMBER", "(800) 555-1234", 5),
    ("URL", "www.healthguardinsurance.com", 5),
    ("URL", "www.healthguardinsurance.com/privacy", 5),
    ("US_PHONE_NUMBER", "(800) 555-1234", 5),
    # ---- Page 5: privacy notice mentions of the insurer ----
    ("ORGANIZATION", "HealthGuard Insurance Company", 5),
    # ---- Page 6: representative + signature date ----
    ("PERSON", "Michael J. Williams", 6),
    ("DATE", "06/01/2024", 6),
]


def _search_pattern(value: str) -> re.Pattern:
    pattern = re.escape(value)
    if value and value[0].isalnum():
        pattern = r"(?<!\w)" + pattern
    if value and value[-1].isalnum():
        pattern = pattern + r"(?!\w)"
    return re.compile(pattern)


def resolve_gold(text: str | None = None) -> list[dict[str, Any]]:
    """Return gold annotations with resolved start/end offsets and page."""
    if text is None:
        text = load_content()
    boundaries = page_boundaries(text)
    pages_by_number = {
        page_number: (start, end)
        for page_number, start, end in boundaries
    }

    gold: list[dict[str, Any]] = []
    for canonical_type, value, page in GOLD_CORE:
        start, end = pages_by_number[page]
        page_text = text[start:end]
        used = {
            (g["start_char"], g["end_char"])
            for g in gold
            if g["page_number"] == page
            and g["start_char"] is not None
            and g["end_char"] is not None
        }

        span = _locate_span(page_text, value, start, used)
        if span is None:
            gold.append(
                {
                    "entity_type": canonical_type,
                    "entity_value": value,
                    "start_char": None,
                    "end_char": None,
                    "page_number": page,
                    "resolved": False,
                }
            )
            continue

        gold.append(
            {
                "entity_type": canonical_type,
                "entity_value": value,
                "start_char": span[0],
                "end_char": span[1],
                "page_number": page,
                "resolved": True,
            }
        )

    return gold


def _locate_span(
    page_text: str,
    value: str,
    page_start: int,
    used: set[tuple[int, int]],
) -> tuple[int, int] | None:
    pattern = _search_pattern(value)
    for match in pattern.finditer(page_text):
        start = page_start + match.start()
        end = page_start + match.end()
        if any(
            start < used_end and end > used_start
            for used_start, used_end in used
        ):
            continue
        return start, end
    return None


def write_gold(output_path: str = "benchmarks/output/gold_annotations.json") -> list[dict[str, Any]]:
    gold = resolve_gold()
    write_json(
        output_path,
        {
            "source": "manual review of extracted/content.txt (OCR of scanned PDF)",
            "page_separator": "\\n\\n\\f\\n\\n",
            "count": len(gold),
            "annotations": gold,
        },
    )
    return gold


if __name__ == "__main__":
    resolved = write_gold()
    print(f"gold annotations: {len(resolved)}")
    unresolved = [g for g in resolved if not g["resolved"]]
    if unresolved:
        print("UNRESOLVED:")
        for item in unresolved:
            print("  ", item["entity_type"], repr(item["entity_value"]), "page", item["page_number"])
