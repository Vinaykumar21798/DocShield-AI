from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Callable

from modules.detection.confidence import ConfidenceCalculator
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.detectors.gliner_detector import GLiNERDetector
from modules.detection.detectors.medspacy_detector import MedSpaCyDetector
from modules.detection.detectors.ollama_validator import OllamaValidator
from modules.detection.detectors.presidio_detector import PresidioDetector
from modules.detection.detectors.regex_detector import RegexDetector
from modules.detection.detectors.qwen_detector import Qwen3BDetector
from modules.detection.analyzer.detector_selector import DetectorSelector
from modules.detection.deduplicator import Deduplicator
from modules.detection.entity_mapper import EntityMapper
from modules.detection.exceptions import DetectionError
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState

logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DynamicDetectionConfig:
    """
    Runtime knobs for low-cost dynamic detection orchestration.
    """

    high_confidence_threshold: float = 0.85
    medium_confidence_threshold: float = 0.60
    llm_validation_threshold: float = 0.80
    semantic_reasoning_threshold: float = 0.80
    stopping_candidate_threshold: int = 0
    min_candidate_chars: int = 3
    llm_context_window: int = 160
    max_unresolved_llm_contexts: int = 8
    unresolved_llm_enabled: bool = True
    detection_llm_enabled: bool = True

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
            llm_validation_threshold=cls._float_env(
                "DETECTION_LLM_VALIDATION_THRESHOLD",
                cls.llm_validation_threshold,
            ),
            semantic_reasoning_threshold=cls._float_env(
                "DETECTION_SEMANTIC_REASONING_THRESHOLD",
                cls.semantic_reasoning_threshold,
            ),
            stopping_candidate_threshold=cls._int_env(
                "DETECTION_STOPPING_CANDIDATE_THRESHOLD",
                cls.stopping_candidate_threshold,
            ),
            min_candidate_chars=cls._int_env(
                "DETECTION_MIN_CANDIDATE_CHARS",
                cls.min_candidate_chars,
            ),
            llm_context_window=cls._int_env(
                "DETECTION_LLM_CONTEXT_WINDOW",
                cls.llm_context_window,
            ),
            max_unresolved_llm_contexts=cls._int_env(
                "DETECTION_MAX_UNRESOLVED_LLM_CONTEXTS",
                cls.max_unresolved_llm_contexts,
            ),
            unresolved_llm_enabled=cls._bool_env(
                "DETECTION_UNRESOLVED_LLM_ENABLED",
                cls.unresolved_llm_enabled,
            ),
            detection_llm_enabled=cls._bool_env(
                "DETECTION_LLM_ENABLED",
                cls.detection_llm_enabled,
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
    routes detectors one at a time against PipelineState.current_text, which is
    the original text with all previously accepted spans masked out.
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
        # Presidio
        "person": "presidio",
        "location": "presidio",
        "date_time": "presidio",
        "organization": "presidio",
        "address": "presidio",
        # GLiNER
        "doctor": "gliner",
        "patient": "gliner",
        "hospital": "gliner",
        "nurse": "gliner",
        "physician": "gliner",
        "healthcare staff": "gliner",
        "healthcare_staff": "gliner",
        "medical facility": "gliner",
        "medical_facility": "gliner",
        "healthcare organization": "gliner",
        "healthcare_organization": "gliner",
        # MedSpaCy
        "problem": "medspacy",
        "medication": "medspacy",
        "procedure": "medspacy",
        "lab": "medspacy",
        "symptom": "medspacy",
        "diagnosis": "medspacy",
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
        "regex": 4,
        "presidio": 3,
        "gliner": 2,
        "medspacy": 1,
        "qwen3b": 0,
        "qwen8b": 0,
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
        "npi_number",
        "member_id",
        "group_number",
        "tax_id",
        "eob_number",
        "po_box",
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

    def __init__(self):
        self.regex = RegexDetector()

        self._presidio = None
        self._gliner = None
        self._medspacy = None
        self._qwen3b = None

        self.validator = OllamaValidator()
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
            logger.info("Loading Qwen 3B...")
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
        )

        try:
            start_time = time.perf_counter()
            raw_entities = detector.detect(
                run_text,
                page_number,
            )
            duration = time.perf_counter() - start_time
            state.log_time(detector.name, duration)
            if context_offset:
                raw_entities = self._offset_entities(raw_entities, context_offset)

            entities = self._filter_new_entities(
                raw_entities,
                state,
                detector.name,
                mask_confidence_threshold=self.config.high_confidence_threshold,
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

        except Exception as exc:
            logger.exception(
                "%s detector failed",
                detector.name,
            )
            raise DetectionError(
                f"{detector.name} failed"
            ) from exc

    @staticmethod
    def _filter_new_entities(
        entities: list[DetectionResult],
        state: PipelineState,
        detector_name: str,
        mask_confidence_threshold: float | None = None,
    ) -> list[DetectionResult]:
        accepted = []
        for entity in entities:
            if DetectionService._matches_previous_entity(
                entity,
                state,
                mask_confidence_threshold,
            ):
                logger.info(
                    "Skipping %s entity from %s because it duplicates a previous entity",
                    entity.entity_type,
                    detector_name,
                )
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

    def _attach_orchestration_context(
        self,
        detector: BaseDetector,
        state: PipelineState,
        remaining_text: str,
        candidate_summary: dict,
        context_offset: int,
    ) -> None:
        setattr(
            detector,
            "orchestration_context",
            {
                "remaining_text": remaining_text,
                "previous_entities": list(state.resolved_entities),
                "remaining_candidates": candidate_summary,
                "text_offset": context_offset,
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
            if (
                previous.start_char == entity.start_char
                and previous.end_char == entity.end_char
            ):
                # Duplicate span/type found. Merge detector names regardless of confidence.
                previous.detector = Deduplicator._merged_detectors(previous.detector, entity.detector)

                # Check if new detection is higher confidence.
                if entity.confidence_score > previous.confidence_score:
                    previous.confidence_score = entity.confidence_score
                    if entity.metadata:
                        previous.metadata.update(entity.metadata)

                    # Trigger masking if the updated confidence now exceeds the threshold
                    if (
                        mask_confidence_threshold is not None
                        and previous.confidence_score >= mask_confidence_threshold
                    ):
                        state.mask_manager.add_entities([previous])

                return True
        return False

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

            current_stage = "SEMANTIC_REASONING_DECISION"
            self._run_semantic_reasoning_if_needed(
                state,
                page_number,
                config,
            )

            current_stage = "LLM_VALIDATION"
            entities = self._calibrate_confidence(
                state.resolved_entities,
                config,
            )
            entities = self._validate_low_confidence_entities(
                text,
                entities,
                config,
            )

            current_stage = "FINALIZATION"
            results = self._finalize_results(
                state,
                entities,
                config,
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
            new_entities = self._run_detector(
                detector,
                state,
                page_number,
                custom_text=state.current_text,
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

    def _run_semantic_reasoning_if_needed(
        self,
        state: PipelineState,
        page_number: int,
        config: DynamicDetectionConfig,
    ) -> None:
        remaining = state.remaining_candidate_summary(
            min_chars=config.min_candidate_chars,
        )
        unresolved_candidates = (
            remaining["count"] > config.stopping_candidate_threshold
        )
        low_or_conflicted = (
            self._has_low_confidence(
                state.resolved_entities,
                config.semantic_reasoning_threshold,
            )
            or self._has_overlapping_type_conflicts(state.resolved_entities)
        )

        if self._llm_bypassed():
            if unresolved_candidates or low_or_conflicted:
                logger.info(
                    "Skipping Qwen/Ollama because BYPASS_LLM is true. "
                    "unresolved_candidates=%s low_or_conflicted=%s",
                    remaining["count"],
                    low_or_conflicted,
                )
            return

        if not config.unresolved_llm_enabled:
            logger.info("Skipping Qwen 3B semantic extraction by configuration.")
            return

        if not unresolved_candidates:
            logger.info(
                "Skipping Qwen 3B semantic extraction: no unresolved candidate spans remain."
            )
            return

        qwen = self.qwen3b
        if qwen.client is None:
            logger.info("Skipping Qwen 3B semantic extraction: Ollama client unavailable.")
            return

        contexts = state.candidate_contexts(
            candidates=remaining["candidates"],
            window=config.llm_context_window,
            max_contexts=config.max_unresolved_llm_contexts,
        )
        if not contexts:
            logger.info(
                "Skipping Qwen 3B semantic extraction: no bounded unresolved contexts available."
            )
            return

        total_new_entities = 0
        for context in contexts:
            logger.info(
                "Executing Qwen 3B on bounded unresolved context. "
                "context_start=%s context_end=%s candidate=%s",
                context["start"],
                context["end"],
                context["candidate"],
            )
            new_entities = self._run_detector(
                qwen,
                state,
                page_number,
                custom_text=context["text"],
                context_offset=context["start"],
            )
            total_new_entities += len(new_entities)

        self._calibrate_confidence(state.resolved_entities, config)
        logger.info(
            "Qwen 3B bounded semantic extraction complete. contexts=%d new_entities=%d",
            len(contexts),
            total_new_entities,
        )

    def _validate_low_confidence_entities(
        self,
        original_text: str,
        entities: list[DetectionResult],
        config: DynamicDetectionConfig,
    ) -> list[DetectionResult]:
        high_entities = []
        low_entities = []

        for entity in entities:
            if entity.confidence_score < config.llm_validation_threshold:
                low_entities.append(entity)
            else:
                high_entities.append(entity)

        if not low_entities:
            logger.info("No low-confidence entities require Qwen 8B validation.")
            return entities

        if self._llm_bypassed():
            logger.info(
                "BYPASS_LLM is true. Skipping Qwen 8B validation for %d low-confidence entities.",
                len(low_entities),
            )
            return entities

        context = self._build_entity_context(
            original_text,
            low_entities,
            config.llm_context_window,
        )
        logger.info(
            "Validating %d low-confidence entities via Qwen 8B using bounded context.",
            len(low_entities),
        )
        start_val = time.perf_counter()
        validated_low_entities = self.validator.validate_batch(
            context=context,
            entities=low_entities,
        )
        val_duration = time.perf_counter() - start_val

        accepted_count = sum(
            1
            for entity in validated_low_entities
            if entity.metadata.get("valid", True)
        )
        rejected_count = len(validated_low_entities) - accepted_count
        logger.info(
            "Qwen 8B validation complete. duration=%.3fs escalated=%d accepted=%d rejected=%d",
            val_duration,
            len(low_entities),
            accepted_count,
            rejected_count,
        )

        return high_entities + validated_low_entities

    def _finalize_results(
        self,
        state: PipelineState,
        entities: list[DetectionResult],
        config: DynamicDetectionConfig,
    ) -> list[DetectionResult]:
        results = [
            entity
            for entity in entities
            if entity.metadata.get("valid", True)
        ]

        results = EntityMapper.normalize(results)
        results = self._calibrate_confidence(results, config)
        results = Deduplicator.deduplicate(results)
        results = self._resolve_overlapping_spans(results)

        # 1. OCR Line Break Crossing protection
        filtered_results = []
        for entity in results:
            if "\n" in entity.entity_value and entity.entity_type != "ADDRESS":
                logger.info(
                    "Discarding entity %s because it crosses line boundaries (contains newline)",
                    entity.entity_value
                )
                continue
            filtered_results.append(entity)
        results = filtered_results

        # 2. Contextual Re-classification
        results = self._contextual_reclassify(state.original_text, results)

        # 3. Medication-Dosage Association
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
        return entities

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
                    # Record conflicting types for overlapping spans
                    if accepted.entity_type.upper() != entity.entity_type.upper():
                        conflicting = accepted.metadata.get("conflicting_types") or [accepted.entity_type]
                        if entity.entity_type not in conflicting:
                            conflicting.append(entity.entity_type)
                        accepted.metadata["conflicting_types"] = conflicting
                    # Merge detector names if they overlap
                    accepted.detector = Deduplicator._merged_detectors(accepted.detector, entity.detector)
                    break
            if not overlap:
                non_overlapping.append(entity)

        return non_overlapping

    def _overlap_sorting_key(self, entity: DetectionResult) -> tuple:
        entity_type = entity.entity_type.lower()
        detector_names = self._detector_names(entity.detector)
        owner = self.AUTHORITATIVE_OWNERS.get(entity_type)
        is_authoritative = 1 if owner in detector_names else 0
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

    @staticmethod
    def _has_low_confidence(
        entities: list[DetectionResult],
        threshold: float,
    ) -> bool:
        return any(entity.confidence_score < threshold for entity in entities)

    @staticmethod
    def _has_overlapping_type_conflicts(
        entities: list[DetectionResult],
    ) -> bool:
        for index, left in enumerate(entities):
            for right in entities[index + 1:]:
                if left.page_number != right.page_number:
                    continue
                if left.start_char >= right.end_char or left.end_char <= right.start_char:
                    continue
                if left.entity_type != right.entity_type:
                    return True
        return False

    @staticmethod
    def _build_entity_context(
        text: str,
        entities: list[DetectionResult],
        window: int,
    ) -> str:
        snippets = []
        seen = set()
        for entity in entities:
            start, end = PipelineState._bounded_context_bounds(
                len(text),
                entity.start_char,
                entity.end_char,
                window,
            )
            key = (start, end)
            if key in seen:
                continue
            seen.add(key)
            snippets.append(
                f"[{start}:{end}] {text[start:end]}"
            )
        return "\n\n".join(snippets)

    @staticmethod
    def _sync_compatibility_fields(entity: DetectionResult) -> None:
        entity.text = entity.entity_value
        entity.confidence = entity.confidence_score
        entity.start = entity.start_char
        entity.end = entity.end_char
        entity.canonical_type = entity.entity_type
        if entity.entity_owner is None:
            entity.entity_owner = entity.detector

    @staticmethod
    def _llm_bypassed() -> bool:
        return os.getenv("BYPASS_LLM", "false").strip().lower() in TRUE_VALUES
