import re
from dataclasses import dataclass, field
from typing import Any

from modules.detection.mask_manager import MaskManager
from modules.detection.models.detection_result import DetectionResult

CANDIDATE_LABEL_WORDS = {
    "account",
    "address",
    "aadhaar",
    "age",
    "allergy",
    "claim",
    "clinical",
    "consultant",
    "contact",
    "date",
    "diagnosis",
    "doctor",
    "dob",
    "email",
    "employee",
    "holder",
    "hospital",
    "ifsc",
    "insurance",
    "lab",
    "medical",
    "medication",
    "mobile",
    "mrn",
    "name",
    "pan",
    "passport",
    "patient",
    "phone",
    "policy",
    "procedure",
    "provider",
    "ssn",
    "agreement",
    "authorized",
    "customer",
    "driving",
    "emergency",
    "gstin",
    "invoice",
    "license",
    "organization",
    "salary",
    "signatory",
    "witness",
    "upi",
}

CANDIDATE_SIGNAL_WORDS = {
    "admission",
    "allergy",
    "asthma",
    "biopsy",
    "clinic",
    "clinical",
    "diabetes",
    "diagnosis",
    "fever",
    "glucose",
    "hospital",
    "hypertension",
    "laboratory",
    "medication",
    "metformin",
    "mri",
    "pain",
    "paracetamol",
    "physician",
    "procedure",
    "symptom",
    "treatment",
}

CANDIDATE_IGNORED_VALUES = {
    "company information",
    "contact information",
    "enterprise service agreement",
    "footer",
    "legal section",
    "medical information",
}

ORG_OR_FACILITY_SUFFIXES = (
    "Association",
    "Clinic",
    "Company",
    "Corp",
    "Corporation",
    "Group",
    "Hospital",
    "Inc",
    "LLC",
    "Ltd",
    "Medical Center",
)

STRUCTURED_TOKEN_PATTERN = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.\w+\b"
    r"|\b(?:\+?\d[\d\s().-]{5,}\d)\b"
    r"|\b[A-Z]{5}\d{4}[A-Z]\b"
    r"|\b[A-Z]{2,}\d[A-Z0-9-]{3,}\b"
    r"|\b\d{3}-\d{2}-\d{4}\b"
    r"|\b\d{2,4}[-/]\d{1,2}[-/]\d{1,4}\b"
)

PROPER_NOUN_PATTERN = re.compile(
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}\b"
)

TITLE_NAME_PATTERN = re.compile(
    r"\b(?:Dr|Mr|Mrs|Ms|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
)

ORG_OR_FACILITY_PATTERN = re.compile(
    r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,5}\s+(?:"
    + "|".join(re.escape(suffix) for suffix in ORG_OR_FACILITY_SUFFIXES)
    + r")\b"
)


@dataclass
class PipelineState:
    """
    Maintains the state of the sequential detection pipeline.

    Responsibilities:
    - Store the original document text.
    - Track all detected entities.
    - Manage masked regions through MaskManager.
    """

    original_text: str

    resolved_entities: list[DetectionResult] = field(default_factory=list)
    executed_detectors: list[str] = field(default_factory=list)
    skipped_detectors: list[str] = field(default_factory=list)
    execution_time: dict[str, float] = field(default_factory=dict)
    detection_history: list[dict] = field(default_factory=list)
    confidence_summary: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.mask_manager = MaskManager(self.original_text)

    def add_entities(
        self,
        entities: list[DetectionResult],
        detector_name: str = "Unknown",
        mask_confidence_threshold: float | None = None,
    ) -> None:
        """
        Add newly detected entities to the pipeline.
        """

        if not entities:
            # Still record that the detector was executed and found nothing
            if detector_name not in self.executed_detectors:
                self.executed_detectors.append(detector_name)
            self.detection_history.append({"step": detector_name, "count": 0})
            return

        self.resolved_entities.extend(entities)

        if mask_confidence_threshold is not None:
            maskable = [
                e for e in entities
                if e.confidence_score >= mask_confidence_threshold
            ]
            self.mask_manager.add_entities(maskable)
        else:
            self.mask_manager.add_entities(entities)

        if detector_name not in self.executed_detectors:
            self.executed_detectors.append(detector_name)
        self.detection_history.append({"step": detector_name, "count": len(entities)})

    def log_skipped(self, detector_name: str) -> None:
        """Logs a skipped detector."""
        if detector_name not in self.skipped_detectors:
            self.skipped_detectors.append(detector_name)

    def log_time(self, detector_name: str, duration: float) -> None:
        """Logs execution latency in milliseconds."""
        self.execution_time[detector_name] = round(duration * 1000.0, 2)

    def is_span_unmasked(
        self,
        start: int,
        end: int,
    ) -> bool:
        """
        Returns True when a detector result belongs entirely to text that has
        not already been claimed by a previous detector.
        """
        if start < 0 or end > len(self.mask_manager.mask) or start >= end:
            return False

        return not any(self.mask_manager.mask[start:end])

    def remaining_candidate_summary(
        self,
        min_chars: int = 3,
        preview_limit: int = 5,
    ) -> dict[str, Any]:
        """
        Recalculates a lightweight summary of unmasked entity candidates.

        This is a routing heuristic, not duplicate detector logic. It identifies
        residual spans with entity-like structure or domain signals so the
        orchestrator can stop on candidates instead of raw leftover text.
        """
        candidates: list[dict[str, Any]] = []

        for match in re.finditer(r"[^\r\n]+", self.current_text):
            line = match.group()
            line_start = match.start()
            self._extend_line_candidates(
                candidates,
                line,
                line_start,
                min_chars,
            )

        candidates = self._dedupe_candidate_spans(candidates)
        return {
            "count": len(candidates),
            "preview": [
                candidate["text"]
                for candidate in candidates[:preview_limit]
            ],
            "total_chars": sum(
                candidate["end"] - candidate["start"]
                for candidate in candidates
            ),
            "candidates": candidates,
        }

    def candidate_contexts(
        self,
        candidates: list[dict[str, Any]],
        window: int,
        max_contexts: int,
    ) -> list[dict[str, Any]]:
        contexts: list[dict[str, Any]] = []
        seen_ranges = set()

        for candidate in candidates[:max_contexts]:
            start, end = self._bounded_context_bounds(
                len(self.original_text),
                candidate["start"],
                candidate["end"],
                window,
            )
            raw_text = self.current_text[start:end]
            leading = len(raw_text) - len(raw_text.lstrip())
            trailing = len(raw_text.rstrip())
            context_start = start + leading
            context_end = start + trailing
            if context_start >= context_end:
                continue

            key = (context_start, context_end)
            if key in seen_ranges:
                continue
            seen_ranges.add(key)
            contexts.append(
                {
                    "start": context_start,
                    "end": context_end,
                    "text": self.current_text[context_start:context_end],
                    "candidate": candidate,
                }
            )

        return contexts

    def _extend_line_candidates(
        self,
        candidates: list[dict[str, Any]],
        line: str,
        line_start: int,
        min_chars: int,
    ) -> None:
        label_match = re.match(
            r"^\s*([A-Za-z][A-Za-z ]{1,35})\s*[:\-]\s*(.+?)\s*$",
            line,
        )
        if label_match and self._looks_like_label(label_match.group(1)):
            self._add_candidate(
                candidates,
                line_start + label_match.start(2),
                line_start + label_match.end(2),
                "label_value",
                min_chars,
            )

        for pattern, kind in (
            (STRUCTURED_TOKEN_PATTERN, "structured_token"),
            (TITLE_NAME_PATTERN, "titled_name"),
            (ORG_OR_FACILITY_PATTERN, "organization_or_facility"),
            (PROPER_NOUN_PATTERN, "proper_noun"),
        ):
            for match in pattern.finditer(line):
                self._add_candidate(
                    candidates,
                    line_start + match.start(),
                    line_start + match.end(),
                    kind,
                    min_chars,
                )

        for word_match in re.finditer(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", line):
            value = word_match.group().lower()
            if value not in CANDIDATE_SIGNAL_WORDS:
                continue
            self._add_candidate(
                candidates,
                line_start + word_match.start(),
                line_start + word_match.end(),
                "domain_signal",
                min_chars,
            )

    def _add_candidate(
        self,
        candidates: list[dict[str, Any]],
        start: int,
        end: int,
        kind: str,
        min_chars: int,
    ) -> None:
        if start < 0 or end > len(self.original_text) or start >= end:
            return
        if not self.is_span_unmasked(start, end):
            return

        candidate_text = " ".join(self.current_text[start:end].split())
        if not candidate_text:
            return
        if kind == "label_value":
            if not self._is_meaningful_label_value(candidate_text, min_chars):
                return
        elif not self._is_meaningful_candidate(candidate_text, min_chars):
            return

        candidates.append(
            {
                "start": start,
                "end": end,
                "text": candidate_text[:80],
                "kind": kind,
            }
        )

    @staticmethod
    def _looks_like_label(label: str) -> bool:
        words = {
            word.lower()
            for word in re.findall(r"[A-Za-z]+", label)
        }
        return not words.isdisjoint(CANDIDATE_LABEL_WORDS)

    @staticmethod
    def _is_meaningful_label_value(
        segment: str,
        min_chars: int,
    ) -> bool:
        normalized_segment = " ".join(segment.strip().lower().split())
        if normalized_segment in CANDIDATE_IGNORED_VALUES:
            return False

        tokens = re.findall(r"[A-Za-z0-9@._#:/+-]+", segment)
        normalized_tokens = []
        for token in tokens:
            normalized = token.strip("._#:/+-").lower()
            if normalized and normalized not in CANDIDATE_LABEL_WORDS:
                normalized_tokens.append(normalized)

        if not normalized_tokens:
            return False

        alpha_chars = sum(
            len(re.sub(r"[^a-z]", "", token))
            for token in normalized_tokens
        )
        digit_chars = sum(
            len(re.sub(r"\D", "", token))
            for token in normalized_tokens
        )
        return alpha_chars >= min_chars or digit_chars >= min_chars
    @staticmethod
    def _is_meaningful_candidate(
        segment: str,
        min_chars: int,
    ) -> bool:
        normalized_segment = " ".join(segment.strip().lower().split())
        if normalized_segment in CANDIDATE_IGNORED_VALUES:
            return False

        tokens = re.findall(r"[A-Za-z0-9@._#:/+-]+", segment)
        if not tokens:
            return False

        normalized_tokens = []
        for token in tokens:
            normalized = token.strip("._#:/+-").lower()
            if not normalized:
                continue
            if normalized in CANDIDATE_LABEL_WORDS:
                continue
            normalized_tokens.append(normalized)

        if not normalized_tokens:
            return False

        alpha_chars = sum(
            len(re.sub(r"[^a-z]", "", token))
            for token in normalized_tokens
        )
        digit_chars = sum(
            len(re.sub(r"\D", "", token))
            for token in normalized_tokens
        )

        has_entity_signal = any(
            token in CANDIDATE_SIGNAL_WORDS
            or "@" in token
            or any(char.isdigit() for char in token)
            for token in normalized_tokens
        )
        has_multi_word_value = len(normalized_tokens) >= 2 and alpha_chars >= min_chars

        return (
            alpha_chars >= min_chars and has_entity_signal
        ) or digit_chars >= min_chars or has_multi_word_value

    @staticmethod
    def _dedupe_candidate_spans(
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        candidates.sort(
            key=lambda candidate: (
                candidate["start"],
                -(candidate["end"] - candidate["start"]),
            )
        )
        accepted: list[dict[str, Any]] = []
        seen = set()

        for candidate in candidates:
            key = (
                candidate["start"],
                candidate["end"],
                candidate["kind"],
            )
            if key in seen:
                continue
            seen.add(key)

            overlaps_existing = False
            for existing in accepted:
                if (
                    candidate["start"] >= existing["start"]
                    and candidate["end"] <= existing["end"]
                ):
                    overlaps_existing = True
                    break
            if overlaps_existing:
                continue

            accepted.append(candidate)

        return accepted

    @staticmethod
    def _bounded_context_bounds(
        text_length: int,
        start: int,
        end: int,
        window: int,
    ) -> tuple[int, int]:
        entity_length = max(1, end - start)
        max_context_chars = min(
            text_length,
            entity_length + (2 * max(0, window)),
        )
        if text_length > entity_length and max_context_chars >= text_length:
            max_context_chars = max(entity_length, text_length - 1)

        center = (start + end) // 2
        context_start = max(0, center - (max_context_chars // 2))
        context_end = min(text_length, context_start + max_context_chars)
        context_start = max(0, context_end - max_context_chars)
        return context_start, context_end

    def finalize_confidence_summary(self) -> None:
        """Calculates count of entities per confidence level."""
        summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for entity in self.resolved_entities:
            lvl = entity.metadata.get("confidence_level", "HIGH")
            if lvl in summary:
                summary[lvl] += 1
        self.confidence_summary = summary

    @property
    def current_text(self) -> str:
        """
        Returns the remaining (masked) text for the next detector.
        """

        return self.mask_manager.remaining_text()

    @property
    def has_remaining_text(self) -> bool:
        """
        Returns True if unresolved text still exists.
        """

        return self.mask_manager.has_remaining_text()
