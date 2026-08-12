from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Callable

from modules.detection.confidence import ConfidenceCalculator
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.detectors.gliner_detector import GLiNERDetector
from modules.detection.detectors.medspacy_detector import MedSpaCyDetector
from modules.detection.detectors.presidio_detector import PresidioDetector
from modules.detection.detectors.regex_detector import RegexDetector
from modules.detection.detectors.qwen_detector import Qwen3BDetector
from modules.detection.analyzer.detector_selector import DetectorSelector
from modules.detection.deduplicator import Deduplicator
from modules.detection.entity_mapper import EntityMapper, PrivacyMapper
from modules.detection.exceptions import DetectionError
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState
from modules.detection.validators.entity_validator import EntityValidator

logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DynamicDetectionConfig:
    """
    Runtime knobs for low-cost dynamic detection orchestration.
    """

    high_confidence_threshold: float = 0.80
    medium_confidence_threshold: float = 0.60
    stopping_candidate_threshold: int = 0
    min_candidate_chars: int = 3

    @classmethod
    def from_env(cls) -> "DynamicDetectionConfig":
        return cls(
            high_confidence_threshold=cls._float_env(
                "DETECTION_HIGH_CONFIDENCE_THRESHOLD",
                cls.high_confidence_threshold,
            ),
            medium_confidence_threshold=cls._float_env(
                "DETECTION_MEDIUM_CONFIDENCE_THRESHOLD",
                cls.medium_confidence_threshold,
            ),
            stopping_candidate_threshold=cls._int_env(
                "DETECTION_STOPPING_CANDIDATE_THRESHOLD",
                cls.stopping_candidate_threshold,
            ),
            min_candidate_chars=cls._int_env(
                "DETECTION_MIN_CANDIDATE_CHARS",
                cls.min_candidate_chars,
            ),
        )

    @staticmethod
    def _float_env(name: str, default: float) -> float:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            logger.warning("Invalid float for %s=%s; using %s", name, value, default)
            return default

    @staticmethod
    def _int_env(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning("Invalid integer for %s=%s; using %s", name, value, default)
            return default

    @staticmethod
    def _bool_env(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in TRUE_VALUES


class DetectionService:
    """
    Dynamic Detection Orchestrator

    The public API remains detect(text, page_number=1) with an optional
    document_type hint. Internally, the service
    lets deterministic detectors inspect the same original text, then resolves
    their candidates centrally. Qwen remains bounded to unresolved context.
    """

    AUTHORITATIVE_OWNERS = {
        # Regex
        "email": "regex",
        "phone_number": "regex",
        "us_phone_number": "regex",
        "pan_number": "regex",
        "passport_number": "regex",
        "aadhaar_number": "regex",
        "ssn": "regex",
        "mrn": "regex",
        "medical_record_number": "regex",
        "insurance_id": "regex",
        "insurance_provider": "regex",
        "claim_number": "regex",
        "ifsc_code": "regex",
        "upi_id": "regex",
        "url": "regex",
        "ip_address": "regex",
        "zip_code": "regex",
        "pin_code": "regex",
        "date_of_birth": "regex",
        "visit_date": "regex",
        "provider": "regex",
        "credit_card": "regex",
        "credit_card_number": "regex",
        "bank_account": "regex",
        "bank_account_number": "regex",
        "cpt_code": "regex",
        "icd10_code": "regex",
        "npi_number": "regex",
        "member_id": "regex",
        "group_number": "regex",
        "tax_id": "regex",
        "eob_number": "regex",
        "po_box": "regex",
        "tracking_number": "regex",
        "access_code": "regex",
        "report_id": "regex",
        # Presidio
        "person": "presidio",
        "location": "presidio",
        "date_time": "presidio",
        "organization": "presidio",
        "address": "presidio",
        # GLiNER
        "doctor": ("regex", "gliner"),
        "patient": ("regex", "gliner"),
        "hospital": ("regex", "gliner"),
        "nurse": "gliner",
        "physician": "gliner",
        "healthcare staff": "gliner",
        "healthcare_staff": "gliner",
        "medical facility": "gliner",
        "medical_facility": "gliner",
        "healthcare organization": "gliner",
        "healthcare_organization": ("regex", "gliner"),
        # MedSpaCy
        "problem": "medspacy",
        "medication": ("regex", "medspacy"),
        "procedure": ("regex", "medspacy"),
        "lab": "medspacy",
        "symptom": "medspacy",
        "diagnosis": ("regex", "medspacy"),
        "allergy": "medspacy",
        "vital_sign": "medspacy",
        "disease": "medspacy",
        "clinical_findings": "medspacy",
        "clinical finding": "medspacy",
        "clinical_finding": "medspacy",
        "clinical_measurement": "medspacy",
        "lab_result": "medspacy",
        "dosage": "medspacy",
    }

    DETECTOR_PRIORITY = {
        "regex": 5,
        "medspacy": 4,
        "gliner": 3,
        "presidio": 2,
        "qwen3b": 0,
    }

    PII_SAFETY_TYPES = {
        "ACCESS_CODE",
        "ADDRESS",
        "DATE_OF_BIRTH",
        "EMAIL",
        "INSURANCE_ID",
        "MEDICAL_RECORD_NUMBER",
        "MEMBER_ID",
        "PATIENT",
        "REPORT_ID",
        "PHONE_NUMBER",
        "SSN",
        "TRACKING_NUMBER",
        "US_PHONE_NUMBER",
    }

    SPECIALIZED_TYPES = {
        "email",
        "phone_number",
        "us_phone_number",
        "pan_number",
        "passport_number",
        "aadhaar_number",
        "ssn",
        "mrn",
        "medical_record_number",
        "insurance_id",
        "insurance_provider",
        "claim_number",
        "ifsc_code",
        "upi_id",
        "url",
        "ip_address",
        "zip_code",
        "pin_code",
        "date_of_birth",
        "visit_date",
        "provider",
        "credit_card",
        "credit_card_number",
        "bank_account_number",
        "doctor",
        "patient",
        "cpt_code",
        "icd10_code",
        "npi_number",
        "member_id",
        "group_number",
        "tax_id",
        "eob_number",
        "po_box",
        "tracking_number",
        "access_code",
        "report_id",
        "clinical_measurement",
        "vital_sign",
        "dosage",
        "nurse",
        "physician",
        "healthcare_staff",
        "healthcare staff",
        "medical_facility",
        "medical facility",
        "healthcare_organization",
        "healthcare organization",
        "hospital",
        "disease",
        "problem",
        "medication",
        "procedure",
        "lab",
        "symptom",
        "diagnosis",
        "allergy",
        "vital_sign",
        "clinical_finding",
        "clinical finding",
    }

    QWEN_CONTEXT_WINDOW = 80
    QWEN_MAX_CONTEXTS = 3

    def __init__(self):
        self.regex = RegexDetector()

        self._presidio = None
        self._gliner = None
        self._medspacy = None
        self._qwen3b = None

        self.router = DetectorSelector()
        self.config = DynamicDetectionConfig.from_env()

    @property
    def presidio(self):
        if self._presidio is None:
            logger.info("Loading Presidio...")
            self._presidio = PresidioDetector()
        return self._presidio

    @property
    def gliner(self):
        if self._gliner is None:
            logger.info("Loading GLiNER...")
            self._gliner = GLiNERDetector()
        return self._gliner

    @property
    def medspacy(self):
        if self._medspacy is None:
            logger.info("Loading MedSpaCy...")
            self._medspacy = MedSpaCyDetector()
        return self._medspacy

    @property
    def qwen3b(self):
        if self._qwen3b is None:
            logger.info("Loading Qwen3:4b...")
            self._qwen3b = Qwen3BDetector()
        return self._qwen3b

    def _detector_getters(self) -> dict[str, Callable[[], BaseDetector]]:
        return {
            "regex": lambda: self.regex,
            "presidio": lambda: self.presidio,
            "gliner": lambda: self.gliner,
            "medspacy": lambda: self.medspacy,
            "qwen3b": lambda: self.qwen3b,
        }

    def _run_detector(
        self,
        detector: BaseDetector,
        state: PipelineState,
        page_number: int,
        custom_text: str | None = None,
        context_offset: int = 0,
        allow_claimed_spans: bool = False,
        known_entities: list[dict] | None = None,
    ) -> list[DetectionResult]:
        """
        Executes one detector against the current unmasked text and updates
        PipelineState with newly accepted entities.
        """
        run_text = custom_text if custom_text is not None else state.current_text
        if not run_text or not run_text.strip():
            state.add_entities([], detector.name)
            return []

        candidate_summary = state.remaining_candidate_summary(
            min_chars=self.config.min_candidate_chars,
        )
        self._attach_orchestration_context(
            detector,
            state,
            run_text,
            candidate_summary,
            context_offset,
            known_entities,
        )

        start_time = time.perf_counter()
        try:
            raw_entities = detector.detect(
                run_text,
                page_number,
            )
            duration = time.perf_counter() - start_time
            state.log_time(detector.name, duration)
            if context_offset:
                raw_entities = self._offset_entities(raw_entities, context_offset)

            raw_entities = EntityValidator.validate_candidates(
                raw_entities,
                state.original_text,
            )

            raw_entities = self._filter_valid_entities(
                raw_entities,
                len(state.original_text),
                detector.name,
            )
            entities = self._filter_new_entities(
                raw_entities,
                state,
                detector.name,
                mask_confidence_threshold=self.config.high_confidence_threshold,
                allow_claimed_spans=allow_claimed_spans,
            )
            state.add_entities(
                entities,
                detector.name,
                mask_confidence_threshold=self.config.high_confidence_threshold,
            )

            if len(entities) != len(raw_entities):
                logger.info(
                    "%s produced %d entities; accepted %d on unmasked spans",
                    detector.name,
                    len(raw_entities),
                    len(entities),
                )

            logger.info(
                "%s detected %d accepted entities",
                detector.name,
                len(entities),
            )
            return entities

        except Exception:
            duration = time.perf_counter() - start_time
            state.log_time(detector.name, duration)
            state.log_skipped(detector.name)
            state.add_entities([], detector.name)
            logger.exception(
                "%s detector failed; skipping to next detector",
                detector.name,
            )
            return []

    @staticmethod
    def _filter_new_entities(
        entities: list[DetectionResult],
        state: PipelineState,
        detector_name: str,
        mask_confidence_threshold: float | None = None,
        allow_claimed_spans: bool = False,
        known_entities: list[dict] | None = None,
    ) -> list[DetectionResult]:
        accepted = []
        for entity in entities:
            if not DetectionService._is_valid_entity(
                entity,
                len(state.original_text),
            ):
                logger.info(
                    "Skipping invalid %s entity from %s before masking: value=%r span=%s-%s",
                    getattr(entity, "entity_type", "UNKNOWN"),
                    detector_name,
                    getattr(entity, "entity_value", None),
                    getattr(entity, "start_char", None),
                    getattr(entity, "end_char", None),
                )
                continue

            if DetectionService._matches_previous_entity(
                entity,
                state,
                mask_confidence_threshold,
            ):
                if entity.metadata.pop("duplicate_upgraded_previous", False):
                    logger.info(
                        "Upgraded previous %s entity from %s duplicate: value=%r confidence=%.3f span=%s-%s",
                        entity.entity_type,
                        detector_name,
                        entity.entity_value,
                        entity.confidence_score,
                        entity.start_char,
                        entity.end_char,
                    )
                else:
                    logger.info(
                        "Skipping %s entity from %s because it duplicates a previous entity",
                        entity.entity_type,
                        detector_name,
                    )
                continue

            if allow_claimed_spans:
                accepted.append(entity)
                continue

            if state.is_span_unmasked(entity.start_char, entity.end_char):
                accepted.append(entity)
                continue

            logger.info(
                "Skipping %s entity from %s because span is already masked: %s-%s",
                entity.entity_type,
                detector_name,
                entity.start_char,
                entity.end_char,
            )
        return accepted

    @staticmethod
    def _filter_valid_entities(
        entities: list[DetectionResult],
        text_length: int,
        detector_name: str,
    ) -> list[DetectionResult]:
        valid_entities: list[DetectionResult] = []
        for entity in entities:
            if not DetectionService._is_valid_entity(entity, text_length):
                logger.info(
                    "Skipping invalid %s entity from %s: value=%r span=%s-%s",
                    getattr(entity, "entity_type", "UNKNOWN"),
                    detector_name,
                    getattr(entity, "entity_value", None),
                    getattr(entity, "start_char", None),
                    getattr(entity, "end_char", None),
                )
                continue

            entity.entity_value = entity.entity_value.strip()
            entity.text = entity.entity_value
            valid_entities.append(entity)
        return valid_entities

    @staticmethod
    def _is_valid_entity(
        entity: DetectionResult,
        text_length: int,
    ) -> bool:
        value = getattr(entity, "entity_value", None)
        if not isinstance(value, str) or not value.strip():
            return False

        start = getattr(entity, "start_char", None)
        end = getattr(entity, "end_char", None)
        if not isinstance(start, int) or not isinstance(end, int):
            return False
        if start < 0 or end > text_length or start >= end:
            return False
        return True

    def _attach_orchestration_context(
        self,
        detector: BaseDetector,
        state: PipelineState,
        remaining_text: str,
        candidate_summary: dict,
        context_offset: int,
        known_entities: list[dict] | None = None,
    ) -> None:
        setattr(
            detector,
            "orchestration_context",
            {
                "remaining_text": remaining_text,
                "previous_entities": list(state.resolved_entities),
                "remaining_candidates": candidate_summary,
                "text_offset": context_offset,
                "known_entities": known_entities or [],
                "executed_detectors": list(state.executed_detectors),
                "skipped_detectors": list(state.skipped_detectors),
            },
        )

    @staticmethod
    def _offset_entities(
        entities: list[DetectionResult],
        context_offset: int,
    ) -> list[DetectionResult]:
        for entity in entities:
            entity.start_char += context_offset
            entity.end_char += context_offset
            entity.start = entity.start_char
            entity.end = entity.end_char
            entity.metadata["context_offset"] = context_offset
        return entities

    @staticmethod
    def _matches_previous_entity(
        entity: DetectionResult,
        state: PipelineState,
        mask_confidence_threshold: float | None = None,
    ) -> bool:
        entity_type = entity.entity_type.upper()
        for previous in state.resolved_entities:
            if previous.page_number != entity.page_number:
                continue
            if previous.entity_type.upper() != entity_type:
                continue
            if not DetectionService._is_duplicate_span_or_value(previous, entity):
                continue

            should_replace = DetectionService._should_replace_previous_entity(
                previous,
                entity,
                mask_confidence_threshold,
            )
            if should_replace:
                previous_detector = previous.detector
                previous_confidence = previous.confidence_score
                DetectionService._copy_detection_result(previous, entity)
                previous.metadata["upgraded_from_detector"] = previous_detector
                previous.metadata["upgraded_from_confidence"] = previous_confidence
                previous.metadata["upgraded_by_duplicate"] = True
                entity.metadata["duplicate_upgraded_previous"] = True

                if (
                    mask_confidence_threshold is not None
                    and previous.confidence_score >= mask_confidence_threshold
                ):
                    state.mask_manager.add_entities([previous])
            else:
                entity.metadata["duplicate_upgraded_previous"] = False

            return True
        return False

    @staticmethod
    def _is_duplicate_span_or_value(
        previous: DetectionResult,
        entity: DetectionResult,
    ) -> bool:
        if (
            previous.start_char == entity.start_char
            and previous.end_char == entity.end_char
        ):
            return True

        if not DetectionService._normalized_entity_value_equal(
            previous.entity_value,
            entity.entity_value,
        ):
            return False

        return DetectionService._span_overlap_ratio(previous, entity) >= 0.50

    @staticmethod
    def _should_replace_previous_entity(
        previous: DetectionResult,
        entity: DetectionResult,
        mask_confidence_threshold: float | None = None,
    ) -> bool:
        if entity.confidence_score > previous.confidence_score:
            return True

        if mask_confidence_threshold is None:
            return False

        return (
            previous.confidence_score < mask_confidence_threshold
            and entity.confidence_score >= previous.confidence_score
            and entity.detector != previous.detector
        )

    @staticmethod
    def _normalized_entity_value_equal(left: str, right: str) -> bool:
        return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()

    @staticmethod
    def _span_overlap_ratio(
        previous: DetectionResult,
        entity: DetectionResult,
    ) -> float:
        overlap = max(
            0,
            min(previous.end_char, entity.end_char)
            - max(previous.start_char, entity.start_char),
        )
        if overlap <= 0:
            return 0.0

        previous_length = max(1, previous.end_char - previous.start_char)
        entity_length = max(1, entity.end_char - entity.start_char)
        return overlap / max(previous_length, entity_length)

    @staticmethod
    def _copy_detection_result(
        target: DetectionResult,
        source: DetectionResult,
    ) -> None:
        target.entity_value = source.entity_value.strip()
        target.privacy_category = source.privacy_category
        target.confidence_score = source.confidence_score
        target.detector = source.detector
        target.metadata.update(source.metadata or {})
        target.text = target.entity_value
        target.confidence = target.confidence_score
        target.start = target.start_char
        target.end = target.end_char
        target.canonical_type = source.canonical_type or source.entity_type
        target.entity_owner = source.entity_owner or source.detector

    def detect(
        self,
        text: str,
        page_number: int = 1,
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        """
        Main detection pipeline supporting page splitting.
        """
        if not text:
            return []

        page_separator = "\n\n\f\n\n"
        if page_separator in text:
            pages = text.split(page_separator)
            all_detections = []
            cumulative_offset = 0

            for i, page_text in enumerate(pages):
                current_page_num = page_number + i
                page_detections = self._detect_single_page(
                    page_text,
                    page_number=current_page_num,
                    document_type=document_type,
                )
                for detection in page_detections:
                    detection.start_char += cumulative_offset
                    detection.end_char += cumulative_offset
                    all_detections.append(detection)

                cumulative_offset += len(page_text) + len(page_separator)
            return all_detections
        else:
            return self._detect_single_page(text, page_number, document_type)

    def _detect_single_page(
        self,
        text: str,
        page_number: int = 1,
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        """
        Runs the detection pipeline for a single page of text.
        """
        if not text:
            return []

        current_stage = "INITIALIZATION"
        config = DynamicDetectionConfig.from_env()
        self.config = config

        try:
            state = PipelineState(
                original_text=text,
            )

            current_stage = "DYNAMIC_ORCHESTRATION"
            domain, route = self._execute_dynamic_orchestration(
                state,
                page_number,
                config,
                document_type,
            )

            current_stage = "FINALIZATION"
            entities = self._calibrate_confidence(
                state.resolved_entities,
                config,
            )
            results = self._finalize_results(
                state,
                entities,
                config,
                page_number,
            )

            logger.info(
                "Detection complete. document_domain=%s route=%s entities=%d "
                "skipped_detectors=%s telemetry=%s confidence_summary=%s",
                domain,
                "->".join(route),
                len(results),
                state.skipped_detectors,
                state.execution_time,
                state.confidence_summary,
            )

            return results

        except Exception as exc:
            logger.exception("Detection pipeline failed at stage: %s", current_stage)
            raise DetectionError(
                f"Detection failed at Stage {current_stage}: {exc}"
            ) from exc

    def _execute_dynamic_orchestration(
        self,
        state: PipelineState,
        page_number: int,
        config: DynamicDetectionConfig,
        document_type: str | None = None,
    ) -> tuple[str, tuple[str, ...]]:
        domain = self.router.classify_domain(
            state.original_text,
            document_type=document_type,
        )
        route = self.router.route_for_domain(domain)
        detector_getters = self._detector_getters()

        logger.info(
            "Dynamic detection route selected. document_type=%s domain=%s route=%s "
            "stop_threshold=%s min_candidate_chars=%s",
            document_type,
            domain,
            "->".join(route),
            config.stopping_candidate_threshold,
            config.min_candidate_chars,
        )

        while True:
            selection = self.router.select_next_detector(
                state=state,
                detector_getters=detector_getters,
                route=route,
                stopping_candidate_threshold=(
                    config.stopping_candidate_threshold
                ),
                min_candidate_chars=config.min_candidate_chars,
                continuation_confidence_threshold=config.high_confidence_threshold,
                exhaust_route=True,
            )

            if selection.detector is None:
                logger.info(
                    "%s Remaining candidates=%s preview=%s",
                    selection.reason,
                    selection.remaining_candidates["count"],
                    selection.remaining_candidates["preview"],
                )
                break

            detector = selection.detector
            logger.info(
                "Executing detector=%s reason=%s remaining_candidates=%s preview=%s",
                detector.name,
                selection.reason,
                selection.remaining_candidates["count"],
                selection.remaining_candidates["preview"],
            )

            before_count = len(state.resolved_entities)
            if detector.name.lower() == "qwen3b":
                new_entities = self._run_qwen_detector(
                    detector,
                    state,
                    page_number,
                    selection.remaining_candidates,
                    config,
                )
            else:
                new_entities = self._run_detector(
                    detector,
                    state,
                    page_number,
                    custom_text=state.original_text,
                    allow_claimed_spans=True,
                )
            self._calibrate_confidence(state.resolved_entities, config)
            remaining = state.remaining_candidate_summary(
                min_chars=config.min_candidate_chars,
            )
            logger.info(
                "Detector completed. detector=%s entities_found=%d "
                "total_entities=%d remaining_candidates=%d preview=%s",
                detector.name,
                len(new_entities),
                len(state.resolved_entities),
                remaining["count"],
                remaining["preview"],
            )

            if len(state.resolved_entities) == before_count and not new_entities:
                logger.info(
                    "Detector %s found no new entities; recalculated candidates=%d",
                    detector.name,
                    remaining["count"],
                )

        return domain, route

    def _run_qwen_detector(
        self,
        detector: BaseDetector,
        state: PipelineState,
        page_number: int,
        remaining_candidates: dict,
        config: DynamicDetectionConfig,
    ) -> list[DetectionResult]:
        contexts = self._qwen_contexts(
            state,
            remaining_candidates,
            config,
        )
        if not contexts:
            logger.info(
                "Skipping Qwen3:4b because no unresolved candidate or low-confidence context remains"
            )
            state.add_entities([], detector.name)
            return []

        logger.info(
            "Running Qwen3:4b on %d bounded context(s), max_contexts=%d window=%d",
            len(contexts),
            self.QWEN_MAX_CONTEXTS,
            self.QWEN_CONTEXT_WINDOW,
        )
        collected: list[DetectionResult] = []
        for context in contexts:
            collected.extend(
                self._run_detector(
                    detector,
                    state,
                    page_number,
                    custom_text=context["text"],
                    context_offset=context["start"],
                    known_entities=context.get("known_entities", []),
                )
            )
        return collected

    def _qwen_contexts(
        self,
        state: PipelineState,
        remaining_candidates: dict,
        config: DynamicDetectionConfig,
    ) -> list[dict]:
        candidate_contexts = self._qwen_original_contexts_for_candidates(
            state,
            remaining_candidates.get("candidates", []),
            config,
        )

        low_confidence_candidates = []
        for entity in state.resolved_entities:
            if entity.confidence_score >= config.high_confidence_threshold:
                continue
            if not self._is_valid_entity(entity, len(state.original_text)):
                continue
            if not state.is_span_unmasked(entity.start_char, entity.end_char):
                continue
            low_confidence_candidates.append(
                {
                    "start": entity.start_char,
                    "end": entity.end_char,
                    "text": entity.entity_value[:80],
                    "kind": "low_confidence_entity",
                }
            )

        low_confidence_candidates.sort(
            key=lambda candidate: (
                next(
                    (
                        entity.confidence_score
                        for entity in state.resolved_entities
                        if entity.start_char == candidate["start"]
                        and entity.end_char == candidate["end"]
                    ),
                    1.0,
                ),
                candidate["start"],
            )
        )
        low_confidence_contexts = self._qwen_original_contexts_for_candidates(
            state,
            low_confidence_candidates,
            config,
        )

        contexts: list[dict] = []
        seen_ranges: set[tuple[int, int]] = set()
        for context in [*candidate_contexts, *low_confidence_contexts]:
            key = (context["start"], context["end"])
            if key in seen_ranges:
                continue
            seen_ranges.add(key)
            contexts.append(context)
            if len(contexts) >= self.QWEN_MAX_CONTEXTS:
                break

        return contexts

    def _qwen_original_contexts_for_candidates(
        self,
        state: PipelineState,
        candidates: list[dict],
        config: DynamicDetectionConfig,
    ) -> list[dict]:
        contexts: list[dict] = []
        seen_ranges: set[tuple[int, int]] = set()

        for candidate in candidates[: self.QWEN_MAX_CONTEXTS]:
            start = max(0, candidate["start"] - self.QWEN_CONTEXT_WINDOW)
            end = min(
                len(state.original_text),
                candidate["end"] + self.QWEN_CONTEXT_WINDOW,
            )
            raw_text = state.original_text[start:end]
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
                    "text": state.original_text[context_start:context_end],
                    "candidate": candidate,
                    "known_entities": self._known_entities_for_qwen_context(
                        state,
                        context_start,
                        context_end,
                        config,
                    ),
                }
            )

        return contexts

    def _known_entities_for_qwen_context(
        self,
        state: PipelineState,
        context_start: int,
        context_end: int,
        config: DynamicDetectionConfig,
    ) -> list[dict]:
        known_entities: list[dict] = []
        for entity in state.resolved_entities:
            if entity.confidence_score < config.high_confidence_threshold:
                continue
            if not self._is_valid_entity(entity, len(state.original_text)):
                continue
            if entity.end_char <= context_start or entity.start_char >= context_end:
                continue

            known_entities.append(
                {
                    "entity_type": entity.entity_type,
                    "start_char": max(entity.start_char, context_start) - context_start,
                    "end_char": min(entity.end_char, context_end) - context_start,
                    "original_start_char": entity.start_char,
                    "original_end_char": entity.end_char,
                    "confidence_score": round(entity.confidence_score, 4),
                    "detector": entity.detector,
                }
            )

        known_entities.sort(key=lambda item: (item["start_char"], item["end_char"]))
        return known_entities

    def _finalize_results(
        self,
        state: PipelineState,
        entities: list[DetectionResult],
        config: DynamicDetectionConfig,
        page_number: int,
    ) -> list[DetectionResult]:
        results = [
            entity
            for entity in entities
            if entity.metadata.get("valid", True)
        ]
        results = EntityValidator.validate_candidates(
            results,
            state.original_text,
        )
        results = self._filter_valid_entities(
            results,
            len(state.original_text),
            "finalize",
        )

        results = EntityMapper.normalize(results)
        results = self._filter_valid_entities(
            results,
            len(state.original_text),
            "finalize",
        )
        results = self._calibrate_confidence(results, config)
        results = Deduplicator.deduplicate(results)
        results = self._resolve_overlapping_spans(results)

        # 1. OCR Line Break Crossing protection
        filtered_results = []
        for entity in results:
            if (
                "\n" in entity.entity_value
                and entity.entity_type
                not in {
                    "ADDRESS",
                    "CLINICAL_SECTION",
                    "PHONE_NUMBER",
                    "US_PHONE_NUMBER",
                }
            ):
                logger.info(
                    "Discarding entity %s because it crosses line boundaries (contains newline)",
                    entity.entity_value
                )
                continue
            filtered_results.append(entity)
        results = filtered_results

        # 2. Contextual Re-classification
        results = self._contextual_reclassify(state.original_text, results)

        # 3. Conservative adjacent-name merge for OCR/model fragments such as
        # "David A" + "Wilson" when they belong to one labeled patient field.
        results = self._merge_adjacent_person_spans(
            state.original_text,
            results,
        )

        # 4. Re-run only deterministic high-risk patterns as a final safety net.
        results = self._add_final_pii_safety_net(
            state.original_text,
            results,
            page_number,
        )

        # 5. Medication-Dosage Association
        self._associate_medication_dosages(results)
        results = self._calibrate_confidence(results, config)

        for entity in results:
            self._sync_compatibility_fields(entity)

        state.resolved_entities = results
        state.finalize_confidence_summary()

        results.sort(
            key=lambda entity: (
                entity.page_number,
                entity.start_char,
            )
        )
        return results

    def _contextual_reclassify(self, text: str, entities: list[DetectionResult]) -> list[DetectionResult]:
        for entity in entities:
            # Get surrounding text window (e.g., 40 characters)
            start = max(0, entity.start_char - 40)
            end = min(len(text), entity.end_char + 40)
            context = text[start:end].lower()

            if entity.entity_type in {"INSURANCE_ID", "POLICY_NUMBER"}:
                if "member" in context:
                    entity.entity_type = "MEMBER_ID"
                elif "group" in context:
                    entity.entity_type = "GROUP_NUMBER"
                elif "eob" in context:
                    entity.entity_type = "EOB_NUMBER"

            if entity.entity_type == "PHONE_NUMBER" and "npi" in context:
                # If it is valid Luhn NPI, reclassify
                if BaseDetector.is_valid_npi(entity.entity_value):
                    entity.entity_type = "NPI_NUMBER"

            if entity.entity_type == "PERSON":
                preceding = text[max(0, entity.start_char - 240):entity.start_char]
                has_name_label = bool(
                    re.search(
                        r"(?:^|\n)[ \t]*[ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¢*\-]?[ \t]*Name[ \t]*[:\-][ \t]*$",
                        preceding,
                        re.IGNORECASE,
                    )
                )
                patient_section = preceding.lower().rfind("patient information")
                next_section = max(
                    preceding.lower().rfind("appointment details"),
                    preceding.lower().rfind("medical history"),
                )
                if has_name_label and patient_section > next_section:
                    entity.entity_type = "PATIENT"
                    entity.metadata["reclassified_by"] = "patient_section_context"

            entity.privacy_category = PrivacyMapper.get_category(
                entity.entity_type
            )
        return entities

    def _add_final_pii_safety_net(
        self,
        text: str,
        entities: list[DetectionResult],
        page_number: int,
    ) -> list[DetectionResult]:
        candidates = EntityValidator.validate_candidates(
            RegexDetector().detect(text, page_number),
            text,
        )
        candidates = EntityMapper.normalize(candidates)
        existing = {
            (
                entity.page_number,
                entity.start_char,
                entity.end_char,
                entity.entity_type,
            )
            for entity in entities
        }

        for candidate in candidates:
            key = (
                candidate.page_number,
                candidate.start_char,
                candidate.end_char,
                candidate.entity_type,
            )
            if candidate.entity_type not in self.PII_SAFETY_TYPES or key in existing:
                continue
            candidate.metadata["pii_safety_net"] = True
            entities.append(candidate)
            existing.add(key)

        entities = Deduplicator.deduplicate(entities)
        return self._resolve_overlapping_spans(entities)

    def _merge_adjacent_person_spans(
        self,
        text: str,
        entities: list[DetectionResult],
    ) -> list[DetectionResult]:
        person_types = {"PATIENT", "PERSON"}
        ordered = sorted(
            entities,
            key=lambda entity: (
                entity.page_number,
                entity.start_char,
                entity.end_char,
            ),
        )
        merged: list[DetectionResult] = []
        index = 0

        while index < len(ordered):
            current = ordered[index].model_copy(deep=True)
            index += 1

            while index < len(ordered):
                following = ordered[index]
                if (
                    current.page_number != following.page_number
                    or current.entity_type not in person_types
                    or following.entity_type not in person_types
                    or following.start_char < current.end_char
                ):
                    break

                gap = text[current.end_char:following.start_char]
                if len(gap) > 3 or "\n" in gap or not re.fullmatch(r"[\s.'-]*", gap):
                    break

                preceding = text[max(0, current.start_char - 40):current.start_char]
                has_patient_context = bool(
                    re.search(
                        r"\bpatient(?:\s+name)?\s*[:\-]?\s*$",
                        preceding,
                        re.IGNORECASE,
                    )
                )
                if "PATIENT" not in {current.entity_type, following.entity_type} and not has_patient_context:
                    break

                combined_value = text[
                    current.start_char:following.end_char
                ].strip()
                if not self.regex.validate_labeled_person_value(combined_value):
                    break

                current.end_char = following.end_char
                current.entity_value = combined_value
                current.entity_type = (
                    "PATIENT"
                    if has_patient_context
                    or "PATIENT" in {current.entity_type, following.entity_type}
                    else "PERSON"
                )
                current.confidence_score = max(
                    current.confidence_score,
                    following.confidence_score,
                )
                current.metadata["merged_adjacent_name"] = True
                current.metadata["merged_detectors"] = sorted(
                    {
                        current.detector,
                        following.detector,
                    }
                )
                index += 1

            merged.append(current)

        return merged

    def _associate_medication_dosages(self, entities: list[DetectionResult]) -> None:
        medications = [e for e in entities if e.entity_type == "MEDICATION"]
        dosages = [e for e in entities if e.entity_type == "DOSAGE"]

        for med in medications:
            best_dosage = None
            min_distance = 999999
            for dos in dosages:
                if med.page_number == dos.page_number:
                    # calculate character distance
                    if dos.start_char >= med.end_char:
                        dist = dos.start_char - med.end_char
                    else:
                        dist = med.start_char - dos.end_char

                    # If close (e.g., within 30 characters)
                    if dist < min_distance and dist <= 30:
                        min_distance = dist
                        best_dosage = dos

            if best_dosage:
                med.metadata["associated_dosage"] = best_dosage.entity_value
                best_dosage.metadata["associated_medication"] = med.entity_value

    def _resolve_overlapping_spans(
        self,
        results: list[DetectionResult],
    ) -> list[DetectionResult]:
        results.sort(key=self._overlap_sorting_key, reverse=True)

        non_overlapping = []
        for entity in results:
            overlap = False
            for accepted in non_overlapping:
                if entity.page_number != accepted.page_number:
                    continue
                if (
                    entity.start_char < accepted.end_char
                    and entity.end_char > accepted.start_char
                ):
                    overlap = True
                    break
            if not overlap:
                non_overlapping.append(entity)

        return non_overlapping

    def _overlap_sorting_key(self, entity: DetectionResult) -> tuple:
        entity_type = entity.entity_type.lower()
        detector_names = self._detector_names(entity.detector)
        owners = self.AUTHORITATIVE_OWNERS.get(entity_type)
        if isinstance(owners, str):
            owner_names = {owners}
        else:
            owner_names = set(owners or ())
        is_authoritative = 1 if detector_names & owner_names else 0
        type_rank = 1 if entity_type in self.SPECIALIZED_TYPES else 0
        detector_priority = max(
            self.DETECTOR_PRIORITY.get(detector_name, 0)
            for detector_name in detector_names
        )

        return (
            is_authoritative,
            type_rank,
            detector_priority,
            entity.confidence_score,
            entity.end_char - entity.start_char,
        )

    @staticmethod
    def _detector_names(detector: str) -> set[str]:
        names = {
            part.strip().lower()
            for part in detector.split(",")
            if part.strip()
        }
        return names or {"unknown"}

    def _calibrate_confidence(
        self,
        entities: list[DetectionResult],
        config: DynamicDetectionConfig,
    ) -> list[DetectionResult]:
        return ConfidenceCalculator.calculate(
            entities,
            high_threshold=config.high_confidence_threshold,
            medium_threshold=config.medium_confidence_threshold,
        )

    @classmethod
    def _sync_compatibility_fields(cls, entity: DetectionResult) -> None:
        entity.detector = cls._display_detector_name(entity.detector)
        entity.text = entity.entity_value
        entity.confidence = entity.confidence_score
        entity.start = entity.start_char
        entity.end = entity.end_char
        entity.canonical_type = entity.entity_type
        entity.entity_owner = entity.detector

    @staticmethod
    def _display_detector_name(detector: str) -> str:
        display_names = {
            "regex": "Regex",
            "presidio": "Presidio",
            "medspacy": "MedSpaCy",
            "gliner": "GLiNER",
            "qwen3b": "Qwen3:4b",
            "qwen3:4b": "Qwen3:4b",
        }
        ignored = {"ollama", "validator", "llm-validation"}
        parts = [
            part.strip()
            for part in (detector or "").split(",")
            if part.strip()
        ]
        visible_parts = [
            part for part in parts if part.lower() not in ignored
        ]
        owner = (visible_parts or parts or ["Unknown"])[-1]
        return display_names.get(owner.lower(), owner)
