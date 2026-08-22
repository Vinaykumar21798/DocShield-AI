import re
from dataclasses import dataclass, field
from typing import Any

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
    "physician",
    "policy",
    "procedure",
    "provider",
    "ssn",
    "agreement",
    "amount",
    "authorized",
    "billed",
    "customer",
    "driving",
    "emergency",
    "gstin",
    "id",
    "invoice",
    "license",
    "number",
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
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}\b"
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
    - Track unmasked spans directly via entity intervals.
    """

    original_text: str

    locked_spans: list[dict[str, Any]] = field(default_factory=list)
    resolved_entities: list[DetectionResult] = field(default_factory=list)
    pending_candidates: list[DetectionResult] = field(default_factory=list)
    executed_detectors: list[str] = field(default_factory=list)
    skipped_detectors: list[str] = field(default_factory=list)
    execution_time: dict[str, float] = field(default_factory=dict)
    detection_history: list[dict] = field(default_factory=list)
    confidence_summary: dict[str, int] = field(default_factory=dict)
    routing_audit: list[dict] = field(default_factory=list)
    llm_candidate_audit: dict[str, list[dict]] = field(default_factory=lambda: {
        "accepted": [],
        "rejected": [],
    })
    pipeline_metrics: dict[str, Any] = field(default_factory=lambda: {
        "total_detector_candidates": 0,
        "high_confidence_locked": 0,
        "duplicate_suppressed": 0,
        "pre_llm_rejected": 0,
        "sent_to_llm_validation": 0,
        "llm_confirmed": 0,
        "llm_reclassified": 0,
        "llm_rejected": 0,
        "llm_residual_entities": 0,
        "detector_breakdown": {},
    })

    @property
    def current_text(self) -> str:
        """Returns the current text where high-confidence resolved entities are masked."""
        if not self.resolved_entities:
            return self.original_text
        chars = list(self.original_text)
        for entity in self.resolved_entities:
            if entity.confidence_score >= 0.80:
                for idx in range(max(0, entity.start_char), min(len(chars), entity.end_char)):
                    chars[idx] = " "
        return "".join(chars)

    def lock_span(
        self,
        entity: DetectionResult,
        reason: str = "Authoritative high-confidence detection",
        document_id: str | None = None,
    ) -> None:
        """
        Registers an authoritative high-confidence locked span in document-global coordinates.
        Protects the exact character interval from redundant detection while keeping context untouched.
        """
        for locked in self.locked_spans:
            if (
                locked.get("page_number", 1) == getattr(entity, "page_number", 1)
                and locked["start_char"] == entity.start_char
                and locked["end_char"] == entity.end_char
            ):
                det = getattr(entity, "detector", "Unknown")
                if det not in locked.get("duplicate_sources", []):
                    locked.setdefault("duplicate_sources", []).append(det)
                locked["confidence"] = max(locked["confidence"], entity.confidence_score)
                return

        span_entry = {
            "document_id": document_id or getattr(self, "document_id", "doc"),
            "page_number": getattr(entity, "page_number", 1),
            "start_char": entity.start_char,
            "end_char": entity.end_char,
            "entity_value": entity.entity_value,
            "entity_type": entity.entity_type,
            "confidence": round(float(entity.confidence_score), 3),
            "detector": getattr(entity, "detector", "Unknown"),
            "status": "LOCKED",
            "reason": reason,
            "duplicate_sources": [getattr(entity, "detector", "Unknown")],
        }
        self.locked_spans.append(span_entry)

    def is_span_locked(
        self,
        start_char: int,
        end_char: int,
        page_number: int = 1,
    ) -> bool:
        """
        Checks whether the interval [start_char, end_char] overlaps any authoritative locked span.
        Uses exact interval overlap logic: max(start_char, locked_start) < min(end_char, locked_end).
        """
        for locked in self.locked_spans:
            if locked.get("page_number", 1) == page_number:
                if max(start_char, locked["start_char"]) < min(end_char, locked["end_char"]):
                    return True
        return False

    def get_overlapping_locked_span(
        self,
        start_char: int,
        end_char: int,
        page_number: int = 1,
    ) -> dict[str, Any] | None:
        """
        Returns the locked span record that overlaps with [start_char, end_char], or None if no overlap.
        """
        for locked in self.locked_spans:
            if locked.get("page_number", 1) == page_number:
                if max(start_char, locked["start_char"]) < min(end_char, locked["end_char"]):
                    return locked
        return None

    def prune_pending_candidates(self) -> None:
        """
        Removes any candidate from pending_candidates whose span has now been claimed
        by an authoritative locked high-confidence entity.
        """
        self.pending_candidates = [
            c for c in self.pending_candidates
            if not self.is_span_locked(c.start_char, c.end_char, getattr(c, "page_number", 1))
            and self.is_span_unmasked(c.start_char, c.end_char, min_confidence=0.80)
        ]

    def record_llm_candidate(
        self,
        candidate_value: str,
        entity_type: str,
        decision: str,
        confidence: float,
        reasoning: str,
        start_char: int,
        end_char: int,
        detector: str = "Gemma",
        original_type: str | None = None,
        page_number: int = 1,
    ) -> None:
        """Records an LLM validation/discovery candidate decision with explicit reasoning for UI display."""
        entry = {
            "entity_value": candidate_value,
            "entity_type": entity_type,
            "original_type": original_type or entity_type,
            "decision": decision,
            "confidence": round(float(confidence), 3),
            "reasoning": reasoning,
            "start_char": start_char,
            "end_char": end_char,
            "detector": detector,
            "page_number": page_number,
        }
        if decision in {"CONFIRM", "RECLASSIFY", "ACCEPT"}:
            self.llm_candidate_audit["accepted"].append(entry)
        else:
            self.llm_candidate_audit["rejected"].append(entry)

    def log_candidate_routing(
        self,
        candidate: DetectionResult,
        decision: str,
        reason: str,
        detector_name: str | None = None,
        semantic_score: float = 0.0,
        structural_score: float = 0.0,
    ) -> None:
        """Logs the lifecycle and routing decision for a candidate detection result."""
        det = detector_name or getattr(candidate, "detector", "Unknown")
        audit_entry = {
            "value": candidate.entity_value,
            "entity_type": candidate.entity_type,
            "detector": det,
            "confidence": round(float(candidate.confidence_score), 3),
            "span": (candidate.start_char, candidate.end_char),
            "decision": decision,
            "reason": reason,
            "semantic_score": round(float(semantic_score), 3),
            "structural_score": round(float(structural_score), 3),
        }
        self.routing_audit.append(audit_entry)

        # Update metrics
        self.pipeline_metrics["total_detector_candidates"] += 1
        det_stats = self.pipeline_metrics["detector_breakdown"].setdefault(
            det, {"candidates": 0, "locked": 0, "duplicates_suppressed": 0, "pre_llm_rejected": 0, "pending_for_llm": 0}
        )
        det_stats["candidates"] += 1

        if decision == "LOCKED":
            self.pipeline_metrics["high_confidence_locked"] += 1
            det_stats["locked"] += 1
        elif decision in {"DUPLICATE_SUPPRESSED", "OVERLAP_SUPPRESSED"}:
            self.pipeline_metrics["duplicate_suppressed"] += 1
            det_stats["duplicates_suppressed"] += 1
        elif decision == "PRE_LLM_REJECT":
            self.pipeline_metrics["pre_llm_rejected"] += 1
            det_stats["pre_llm_rejected"] += 1
        elif decision == "PENDING_FOR_LLM":
            self.pipeline_metrics["sent_to_llm_validation"] += 1
            det_stats["pending_for_llm"] += 1

    def add_entities(
        self,
        entities: list[DetectionResult],
        detector_name: str = "Unknown",
        mask_confidence_threshold: float | None = None,
    ) -> None:
        """
        Add newly detected entities to the pipeline.
        Updates locked spans for high-confidence detections and prunes pending candidates.
        """
        threshold = mask_confidence_threshold if mask_confidence_threshold is not None else 0.80

        if not entities:
            # Still record that the detector was executed and found nothing
            if detector_name not in self.executed_detectors:
                self.executed_detectors.append(detector_name)
            self.detection_history.append({"step": detector_name, "count": 0})
            return

        for new_entity in entities:
            self.resolved_entities = [
                e for e in self.resolved_entities
                if not (
                    e.page_number == new_entity.page_number
                    and max(e.start_char, new_entity.start_char) < min(e.end_char, new_entity.end_char)
                    and e.confidence_score <= new_entity.confidence_score
                )
            ]
            self.resolved_entities.append(new_entity)

            if new_entity.confidence_score >= threshold:
                self.lock_span(
                    new_entity,
                    reason=f"Authoritative high-confidence {detector_name} detection",
                )

        self.prune_pending_candidates()

        if detector_name not in self.executed_detectors:
            self.executed_detectors.append(detector_name)
        self.detection_history.append({"step": detector_name, "count": len(entities)})

    def add_pending_candidates(self, candidates: list[DetectionResult]) -> None:
        """Adds low-confidence candidate detections to the pending validation queue."""
        for c in candidates:
            if not self.is_span_locked(c.start_char, c.end_char, getattr(c, "page_number", 1)) and self.is_span_unmasked(c.start_char, c.end_char, min_confidence=0.80):
                self.pending_candidates.append(c)

    def clear_pending_candidates(self) -> None:
        """Clears the pending candidate validation queue."""
        self.pending_candidates.clear()

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
        min_confidence: float = 0.80,
    ) -> bool:
        """
        Returns True when a detector result belongs entirely to text that has
        not already been claimed by an existing high-confidence entity or locked span.
        Uses exact interval overlap logic: max(start, locked_start) < min(end, locked_end).
        """
        if start < 0 or end > len(self.original_text) or start >= end:
            return False

        if self.is_span_locked(start, end):
            return False

        for entity in self.resolved_entities:
            if entity.confidence_score >= min_confidence:
                if max(start, entity.start_char) < min(end, entity.end_char):
                    return False

        return True

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
                (
                    f"{candidate['kind']}@"
                    f"{candidate['start']}:{candidate['end']}"
                )
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
        # 1. Check if the line matches a structured Key-Value / Label-Value pattern
        label_match = re.match(
            r"^\s*([A-Za-z0-9][A-Za-z0-9\s]{0,25})\s*[:]\s*(.+?)\s*$",
            line,
        )
        if label_match and not self._looks_like_label(label_match.group(1)):
            label_match = None

        if not label_match and line.count(" - ") == 1:
            temp_match = re.match(
                r"^\s*([A-Za-z0-9][A-Za-z0-9\s]{0,25})\s+[-]\s+(.+?)\s*$",
                line,
            )
            if temp_match and self._looks_like_label(temp_match.group(1)):
                label_match = temp_match

        exclude_start = -1
        exclude_end = -1
        is_structured = False

        if label_match:
            is_structured = True
            exclude_start = label_match.start(1)
            exclude_end = label_match.end(1)
            self._add_candidate(
                candidates,
                line_start + label_match.start(2),
                line_start + label_match.end(2),
                "label_value",
                min_chars,
            )

        # 2. Check if the entire line is a standalone title or header (only if not structured)
        if not is_structured and self._is_title_or_header_line(line):
            return

        # 3. Scan line with generic matchers, skipping excluded label spans
        for pattern, kind in (
            (STRUCTURED_TOKEN_PATTERN, "structured_token"),
            (TITLE_NAME_PATTERN, "titled_name"),
            (ORG_OR_FACILITY_PATTERN, "organization_or_facility"),
            (PROPER_NOUN_PATTERN, "proper_noun"),
        ):
            for match in pattern.finditer(line):
                if (
                    exclude_start != -1
                    and match.start() >= exclude_start
                    and match.end() <= exclude_end
                ):
                    continue
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
            if (
                exclude_start != -1
                and word_match.start() >= exclude_start
                and word_match.end() <= exclude_end
            ):
                continue
            self._add_candidate(
                candidates,
                line_start + word_match.start(),
                line_start + word_match.end(),
                "domain_signal",
                min_chars,
            )

    @staticmethod
    def _is_title_or_header_line(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False

        # Sentence punctuation check
        if stripped[-1] in (".", "?", "!"):
            return False

        words = re.findall(r"\b[A-Za-z]+\b", stripped)
        if not words:
            return False

        # Standard lowercase title particles
        title_words = {
            "of", "and", "the", "in", "on", "at", "for", "with",
            "a", "an", "to", "by", "or", "about", "from", "as", "into"
        }

        for word in words:
            if word.lower() in title_words:
                continue
            if not (word[0].isupper() or word.isupper()):
                return False

        return len(words) <= 8

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
        Returns the original document text for detector processing.
        """
        return self.original_text

    @property
    def has_remaining_text(self) -> bool:
        """
        Returns True if unresolved text still exists.
        """
        return bool(self.original_text.strip())
