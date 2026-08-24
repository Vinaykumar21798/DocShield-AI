from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

from modules.detection.confidence import ConfidenceCalculator
from modules.detection.candidate_quality_gate import CandidateQualityGate
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.detectors.gliner_detector import GLiNERDetector
from modules.detection.detectors.medspacy_detector import MedSpaCyDetector
from modules.detection.detectors.presidio_detector import PresidioDetector
from modules.detection.detectors.regex_detector import RegexDetector
from modules.detection.detectors.gemma_detector import Gemma4E4BDetector
from modules.detection.analyzer.detector_selector import DetectorSelector
from modules.detection.deduplicator import Deduplicator
from modules.detection.entity_mapper import EntityMapper, PrivacyMapper
from modules.detection.exceptions import DetectionError
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState
from modules.detection.semantic_chunker import DocumentChunk, SemanticChunker
from modules.detection.taxonomy import TaxonomyService
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
        "qwen3b": 6,
        "gemma": 6,
    }

    LLM_DETECTOR_NAMES = {
        "gemma",
        "gemma4e4b",
        "gemma4:e4b",
        "qwen3b",
        "qwen3:4b",
        "qwen",
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
        self.chunker = SemanticChunker()
        self.quality_gate = CandidateQualityGate()
        self.config = DynamicDetectionConfig.from_env()
        self._current_document_type = None

    @property
    def presidio(self):
        if self._presidio is None:
            logger.info("Loading Presidio...")
            self._presidio = PresidioDetector()
        return self._presidio

    @presidio.setter
    def presidio(self, value):
        self._presidio = value

    @property
    def gliner(self):
        if self._gliner is None:
            logger.info("Loading GLiNER...")
            self._gliner = GLiNERDetector()
        return self._gliner

    @gliner.setter
    def gliner(self, value):
        self._gliner = value

    @property
    def medspacy(self):
        if self._medspacy is None:
            logger.info("Loading MedSpaCy...")
            self._medspacy = MedSpaCyDetector()
        return self._medspacy

    @medspacy.setter
    def medspacy(self, value):
        self._medspacy = value

    @property
    def qwen3b(self):
        return self.gemma

    @qwen3b.setter
    def qwen3b(self, value):
        self.gemma = value

    @property
    def gemma(self):
        provider = os.getenv("LLM_PROVIDER", "gemma").lower().strip()
        if provider == "azure":
            if getattr(self, "_azure_llm", None) is None:
                from modules.detection.detectors.azure_detector import AzureOpenAIDetector
                self._azure_llm = AzureOpenAIDetector()
                provider_name, model_name = self._llm_log_context(self._azure_llm)
                logger.info(
                    "Loading LLM provider=%s model=%s",
                    provider_name,
                    model_name,
                )
            return self._azure_llm
        else:
            if getattr(self, "_gemma4e4b", None) is None:
                from modules.detection.detectors.gemma_detector import Gemma4E4BDetector
                self._gemma4e4b = Gemma4E4BDetector()
                provider_name, model_name = self._llm_log_context(self._gemma4e4b)
                logger.info(
                    "Loading LLM provider=%s model=%s",
                    provider_name,
                    model_name,
                )
            return self._gemma4e4b

    @gemma.setter
    def gemma(self, value):
        self._gemma4e4b = value
        self._azure_llm = value

    @staticmethod
    def _llm_log_context(detector: BaseDetector) -> tuple[str, str]:
        """Return provider and model labels from the active detector instance."""
        raw_provider = str(getattr(detector, "name", "") or "").strip()
        provider_name = " ".join(
            token[:1].upper() + token[1:]
            for token in re.split(r"[_\s-]+", raw_provider)
            if token
        ) or "LLM"
        model_name = (
            getattr(detector, "deployment", None)
            or getattr(detector, "MODEL_NAME", None)
            or "unspecified"
        )
        return provider_name, str(model_name)

    def _detector_getters(self) -> dict[str, Callable[[], BaseDetector]]:
        return {
            "regex": lambda: self.regex,
            "presidio": lambda: self.presidio,
            "gliner": lambda: self.gliner,
            "medspacy": lambda: self.medspacy,
            "qwen3b": lambda: self.qwen3b,
            "gemma": lambda: self.gemma,
        }

    def _run_detector_on_chunks(
        self,
        detector: BaseDetector,
        chunks: list[DocumentChunk],
        state: PipelineState,
        page_number: int,
        allow_claimed_spans: bool = False,
    ) -> list[DetectionResult]:
        """
        Executes one detector across all relevant semantic chunks.
        Remaps chunk-local detection offsets to document-global coordinates
        and aggregates candidates into PipelineState without mutating or destroying text.
        """
        if not chunks:
            state.add_entities([], detector.name)
            return []

        all_chunk_entities: list[DetectionResult] = []
        executed_chunks = 0
        skipped_chunks = 0
        failed_chunks = 0
        total_duration = 0.0

        candidate_summary = state.remaining_candidate_summary(
            min_chars=self.config.min_candidate_chars,
        )

        for chunk in chunks:
            chunk_text = chunk.text
            if not chunk_text or not chunk_text.strip():
                skipped_chunks += 1
                logger.info(
                    "DetectorChunk: chunk_id=%d detector=%s status=SKIPPED reason='Empty or whitespace-only chunk text'",
                    chunk.chunk_id,
                    detector.name,
                )
                continue

            # Check if detector should run on this chunk
            try:
                should_run = detector.should_run(chunk_text, state)
            except Exception as exc:
                should_run = True
                logger.warning(
                    "DetectorChunk: chunk_id=%d detector=%s should_run check failed (%s); defaulting to execute for safety",
                    chunk.chunk_id,
                    detector.name,
                    exc,
                )

            if not should_run:
                skipped_chunks += 1
                logger.info(
                    "DetectorChunk: chunk_id=%d detector=%s status=SKIPPED reason='No relevant entity patterns/context in chunk'",
                    chunk.chunk_id,
                    detector.name,
                )
                continue

            self._attach_orchestration_context(
                detector,
                state,
                chunk_text,
                candidate_summary,
                chunk.start_char,
                None,
            )

            start_time = time.perf_counter()
            try:
                raw_chunk_entities = detector.detect(
                    chunk_text,
                    page_number,
                ) or []
                chunk_duration = time.perf_counter() - start_time
                total_duration += chunk_duration
                executed_chunks += 1

                logger.info(
                    "DetectorChunk: chunk_id=%d range=%d-%d detector=%s status=EXECUTED entities=%d latency=%.1fms",
                    chunk.chunk_id,
                    chunk.start_char,
                    chunk.end_char,
                    detector.name,
                    len(raw_chunk_entities),
                    chunk_duration * 1000.0,
                )

                # Remap local offsets to document global coordinates
                for entity in raw_chunk_entities:
                    local_start = entity.start_char
                    local_end = entity.end_char
                    global_start = chunk.start_char + local_start
                    global_end = chunk.start_char + local_end

                    entity.start_char = global_start
                    entity.end_char = global_end
                    entity.start = global_start
                    entity.end = global_end
                    entity.metadata["chunk_id"] = chunk.chunk_id
                    entity.metadata["chunk_text"] = chunk.text
                    entity.metadata["section_name"] = chunk.section_name
                    entity.metadata["local_span"] = (local_start, local_end)
                    entity.metadata["global_span"] = (global_start, global_end)

                all_chunk_entities.extend(raw_chunk_entities)

            except Exception as exc:
                chunk_duration = time.perf_counter() - start_time
                total_duration += chunk_duration
                failed_chunks += 1
                logger.error(
                    "DetectorChunk: chunk_id=%d range=%d-%d detector=%s status=FAILED error=%s latency=%.1fms",
                    chunk.chunk_id,
                    chunk.start_char,
                    chunk.end_char,
                    detector.name,
                    str(exc),
                    chunk_duration * 1000.0,
                    exc_info=True,
                )

        state.log_time(detector.name, total_duration)

        # Aggregate candidates across all processed chunks
        return self._aggregate_detector_candidates(
            detector=detector,
            raw_entities=all_chunk_entities,
            state=state,
            allow_claimed_spans=allow_claimed_spans,
            executed_chunks=executed_chunks,
            skipped_chunks=skipped_chunks,
            failed_chunks=failed_chunks,
        )

    @staticmethod
    def _is_authoritative_detection(
        entity: DetectionResult,
        detector_name: str,
        high_conf_threshold: float = 0.80,
    ) -> bool:
        """
        Determines whether a detection qualifies for authoritative LOCKED status.
        Protects against early weak generic classifications prematurely locking entities.
        """
        if entity.confidence_score < high_conf_threshold:
            return False

        det_lower = detector_name.lower()
        if "regex" in det_lower:
            return True

        if "medspacy" in det_lower:
            return entity.confidence_score >= 0.80

        if "gliner" in det_lower:
            # GLiNER is authoritative on specialized types or strong confidence
            return entity.confidence_score >= 0.85 or entity.entity_type in {
                "PATIENT", "DOCTOR", "PHYSICIAN", "NURSE", "HEALTHCARE_STAFF",
                "HOSPITAL", "CLINIC", "MEDICAL_FACILITY", "HEALTHCARE_ORGANIZATION",
                "INSURANCE_PROVIDER", "SSN", "PASSPORT_NUMBER", "DRIVING_LICENSE",
            }

        if "presidio" in det_lower:
            # Structured Presidio (NPI) or deterministically validated entities
            if entity.entity_type == "NPI_NUMBER":
                return True
            if entity.metadata.get("deterministic_validation") == "passed" and entity.confidence_score >= 0.85:
                return True
            # Weak generic Presidio NER should remain PENDING for downstream specialization
            return False

        return entity.confidence_score >= high_conf_threshold

    def _aggregate_detector_candidates(
        self,
        detector: BaseDetector,
        raw_entities: list[DetectionResult],
        state: PipelineState,
        allow_claimed_spans: bool = False,
        executed_chunks: int = 0,
        skipped_chunks: int = 0,
        failed_chunks: int = 0,
    ) -> list[DetectionResult]:
        """
        Validates, filters, and aggregates candidate detections from all chunks
        into PipelineState with span-level locking, overlap suppression, and detector continuation.
        """
        raw_entities = EntityValidator.validate_candidates(
            raw_entities,
            state.original_text,
        )
        raw_entities = self._filter_valid_entities(
            raw_entities,
            len(state.original_text),
            detector.name,
        )

        high_conf_threshold = self.config.high_confidence_threshold
        accepted_high: list[DetectionResult] = []
        pending_low: list[DetectionResult] = []

        for entity in raw_entities:
            # 1. Check if entity matches or upgrades a previously seen entity
            if DetectionService._matches_previous_entity(
                entity,
                state,
                high_conf_threshold,
            ):
                if entity.metadata.get("duplicate_upgraded_previous"):
                    state.prune_pending_candidates()
                    state.log_candidate_routing(
                        entity,
                        "LOCKED" if entity.confidence_score >= high_conf_threshold else "PENDING_FOR_LLM",
                        f"Upgraded previous entity with higher confidence ({entity.confidence_score:.2f}) from {detector.name}",
                        detector.name,
                    )
                    logger.info(
                        "CandidateGate: entity_type=%r detector=%r confidence=%.2f decision=UPGRADED reason='Upgraded previous candidate'",
                        entity.entity_type,
                        detector.name,
                        entity.confidence_score,
                    )
                else:
                    state.log_candidate_routing(
                        entity,
                        "DUPLICATE_SUPPRESSED",
                        "Overlaps previously resolved entity or duplicate candidate",
                        detector.name,
                    )
                    logger.info(
                        "DuplicateSuppressed: entity_type=%r detector=%r reason='Duplicates previously resolved entity'",
                        entity.entity_type,
                        detector.name,
                    )
                continue

            # 2. Pre-detector overlap check: check if span overlaps an already LOCKED authoritative span
            locked_match = state.get_overlapping_locked_span(entity.start_char, entity.end_char, getattr(entity, "page_number", 1))
            if not allow_claimed_spans and locked_match is not None:
                # Check for specialized replacement of a generic locked entity
                prev_type = locked_match.get("entity_type", "").upper()
                curr_type = entity.entity_type.upper()
                is_specialization = curr_type in DetectionService.ENTITY_SPECIALIZATIONS.get(prev_type, set())

                if is_specialization and entity.confidence_score >= 0.70:
                    locked_match["entity_type"] = entity.entity_type
                    if detector.name not in locked_match.get("duplicate_sources", []):
                        locked_match.setdefault("duplicate_sources", []).append(detector.name)
                    for prev in state.resolved_entities:
                        if prev.start_char == locked_match["start_char"] and prev.end_char == locked_match["end_char"]:
                            prev.entity_type = entity.entity_type
                            prev.metadata["specialized_by"] = detector.name
                    logger.info(
                        "CandidateGate: span=%d-%d specialized to %r from %s",
                        entity.start_char,
                        entity.end_char,
                        entity.entity_type,
                        detector.name,
                    )
                    continue

                state.log_candidate_routing(
                    entity,
                    "OVERLAP_SUPPRESSED",
                    f"Overlaps locked {locked_match['entity_type']} from {locked_match['detector']}",
                    detector.name,
                )
                if detector.name not in locked_match.get("duplicate_sources", []):
                    locked_match.setdefault("duplicate_sources", []).append(detector.name)
                logger.info(
                    "OverlapSuppressed: entity_type=%r detector=%r span=[%d,%d] reason='Overlaps locked %s from %s'",
                    entity.entity_type,
                    detector.name,
                    entity.start_char,
                    entity.end_char,
                    locked_match["entity_type"],
                    locked_match["detector"],
                )
                continue

            # 3. Determine if candidate qualifies for LOCKED vs PENDING
            is_authoritative = self._is_authoritative_detection(entity, detector.name, high_conf_threshold)

            if is_authoritative:
                accepted_high.append(entity)
                state.lock_span(
                    entity,
                    reason=f"Authoritative high-confidence {detector.name} detection",
                )
                state.log_candidate_routing(
                    entity,
                    "LOCKED",
                    f"Authoritative high-confidence {detector.name} detection",
                    detector.name,
                )
                logger.info(
                    "CandidateGate: entity_type=%r detector=%r confidence=%.2f decision=LOCKED reason='Authoritative high-confidence detection'",
                    entity.entity_type,
                    detector.name,
                    entity.confidence_score,
                )
            else:
                gate_eval = self.quality_gate.evaluate(
                    candidate=entity,
                    document_text=state.original_text,
                    document_type=getattr(self, "_current_document_type", None),
                    chunk_text=entity.metadata.get("chunk_text"),
                )

                state.log_candidate_routing(
                    candidate=entity,
                    decision=gate_eval.decision,
                    reason=gate_eval.reason,
                    detector_name=detector.name,
                    semantic_score=gate_eval.semantic_score,
                    structural_score=gate_eval.structural_score,
                )

                logger.info(
                    "QualityGateCandidate: candidate_id=%s doc_id=%s chunk_id=%s page=%d type=%r detector=%r confidence=%.2f semantic_relevance=%.2f doc_type=%r quality_decision=%s action=%s llm_required=%s",
                    getattr(entity, "id", hex(id(entity))[-6:]),
                    getattr(state, "document_id", "doc"),
                    entity.metadata.get("chunk_id", 0),
                    getattr(entity, "page_number", 1),
                    entity.entity_type,
                    detector.name,
                    entity.confidence_score,
                    gate_eval.semantic_score,
                    getattr(self, "_current_document_type", "generic"),
                    gate_eval.quality_decision,
                    gate_eval.action,
                    gate_eval.llm_required,
                )

                if gate_eval.decision == "PRE_LLM_REJECT":
                    logger.info(
                        "CandidateGate: type=%r detector=%r confidence=%.2f semantic_relevance=%.2f decision=PRE_LLM_REJECT",
                        entity.entity_type,
                        detector.name,
                        entity.confidence_score,
                        gate_eval.semantic_score,
                    )
                else:
                    pending_low.append(entity)
                    logger.info(
                        "CandidateGate: type=%r detector=%r confidence=%.2f semantic_relevance=%.2f decision=PENDING_FOR_LLM",
                        entity.entity_type,
                        detector.name,
                        entity.confidence_score,
                        gate_eval.semantic_score,
                    )

        state.add_entities(
            accepted_high,
            detector.name,
            mask_confidence_threshold=high_conf_threshold,
        )

        if pending_low:
            state.add_pending_candidates(pending_low)
            bypass_llm = os.getenv("BYPASS_LLM", "false").lower() in {"1", "true", "yes"}
            if bypass_llm:
                state.add_entities(
                    pending_low,
                    detector_name=detector.name,
                    mask_confidence_threshold=high_conf_threshold,
                )
            logger.info(
                "%s queued %d low-confidence candidate(s) for downstream detector continuation / validation",
                detector.name,
                len(pending_low),
            )

        logger.info(
            "Detector completed: detector=%s chunks_executed=%d chunks_skipped=%d chunks_failed=%d entities_found=%d total_entities=%d remaining_candidates=%d queued_for_validation=%d",
            detector.name,
            executed_chunks,
            skipped_chunks,
            failed_chunks,
            len(accepted_high),
            len(state.resolved_entities),
            len(pending_low),
            len(pending_low),
        )
        return accepted_high

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
        Executes one detector against a specific text slice/context.
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
            ) or []
            duration = time.perf_counter() - start_time
            state.log_time(detector.name, duration)
            if context_offset:
                self._offset_entities(raw_entities, context_offset)

            return self._aggregate_detector_candidates(
                detector=detector,
                raw_entities=raw_entities,
                state=state,
                allow_claimed_spans=allow_claimed_spans,
                executed_chunks=1,
            )

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
                    "Skipping invalid %s entity from %s before masking: span=%s-%s",
                    getattr(entity, "entity_type", "UNKNOWN"),
                    detector_name,
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
                        "Upgraded previous %s entity from %s duplicate: confidence=%.3f span=%s-%s",
                        entity.entity_type,
                        detector_name,
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
                    "Skipping invalid %s entity from %s: span=%s-%s",
                    getattr(entity, "entity_type", "UNKNOWN"),
                    detector_name,
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
                "document_type": getattr(self, "_current_document_type", None),
                "target_entities": TaxonomyService.get_target_entities(getattr(self, "_current_document_type", None)),
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

    def _run_qwen_detector(
        self,
        detector: BaseDetector,
        state: PipelineState,
        page_number: int,
        candidate_summary: dict,
        config: DynamicDetectionConfig,
    ) -> list[DetectionResult]:
        known_entities = [
            {
                "entity_type": entity.entity_type,
                "start_char": entity.start_char,
                "end_char": entity.end_char,
                "original_start_char": entity.start_char,
                "original_end_char": entity.end_char,
                "confidence_score": entity.confidence_score,
                "detector": entity.detector,
            }
            for entity in state.resolved_entities
        ]

        text_to_run = state.original_text
        offset = 0
        if candidate_summary.get("candidates") and len(state.original_text) > 400:
            first_c = candidate_summary["candidates"][0]
            c_start = first_c.get("start", 0)
            c_end = first_c.get("end", len(state.original_text))
            w_start = max(0, c_start - 200)
            w_end = min(len(state.original_text), c_end + 200)
            while w_start > 0 and state.original_text[w_start - 1] != "\n":
                w_start -= 1
            while w_end < len(state.original_text) and state.original_text[w_end] != "\n":
                w_end += 1
            if (w_end - w_start) < len(state.original_text):
                text_to_run = state.original_text[w_start:w_end]
                offset = w_start

        self._attach_orchestration_context(
            detector,
            state,
            remaining_text=text_to_run,
            candidate_summary=candidate_summary,
            context_offset=offset,
            known_entities=known_entities,
        )

        start_time = time.perf_counter()
        raw_results = detector.detect(text_to_run, page_number=page_number)
        duration = time.perf_counter() - start_time
        state.log_time(detector.name, duration)

        if offset > 0:
            self._offset_entities(raw_results, offset)

        accepted = []
        for entity in raw_results:
            if not self._is_valid_entity(entity, len(state.original_text)):
                continue
            if state.is_span_unmasked(entity.start_char, entity.end_char, min_confidence=0.80):
                accepted.append(entity)

        state.add_entities(accepted, detector_name=detector.name)
        return accepted
    ENTITY_SPECIALIZATIONS = {
        "PERSON": {"PATIENT", "DOCTOR", "PHYSICIAN", "NURSE", "PROVIDER", "HEALTHCARE_STAFF", "CARDHOLDER_NAME", "MEDICATION"},
        "ORGANIZATION": {"HOSPITAL", "CLINIC", "MEDICAL_FACILITY", "HEALTHCARE_ORGANIZATION", "INSURANCE_PROVIDER", "ORGANIZATION_CONTACT_INFO", "MEDICATION"},
        "LOCATION": {"ADDRESS", "CITY_STATE_ZIP", "FACILITY_ADDRESS", "CITY", "STATE", "ZIP_CODE"},
        "DATE_TIME": {"DATE", "DATE_OF_BIRTH", "DATE_OF_SERVICE", "ADMISSION_DATE", "DISCHARGE_DATE", "DOCUMENT_CREATION_DATE", "COVERAGE_DATE", "DUE_DATE", "VISIT_DATE", "START_DATE"},
        "PHONE_NUMBER": {"US_PHONE_NUMBER", "CUSTOMER_SERVICE_NUMBER", "ORGANIZATION_CONTACT_INFO"},
    }

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

            prev_type = previous.entity_type.upper()
            is_same_type = (prev_type == entity_type)
            is_specialization = (
                entity_type in DetectionService.ENTITY_SPECIALIZATIONS.get(prev_type, set())
            )
            is_reverse_specialization = (
                prev_type in DetectionService.ENTITY_SPECIALIZATIONS.get(entity_type, set())
            )

            if not (is_same_type or is_specialization or is_reverse_specialization):
                continue
            if not DetectionService._is_duplicate_span_or_value(previous, entity):
                continue

            should_replace = DetectionService._should_replace_previous_entity(
                previous,
                entity,
                mask_confidence_threshold,
                is_specialization=is_specialization,
            )
            if should_replace:
                previous_detector = previous.detector
                previous_confidence = previous.confidence_score
                DetectionService._copy_detection_result(previous, entity)
                previous.metadata["upgraded_from_detector"] = previous_detector
                previous.metadata["upgraded_from_confidence"] = previous_confidence
                previous.metadata["upgraded_by_duplicate"] = True
                entity.metadata["duplicate_upgraded_previous"] = True
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
        is_specialization: bool = False,
    ) -> bool:
        # Never downgrade or replace an authoritative high-confidence regex detection unless explicitly specializing
        if previous.confidence_score >= 0.80 and getattr(previous, "detector", "").lower() == "regex" and not is_specialization:
            return False

        # 1. Higher confidence replacement
        if entity.confidence_score > previous.confidence_score:
            return True

        # 2. Specialize a generic entity (e.g. PERSON -> PATIENT/DOCTOR) with solid confidence
        if is_specialization and entity.confidence_score >= 0.70:
            return True

        if mask_confidence_threshold is None:
            return False

        # 3. Upgrade low-confidence detections
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
        target.entity_type = source.entity_type
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
                document_type=document_type,
            )

            self._log_pipeline_summary(state, results, document_type)

            self.last_pipeline_state = state
            self.last_llm_candidate_audit = state.llm_candidate_audit

            return results

        except Exception as exc:
            logger.exception("Detection pipeline failed at stage: %s", current_stage)
            raise DetectionError(
                f"Detection failed at Stage {current_stage}: {exc}"
            ) from exc

    def _log_pipeline_summary(
        self,
        state: PipelineState,
        results: list[DetectionResult],
        document_type: str | None,
    ) -> None:
        """Logs structured detection and LLM optimization summary telemetry."""
        m = state.pipeline_metrics
        det_stats = m.get("detector_breakdown", {})

        logger.info("==================================================")
        logger.info("DETECTION PIPELINE SUMMARY")
        logger.info("==================================================")
        logger.info("document_type=%s", document_type or "Generic / Unspecified")
        logger.info("total_detector_results=%d", m.get("total_detector_candidates", 0))

        for det_name, s in det_stats.items():
            logger.info(
                "  detector=%s: candidates=%d locked=%d suppressed=%d pre_llm_rejected=%d pending=%d",
                det_name,
                s.get("candidates", 0),
                s.get("locked", 0),
                s.get("duplicates_suppressed", 0),
                s.get("pre_llm_rejected", 0),
                s.get("pending_for_llm", 0),
            )

        logger.info("--------------------------------------------------")
        logger.info("high_confidence_locked=%d", m.get("high_confidence_locked", 0))
        logger.info("duplicate_suppressed=%d", m.get("duplicate_suppressed", 0))
        logger.info("low_confidence_candidates=%d", m.get("pre_llm_rejected", 0) + m.get("sent_to_llm_validation", 0))
        logger.info("filtered_before_llm=%d", m.get("pre_llm_rejected", 0))
        logger.info("sent_to_llm_validation=%d", m.get("sent_to_llm_validation", 0))
        logger.info("llm_confirmed=%d", m.get("llm_confirmed", 0))
        logger.info("llm_reclassified=%d", m.get("llm_reclassified", 0))
        logger.info("llm_rejected=%d", m.get("llm_rejected", 0))
        logger.info("llm_residual_entities=%d", m.get("llm_residual_entities", 0))

        pii_count = sum(1 for e in results if getattr(e, "privacy_category", "") == "PII")
        phi_count = sum(1 for e in results if getattr(e, "privacy_category", "") == "PHI")
        logger.info("final_entities=%d (PII=%d, PHI=%d)", len(results), pii_count, phi_count)

        total_low = m.get("pre_llm_rejected", 0) + m.get("sent_to_llm_validation", 0)
        saved = m.get("pre_llm_rejected", 0)
        reduction_pct = (saved / total_low * 100.0) if total_low > 0 else 0.0

        logger.info("==================================================")
        logger.info("LLM USAGE SUMMARY")
        logger.info("==================================================")
        logger.info("validation_candidates=%d", m.get("sent_to_llm_validation", 0))
        logger.info("residual_detection_chunks=%d", len(getattr(state, "detection_history", [])))
        logger.info("total_llm_calls=%d", m.get("sent_to_llm_validation", 0))
        logger.info("validation_rejected=%d", m.get("llm_rejected", 0))
        logger.info("validation_confirmed=%d", m.get("llm_confirmed", 0))
        logger.info("validation_reclassified=%d", m.get("llm_reclassified", 0))
        logger.info("new_entities_discovered=%d", m.get("llm_residual_entities", 0))
        logger.info("raw_low_confidence_candidates=%d", total_low)
        logger.info("llm_calls_avoided=%d (reduction=%.1f%%)", saved, reduction_pct)
        logger.info("==================================================")

    def _execute_dynamic_orchestration(
        self,
        state: PipelineState,
        page_number: int,
        config: DynamicDetectionConfig,
        document_type: str | None = None,
    ) -> tuple[str, tuple[str, ...]]:
        self._current_document_type = document_type
        domain = self.router.classify_domain(
            state.original_text,
            document_type=document_type,
        )
        route = self.router.route_for_domain(domain)
        detector_getters = self._detector_getters()

        # Generate semantic chunks as the common detection input
        semantic_chunks = self.chunker.chunk_document(state.original_text)
        total_doc_len = len(state.original_text)
        covered_indices = set()
        for c in semantic_chunks:
            covered_indices.update(range(c.start_char, c.end_char))
        covered_chars = len(covered_indices)
        uncovered_chars = max(0, total_doc_len - covered_chars)
        coverage_pct = (covered_chars / total_doc_len * 100.0) if total_doc_len > 0 else 100.0

        logger.info("==================================================")
        logger.info("DETECTION PIPELINE EXECUTION (Page %d)", page_number)
        logger.info("Document Type: %s | Domain: %s", document_type or "Unspecified", domain)
        logger.info("Orchestration Route: %s", " -> ".join(route))
        logger.info(
            "DocumentCoverage: document_id=%s number_of_chunks=%d total_document_length=%d covered_characters=%d uncovered_characters=%d coverage_percentage=%.2f%%",
            getattr(state, "document_id", "doc"),
            len(semantic_chunks),
            total_doc_len,
            covered_chars,
            uncovered_chars,
            coverage_pct,
        )
        logger.info("==================================================")

        route_iterations = 0
        selected_detector_names: set[str] = set()
        max_route_iterations = len(route) + 1

        while route_iterations < max_route_iterations:
            route_iterations += 1
            selection = self.router.select_next_detector(
                state=state,
                detector_getters=detector_getters,
                route=route,
                stopping_candidate_threshold=(
                    config.stopping_candidate_threshold
                ),
                min_candidate_chars=config.min_candidate_chars,
                continuation_confidence_threshold=config.high_confidence_threshold,
                exhaust_route=False,
            )

            if selection.detector is None:
                logger.info(
                    "Detection Route Finished: %s (Remaining candidates: %d)",
                    selection.reason,
                    selection.remaining_candidates["count"],
                )
                break

            detector = selection.detector
            detector_name = detector.name.lower()

            if detector_name in selected_detector_names:
                logger.error(
                    "Detection route stopped by no-progress guard: detector=%s "
                    "was selected more than once iteration=%d max_iterations=%d",
                    detector.name,
                    route_iterations,
                    max_route_iterations,
                )
                break
            selected_detector_names.add(detector_name)

            logger.info(
                ">>> [DETECTOR RUN: %s] Reason: %s | Unresolved candidates remaining: %d",
                detector.name,
                selection.reason,
                selection.remaining_candidates["count"],
            )

            # Gemma has a dedicated, bounded two-phase path below: residual
            # discovery first, then batch candidate validation. Deferring it
            # here prevents the generic detector loop from invoking the same
            # expensive model repeatedly or validating before discovery.
            if detector_name in self.LLM_DETECTOR_NAMES:
                logger.info(
                    "Deferring detector=%s to bounded residual discovery and "
                    "candidate validation phases",
                    detector.name,
                )
                break

            before_count = len(state.resolved_entities)
            new_entities = self._run_detector_on_chunks(
                detector=detector,
                chunks=semantic_chunks,
                state=state,
                page_number=page_number,
                allow_claimed_spans=False,
            )
            self._calibrate_confidence(state.resolved_entities, config)
            remaining = state.remaining_candidate_summary(
                min_chars=config.min_candidate_chars,
            )
            logger.info(
                "--- [DETECTOR FINISHED: %s] Found %d new entity/entities | Total resolved: %d | Candidates left: %d",
                detector.name,
                len(new_entities),
                len(state.resolved_entities),
                remaining["count"],
            )

            if len(state.resolved_entities) == before_count and not new_entities:
                logger.info(
                    "Detector %s found 0 new entities; candidates remaining=%d",
                    detector.name,
                    remaining["count"],
                )

        else:
            logger.error(
                "Detection route stopped at maximum iteration guard: "
                "iterations=%d route_length=%d",
                route_iterations,
                len(route),
            )

        # PHASE 4: High-Recall Residual Entity Discovery with the active LLM
        # (Runs on uncovered / partially covered chunks to recover missed entities BEFORE validation)
        bypass_llm = os.getenv("BYPASS_LLM", "false").lower() in {"1", "true", "yes"}
        llm_detector = None
        if not bypass_llm:
            llm_detector = self.gemma
            provider_name, model_name = self._llm_log_context(llm_detector)
            logger.info(
                ">>> [PHASE 4: RESIDUAL ENTITY DISCOVERY] Running coverage analysis "
                "and residual discovery provider=%s model=%s",
                provider_name,
                model_name,
            )
            self._execute_gemma_residual_discovery(
                detector=llm_detector,
                state=state,
                semantic_chunks=semantic_chunks,
                config=config,
                document_type=document_type,
                page_number=page_number,
            )

        # PHASE 5: Contextual LLM Validation for the Combined Candidate Pool
        # (Validates all existing low-confidence detector candidates + new Phase 4 residual candidates)
        if state.pending_candidates and not bypass_llm:
            logger.info(
                ">>> [PHASE 5: LLM CANDIDATE VALIDATION] Validating %d combined "
                "candidate(s) provider=%s model=%s "
                "(CONFIRM / RECLASSIFY / REJECT)",
                len(state.pending_candidates),
                provider_name,
                model_name,
            )
            self._execute_qwen_candidate_validation(
                detector=llm_detector,
                state=state,
                config=config,
                document_type=document_type,
            )

        return domain, route

    @classmethod
    def evaluate_chunk_coverage(
        cls,
        chunk: DocumentChunk,
        resolved_entities: list[DetectionResult],
        original_text: str,
        document_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Span-Level and Semantic Region Coverage Decision Function (Phase 4).

        Evaluates whether a chunk is genuinely fully resolved vs containing meaningful
        unresolved intervals that could harbor sensitive PII/PHI/financial data.
        Coverage percentage is logged as telemetry, but safety decisions are based on
        unresolved semantic interval analysis.
        """
        chunk_len = len(chunk.text)
        if chunk_len == 0:
            return {
                "coverage_status": "FULLY_COVERED",
                "coverage_percentage": 100.0,
                "resolved_spans": 0,
                "unresolved_regions": 0,
                "meaningful_unresolved_regions": 0,
                "high_risk_context": False,
                "skip_residual_detection": True,
                "reason": "Empty chunk",
            }

        # 1. Collect entity spans within this chunk
        chunk_entities = [
            e for e in resolved_entities
            if max(chunk.start_char, e.start_char) < min(chunk.end_char, e.end_char)
        ]

        if not chunk_entities:
            has_meaningful_text = bool(re.search(r"[a-zA-Z0-9]", chunk.text))
            return {
                "coverage_status": "UNCOVERED",
                "coverage_percentage": 0.0,
                "resolved_spans": 0,
                "unresolved_regions": 1 if has_meaningful_text else 0,
                "meaningful_unresolved_regions": 1 if has_meaningful_text else 0,
                "high_risk_context": False,
                "skip_residual_detection": not has_meaningful_text,
                "reason": "No detector detections in chunk; full residual security review required.",
            }

        # 2. Convert and merge relative spans
        rel_spans: list[tuple[int, int]] = []
        for e in chunk_entities:
            s = max(0, e.start_char - chunk.start_char)
            end = min(chunk_len, e.end_char - chunk.start_char)
            if s < end:
                rel_spans.append((s, end))

        rel_spans.sort(key=lambda x: x[0])
        merged_spans: list[tuple[int, int]] = []
        for s, end in rel_spans:
            if not merged_spans:
                merged_spans.append((s, end))
            else:
                last_s, last_end = merged_spans[-1]
                if s <= last_end:
                    merged_spans[-1] = (last_s, max(last_end, end))
                else:
                    merged_spans.append((s, end))

        # 3. Calculate unresolved intervals
        unresolved_intervals: list[tuple[int, int]] = []
        curr = 0
        for s, end in merged_spans:
            if s > curr:
                unresolved_intervals.append((curr, s))
            curr = max(curr, end)
        if curr < chunk_len:
            unresolved_intervals.append((curr, chunk_len))

        # 4. Analyze unresolved intervals for meaningful content and high-risk context
        total_covered_chars = sum(end - s for s, end in merged_spans)
        coverage_percentage = round((total_covered_chars / max(1, chunk_len)) * 100.0, 1)

        meaningful_unresolved_count = 0
        high_risk_context_flag = False

        HIGH_RISK_CUES = {
            "account", "acct", "holder", "patient", "mrn", "member", "policy", "dob",
            "birth", "ssn", "tax", "pan", "aadhaar", "passport", "rx", "diagnosis",
            "condition", "medication", "prescribed", "dr.", "doctor", "physician",
            "hospital", "clinic", "address", "phone", "mobile", "card", "cvv",
            "amount", "balance", "total", "claim", "employer", "tin", "cin", "npi",
        }

        for u_start, u_end in unresolved_intervals:
            raw_text = chunk.text[u_start:u_end]
            stripped = raw_text.strip()
            if not stripped or len(stripped) < 2 or not any(c.isalnum() for c in stripped):
                continue

            label_candidate = re.sub(
                r"^[\s\[\](){}|,;]+|[\s\[\](){}|,;]+$",
                "",
                raw_text.strip(),
            )
            is_pure_label_prompt = bool(
                re.match(r"^[A-Za-z\s\-_/]+[:|\-]\s*$", label_candidate)
            )
            if is_pure_label_prompt:
                continue

            words = [w for w in re.split(r"[\s,:;|/\-]+", stripped) if w]
            if not words:
                continue

            has_digits = any(any(c.isdigit() for c in w) for w in words)
            has_cap_words = any(w[0].isupper() for w in words if w.isalpha())
            has_significant_length = len(stripped) >= 4

            if has_digits or has_cap_words or has_significant_length:
                meaningful_unresolved_count += 1
                surrounding_start = max(0, u_start - 30)
                surrounding_context = chunk.text[surrounding_start:u_end].lower()
                if any(cue in surrounding_context for cue in HIGH_RISK_CUES):
                    high_risk_context_flag = True

        # 5. Determine Coverage Status based on unresolved semantic regions
        if meaningful_unresolved_count == 0:
            coverage_status = "FULLY_COVERED"
            skip_residual = True
            reason = f"All meaningful semantic regions resolved by {len(merged_spans)} span(s); remaining text is whitespace/delimiters."
        elif coverage_percentage < 35.0 or meaningful_unresolved_count >= 3:
            coverage_status = "INSUFFICIENTLY_COVERED"
            skip_residual = False
            reason = f"Sparse coverage ({coverage_percentage}%) with {meaningful_unresolved_count} meaningful unresolved region(s)."
        else:
            coverage_status = "PARTIALLY_COVERED"
            skip_residual = False
            risk_note = " (High-risk context detected)" if high_risk_context_flag else ""
            reason = f"Coverage {coverage_percentage}%, but {meaningful_unresolved_count} unresolved region(s) remain{risk_note}."

        return {
            "coverage_status": coverage_status,
            "coverage_percentage": coverage_percentage,
            "resolved_spans": len(merged_spans),
            "unresolved_regions": len(unresolved_intervals),
            "meaningful_unresolved_regions": meaningful_unresolved_count,
            "high_risk_context": high_risk_context_flag,
            "skip_residual_detection": skip_residual,
            "reason": reason,
        }

    def _execute_gemma_residual_discovery(
        self,
        detector: BaseDetector,
        state: PipelineState,
        semantic_chunks: list[DocumentChunk],
        config: DynamicDetectionConfig,
        document_type: str | None = None,
        page_number: int = 1,
    ) -> list[DetectionResult]:
        """
        Phase 4: Exhaustive High-Recall Residual Entity Discovery.

        Evaluates coverage across all semantic chunks and dispatches Gemma to inspect
        uncovered / insufficiently covered regions for sensitive entities missed by upstream detectors.
        Discovered candidates are merged into state.pending_candidates for Phase 5 validation.
        """
        if not semantic_chunks:
            return []

        remaining_candidates = state.remaining_candidate_summary(
            min_chars=config.min_candidate_chars,
        )
        bounded_contexts = self._qwen_contexts(
            state,
            remaining_candidates,
            config,
        )
        if not bounded_contexts:
            return []

        provider_name, model_name = self._llm_log_context(detector)

        semantic_chunks = [
            DocumentChunk(
                chunk_id=index,
                text=context["text"],
                start_char=context["start"],
                end_char=context["end"],
                metadata={"bounded_llm_context": True},
            )
            for index, context in enumerate(bounded_contexts, start=1)
        ]

        start_residual = time.perf_counter()
        total_chunks = len(semantic_chunks)
        fully_covered = 0
        partially_covered = 0
        insufficiently_covered = 0
        uncovered = 0
        sent_to_gemma = 0
        discovered_entities: list[DetectionResult] = []
        duplicates_suppressed = 0
        failures = 0

        logger.info(
            ">>> [PHASE 4: COVERAGE ANALYSIS] Analyzing %d semantic chunk(s) for residual discovery...",
            total_chunks,
        )

        for chunk in semantic_chunks:
            chunk_len = len(chunk.text.strip())
            if chunk_len < 5:
                continue

            # Evaluate chunk coverage using span-level & semantic region analysis
            coverage_eval = self.evaluate_chunk_coverage(
                chunk=chunk,
                resolved_entities=state.resolved_entities,
                original_text=state.original_text,
                document_type=document_type,
            )

            coverage_status = coverage_eval["coverage_status"]
            if coverage_status == "FULLY_COVERED":
                fully_covered += 1
            elif coverage_status == "PARTIALLY_COVERED":
                partially_covered += 1
            elif coverage_status == "INSUFFICIENTLY_COVERED":
                insufficiently_covered += 1
            else:
                uncovered += 1

            logger.info(
                "ResidualCoverage: doc_id=doc chunk_id=%d coverage=%.1f%% "
                "status=%s resolved_spans=%d unresolved_regions=%d "
                "meaningful_unresolved_regions=%d high_risk_context=%s "
                "action=%s llm_provider=%s llm_model=%s reason=%r",
                chunk.chunk_id,
                coverage_eval["coverage_percentage"],
                coverage_status,
                coverage_eval["resolved_spans"],
                coverage_eval["unresolved_regions"],
                coverage_eval["meaningful_unresolved_regions"],
                coverage_eval["high_risk_context"],
                "SKIP" if coverage_eval["skip_residual_detection"] else "SEND_TO_LLM",
                provider_name,
                model_name,
                coverage_eval["reason"],
            )

            # Skip chunk only if all meaningful content is genuinely resolved
            if coverage_eval["skip_residual_detection"]:
                continue

            sent_to_gemma += 1
            start_chunk_call = time.perf_counter()

            chunk_entities = [
                e for e in state.resolved_entities
                if max(chunk.start_char, e.start_char) < min(chunk.end_char, e.end_char)
            ]

            # Execute Gemma High-Recall Residual Discovery
            chunk_results = []
            if hasattr(detector, "detect_residual_chunk"):
                chunk_results = detector.detect_residual_chunk(
                    chunk_text=chunk.text,
                    chunk_start=chunk.start_char,
                    chunk_end=chunk.end_char,
                    known_entities=chunk_entities,
                    document_type=document_type,
                    page_number=page_number,
                )
            elif hasattr(detector, "detect"):
                known_entity_metadata = self._known_entities_for_qwen_context(
                    state,
                    chunk.start_char,
                    chunk.end_char,
                    config,
                )
                self._attach_orchestration_context(
                    detector,
                    state,
                    remaining_text=chunk.text,
                    candidate_summary=state.remaining_candidate_summary(
                        min_chars=config.min_candidate_chars,
                    ),
                    context_offset=chunk.start_char,
                    known_entities=known_entity_metadata,
                )
                chunk_results = detector.detect(
                    text=chunk.text,
                    page_number=page_number,
                )
                if chunk.start_char:
                    self._offset_entities(chunk_results, chunk.start_char)

            chunk_latency = (time.perf_counter() - start_chunk_call) * 1000.0

            valid_for_chunk = []
            for item in chunk_results:
                # Ensure global coordinates match original text verbatim
                if item.start_char < 0 or item.end_char > len(state.original_text):
                    continue
                actual_text = state.original_text[item.start_char:item.end_char]
                if actual_text.strip() != item.entity_value.strip():
                    continue

                # Check if span is unmasked and does not overlap locked authoritative spans
                if not state.is_span_unmasked(item.start_char, item.end_char):
                    logger.info(
                        "ResidualDuplicateSuppressed: type=%r span=%d-%d reason='Overlaps locked/resolved span'",
                        item.entity_type,
                        item.start_char,
                        item.end_char,
                    )
                    duplicates_suppressed += 1
                    continue

                active_model_name = model_name
                item.detector = getattr(detector, "name", "llm")
                item.metadata["llm_mode"] = "RESIDUAL_DETECTION"
                item.metadata["original_detector"] = active_model_name
                item.metadata["validator"] = active_model_name
                item.metadata["residual_discovery"] = True
                item.metadata["chunk_text"] = chunk.text
                item.metadata["chunk_id"] = chunk.chunk_id

                # Deduplicate against existing pending candidates
                existing_match = next(
                    (p for p in state.pending_candidates if (p.start_char, p.end_char) == (item.start_char, item.end_char)),
                    None,
                )
                if existing_match:
                    existing_match.confidence_score = max(existing_match.confidence_score, item.confidence_score)
                    continue

                valid_for_chunk.append(item)
                discovered_entities.append(item)
                state.pending_candidates.append(item)

                logger.info(
                    "LLMResidualDetection: doc_id=doc chunk_id=%d type=%r span=%d-%d confidence=%.2f detector=%s mode=RESIDUAL_DETECTION status=ADDED_TO_VALIDATION_POOL",
                    chunk.chunk_id,
                    item.entity_type,
                    item.start_char,
                    item.end_char,
                    item.confidence_score,
                    active_model_name,
                )

            logger.info(
                "ResidualChunkReview: doc_id=doc chunk_id=%d span=%d-%d coverage=%s existing_entities=%d entities_found=%d latency=%.1fms status=%s",
                chunk.chunk_id,
                chunk.start_char,
                chunk.end_char,
                coverage_status,
                len(chunk_entities),
                len(valid_for_chunk),
                chunk_latency,
                "DISCOVERY_COMPLETED",
            )

        total_latency = (time.perf_counter() - start_residual) * 1000.0
        avg_latency = total_latency / max(1, sent_to_gemma)

        # Update pipeline metrics
        state.pipeline_metrics["total_chunks"] = total_chunks
        state.pipeline_metrics["fully_covered_chunks"] = fully_covered
        state.pipeline_metrics["partially_covered_chunks"] = partially_covered
        state.pipeline_metrics["insufficiently_covered_chunks"] = insufficiently_covered
        state.pipeline_metrics["uncovered_chunks"] = uncovered
        state.pipeline_metrics["chunks_sent_to_gemma"] = sent_to_gemma
        state.pipeline_metrics["llm_residual_entities"] += len(discovered_entities)
        state.pipeline_metrics["llm_residual_duplicates_suppressed"] = duplicates_suppressed
        state.pipeline_metrics["llm_residual_failures"] = failures

        logger.info(
            "==================================================\n"
            "%s Residual Discovery Summary\n"
            "==================================================\n"
            "Total chunks: %d\n"
            "Fully covered: %d\n"
            "Partially covered: %d\n"
            "Insufficiently covered: %d\n"
            "Uncovered: %d\n"
            "Chunks sent to %s: %d\n"
            "Residual candidates added: %d\n"
            "Duplicates suppressed: %d\n"
            "Failures: %d\n"
            "Model: %s\n"
            "Average latency: %.1fms\n"
            "Total latency: %.1fms\n"
            "==================================================",
            provider_name,
            total_chunks,
            fully_covered,
            partially_covered,
            insufficiently_covered,
            uncovered,
            provider_name,
            sent_to_gemma,
            len(discovered_entities),
            duplicates_suppressed,
            failures,
            model_name,
            avg_latency,
            total_latency,
        )

        return discovered_entities

    def _execute_qwen_candidate_validation(
        self,
        detector: BaseDetector,
        state: PipelineState,
        config: DynamicDetectionConfig,
        document_type: str | None = None,
    ) -> None:
        """
        Phase 5: Contextual Candidate Validation for the Combined Candidate Pool.

        Validates all low-confidence detector candidates + newly discovered Phase 4 residual candidates.
        """
        return self._execute_gemma_candidate_validation_impl(detector, state, config, document_type)

    def _execute_gemma_candidate_validation(
        self,
        detector: BaseDetector,
        state: PipelineState,
        config: DynamicDetectionConfig,
        document_type: str | None = None,
    ) -> None:
        return self._execute_gemma_candidate_validation_impl(detector, state, config, document_type)

    def _execute_gemma_candidate_validation_impl(
        self,
        detector: BaseDetector,
        state: PipelineState,
        config: DynamicDetectionConfig,
        document_type: str | None = None,
    ) -> None:
        if not state.pending_candidates:
            return

        provider_name, model_name = self._llm_log_context(detector)

        all_chunks = self.chunker.chunk_document(state.original_text)
        pending_cands = list(state.pending_candidates)
        validated = detector.validate_candidates(
            pending_cands,
            all_chunks,
            document_type=document_type,
        )

        validated_spans = {(e.start_char, e.end_char) for e in validated}
        for cand in pending_cands:
            cand_id = cand.metadata.get("candidate_id", "cand")
            if (cand.start_char, cand.end_char) in validated_spans:
                match = next(e for e in validated if (e.start_char, e.end_char) == (cand.start_char, cand.end_char))
                decision = match.metadata.get("gemma_validation") or match.metadata.get("qwen_validation", "CONFIRM")
                raw_reason = match.metadata.get("gemma_reason") or match.metadata.get("qwen_reason")
                val_text = match.entity_value or cand.entity_value or ""
                val_type = match.entity_type or cand.entity_type or "ENTITY"
                if raw_reason and not raw_reason.lower().startswith("validated by"):
                    reason = raw_reason
                elif decision == "RECLASSIFY":
                    reason = f"Reclassified '{val_text}' from {cand.entity_type} to {val_type} based on structural document context."
                elif "FINANCIAL" in val_type or val_type in {"MONEY", "SALARY", "COST"}:
                    reason = f"Confirmed monetary amount '{val_text}' as sensitive financial data."
                elif "PERSON" in val_type or val_type in {"PATIENT", "DOCTOR", "PHYSICIAN"}:
                    reason = f"Validated person identity '{val_text}' within document context."
                elif "ORGANIZATION" in val_type or val_type in {"HOSPITAL", "INSURANCE_PROVIDER"}:
                    reason = f"Confirmed organizational entity '{val_text}' in enterprise document context."
                else:
                    reason = f"Validated '{val_text}' as a sensitive {val_type} entity within document context."

                if decision == "RECLASSIFY":
                    state.pipeline_metrics["llm_reclassified"] += 1
                else:
                    state.pipeline_metrics["llm_confirmed"] += 1

                orig_det = match.detector or cand.metadata.get("original_detector") or cand.detector
                orig_mode = cand.metadata.get("llm_mode", "VALIDATION")
                llm_model_name = model_name
                state.record_llm_candidate(
                    candidate_value=match.entity_value,
                    entity_type=match.entity_type,
                    original_type=cand.entity_type,
                    decision=decision,
                    confidence=match.confidence_score,
                    reasoning=reason,
                    start_char=match.start_char,
                    end_char=match.end_char,
                    detector=llm_model_name,
                    page_number=match.page_number,
                )

                logger.info(
                    "LLMValidation: doc_id=doc candidate_id=%s provider=%s "
                    "model=%s mode=VALIDATION decision=%s original_type=%r "
                    "final_type=%r confidence=%.2f",
                    cand_id,
                    provider_name,
                    model_name,
                    decision,
                    cand.entity_type,
                    match.entity_type,
                    match.confidence_score,
                )
            else:
                state.pipeline_metrics["llm_rejected"] += 1
                rej_raw = cand.metadata.get("gemma_reason") or cand.metadata.get("qwen_reason")
                if rej_raw and not rej_raw.lower().startswith("contextual noise"):
                    rejection_reason = rej_raw
                else:
                    rejection_reason = f"Rejected '{cand.entity_value}' as non-sensitive text fragment or structural noise."

                orig_det = cand.metadata.get("original_detector") or cand.detector
                llm_model_name = model_name
                state.record_llm_candidate(
                    candidate_value=cand.entity_value,
                    entity_type=cand.entity_type,
                    decision="REJECT",
                    confidence=cand.confidence_score,
                    reasoning=rejection_reason,
                    start_char=cand.start_char,
                    end_char=cand.end_char,
                    detector=llm_model_name,
                    page_number=cand.page_number,
                )
                logger.info(
                    "LLMValidation: doc_id=doc candidate_id=%s provider=%s "
                    "model=%s mode=VALIDATION decision=REJECT "
                    "original_type=%r final_type=null",
                    cand_id,
                    provider_name,
                    model_name,
                    cand.entity_type,
                )

        state.add_entities(
            validated,
            detector_name=getattr(detector, "name", "llm"),
            mask_confidence_threshold=config.high_confidence_threshold,
        )
        state.clear_pending_candidates()

    def _run_qwen_detector(
        self,
        detector: BaseDetector,
        state: PipelineState,
        page_number: int,
        remaining_candidates: dict,
        config: DynamicDetectionConfig,
    ) -> list[DetectionResult]:
        provider_name, model_name = self._llm_log_context(detector)

        # 1. Contextual Validation Phase for low-confidence candidates
        if state.pending_candidates:
            self._execute_qwen_candidate_validation(
                detector=detector,
                state=state,
                config=config,
                document_type=getattr(self, "_current_document_type", None),
            )

        # 2. Residual Entity Discovery Phase
        contexts = self._qwen_contexts(
            state,
            remaining_candidates,
            config,
        )
        if not contexts:
            logger.info(
                "Skipping LLM residual discovery provider=%s model=%s because "
                "no unresolved candidate or low-confidence context remains",
                provider_name,
                model_name,
            )
            state.add_entities([], detector.name)
            return []

        logger.info(
            "Running LLM residual discovery provider=%s model=%s on %d "
            "bounded context(s), max_contexts=%d window=%d",
            provider_name,
            model_name,
            len(contexts),
            self.QWEN_MAX_CONTEXTS,
            self.QWEN_CONTEXT_WINDOW,
        )
        collected: list[DetectionResult] = []
        for context in contexts:
            discovered = self._run_detector(
                detector,
                state,
                page_number,
                custom_text=context["text"],
                context_offset=context["start"],
                allow_claimed_spans=True,
                known_entities=context.get("known_entities", []),
            )
            for item in discovered:
                state.record_llm_candidate(
                    candidate_value=item.entity_value,
                    entity_type=item.entity_type,
                    decision="ACCEPT",
                    confidence=item.confidence_score,
                    reasoning=item.metadata.get("qwen_reason", "Discovered during LLM residual context extraction"),
                    start_char=item.start_char,
                    end_char=item.end_char,
                    detector=item.detector,
                    page_number=item.page_number,
                )
            collected.extend(discovered)
            logger.info(
                "LLMResidualDetection: provider=%s model=%s chunk_span=%d-%d "
                "known_entities=%d new_entities_found=%d",
                provider_name,
                model_name,
                context["start"],
                context["end"],
                len(context.get("known_entities", [])),
                len(discovered),
            )

        state.pipeline_metrics["llm_residual_entities"] += len(collected)
        return collected

    def _qwen_contexts(
        self,
        state: PipelineState,
        remaining_candidates: dict,
        config: DynamicDetectionConfig,
    ) -> list[dict]:
        candidates = remaining_candidates.get("candidates", [])

        low_confidence_entities = [
            entity for entity in state.resolved_entities
            if entity.confidence_score < config.high_confidence_threshold
            and self._is_valid_entity(entity, len(state.original_text))
            and state.is_span_unmasked(entity.start_char, entity.end_char)
        ]

        if candidates:
            return self._qwen_original_contexts_for_candidates(state, candidates, config)

        all_chunks = self.chunker.chunk_document(state.original_text)
        relevant_chunks = self.chunker.select_relevant_chunks(
            all_chunks,
            candidates=candidates,
            low_confidence_entities=low_confidence_entities,
            resolved_entities=state.resolved_entities,
            max_chunks=self.QWEN_MAX_CONTEXTS,
        )

        contexts: list[dict] = []
        for chunk in relevant_chunks:
            contexts.append(
                {
                    "start": chunk.start_char,
                    "end": chunk.end_char,
                    "text": chunk.text,
                    "known_entities": self._known_entities_for_qwen_context(
                        state,
                        chunk.start_char,
                        chunk.end_char,
                        config,
                    ),
                }
            )

        return contexts

    def _qwen_original_contexts_for_candidates(
        self,
        state: PipelineState,
        candidates: list[dict],
        config: DynamicDetectionConfig,
    ) -> list[dict]:
        contexts: list[dict] = []
        seen_ranges: set[tuple[int, int]] = set()

        high_risk_cues = re.compile(
            r"\b(?:account|acct|beneficiary|routing|ssn|social security|"
            r"passport|tax|member|policy|claim|mrn|medical record|dob|"
            r"date of birth|card|cvv|bank)\b",
            re.IGNORECASE,
        )

        def priority(candidate: dict) -> tuple[int, int]:
            start = int(candidate.get("start", 0))
            end = int(candidate.get("end", start))
            surrounding = state.original_text[
                max(0, start - self.QWEN_CONTEXT_WINDOW):
                min(len(state.original_text), end + 20)
            ]
            score = 0
            if high_risk_cues.search(surrounding):
                score += 100
            value = str(candidate.get("text", ""))
            if re.search(r"(?i)(?=.*\d)[A-Z0-9][A-Z0-9_-]{7,}", value):
                score += 20
            if candidate.get("kind") == "label_value":
                score += 5
            return score, -start

        prioritized_candidates = sorted(
            candidates,
            key=priority,
            reverse=True,
        )

        for candidate in prioritized_candidates[: self.QWEN_MAX_CONTEXTS]:
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
        document_type: str | None = None,
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

        results = EntityMapper.normalize(results, document_type=document_type)
        results = self._filter_valid_entities(
            results,
            len(state.original_text),
            "finalize",
        )

        # Exclude DROP entities per enterprise taxonomy
        results = [
            entity for entity in results
            if not TaxonomyService.is_drop(entity.entity_type, document_type)
        ]

        # Exclude low-confidence unvalidated noise (< 0.60)
        results = [
            entity for entity in results
            if entity.confidence_score >= 0.60
        ]

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
                    "CITY_STATE_ZIP",
                    "CLINICAL_SECTION",
                    "PHONE_NUMBER",
                    "US_PHONE_NUMBER",
                    "CUSTOMER_SERVICE_NUMBER",
                    "ORGANIZATION_CONTACT_INFO",
                }
            ):
                logger.info(
                    "Discarding entity type=%s span=%d-%d because it crosses line boundaries",
                    entity.entity_type,
                    entity.start_char,
                    entity.end_char,
                )
                continue
            filtered_results.append(entity)
        results = filtered_results

        # 2. Merge multi-line addresses (e.g. Street + City/State/Zip on line 2)
        results = self._merge_adjacent_address_lines(
            state.original_text,
            results,
            document_type=document_type,
        )

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

        # 5. Contextual Re-classification (applies to all entities including safety net)
        results = self._contextual_reclassify(state.original_text, results)

        # 6. Medication-Dosage Association
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

    def _merge_adjacent_address_lines(
        self,
        text: str,
        entities: list[DetectionResult],
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        address_types = {"ADDRESS", "CITY_STATE_ZIP"}
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

            if current.entity_type in address_types:
                while index < len(ordered):
                    following = ordered[index]
                    if (
                        current.page_number != following.page_number
                        or following.entity_type not in address_types
                        or following.start_char < current.end_char
                    ):
                        break

                    gap = text[current.end_char:following.start_char]
                    if len(gap) <= 60 and ("\n" in gap or "," in gap or " " in gap):
                        current.end_char = following.end_char
                        current.entity_value = text[current.start_char:current.end_char].strip()
                        current.text = current.entity_value
                        current.entity_type = "ADDRESS"
                        current.canonical_type = "ADDRESS"
                        current.confidence_score = 1.0
                        index += 1
                    else:
                        break

                after_text = text[current.end_char:min(len(text), current.end_char + 120)]
                csz_match = re.match(
                    r"^[ \t]*(?:\r?\n)?[ \t]*(?:City,?[ \t]*State[ \t]*(?:and[ \t]*)?Zip|City/State/Zip|CSZ)?[ \t]*[:\-]?[ \t]*([A-Za-z\s.'-]+,[ \t]*[A-Z]{2}[ \t]+\d{5}(?:-\d{4})?)",
                    after_text,
                    re.IGNORECASE,
                )
                if csz_match:
                    match_end = current.end_char + csz_match.end()
                    current.end_char = match_end
                    current.entity_value = text[current.start_char:match_end].strip()
                    current.text = current.entity_value
                    current.entity_type = "ADDRESS"
                    current.canonical_type = "ADDRESS"
                    current.confidence_score = 1.0
                elif re.search(r",[ \t]*[A-Z]{2}$", current.entity_value.strip()):
                    trailing_zip = re.match(
                        r"^[ \t]+\d{5}(?:-\d{4})?\b",
                        after_text,
                    )
                    if trailing_zip:
                        match_end = current.end_char + trailing_zip.end()
                        current.end_char = match_end
                        current.entity_value = text[current.start_char:match_end].strip()
                        current.text = current.entity_value
                        current.entity_type = "ADDRESS"
                        current.canonical_type = "ADDRESS"
                        current.confidence_score = 1.0

            merged.append(current)

        return merged

    def _contextual_reclassify(self, text: str, entities: list[DetectionResult]) -> list[DetectionResult]:
        for entity in entities:
            start = max(0, entity.start_char - 80)
            end = min(len(text), entity.end_char + 80)
            context = text[start:end].lower()
            line_prefix = text[start:entity.start_char].split("\n")[-1].lower()

            # 1. Insurance, SSN & Claim ID reclassifications
            if entity.entity_type in {"INSURANCE_ID", "POLICY_NUMBER", "EOB_NUMBER", "CLAIM_NUMBER"}:
                if re.match(r"^(?:[Xx*]{3}[-\s]?[Xx*]{2}[-\s]?\d{4}|\d{3}[-\s]?[Xx*]{2}[-\s]?\d{4})$", entity.entity_value):
                    entity.entity_type = "SSN"
                    entity.canonical_type = "SSN"
                elif re.match(r"(?i)^(?:P\.?O\.?\s*)?Box\s+\d+$", entity.entity_value.strip()):
                    entity.entity_type = "ADDRESS"
                    entity.canonical_type = "ADDRESS"
                    entity.confidence_score = 0.95
                elif "member" in line_prefix or "member" in context:
                    entity.entity_type = "MEMBER_ID"
                elif "group" in line_prefix or "group" in context:
                    entity.entity_type = "GROUP_NUMBER"
                elif "eob" in line_prefix or "eob" in context:
                    entity.entity_type = "EOB_NUMBER"

            if entity.entity_type in {"ADDRESS", "LOCATION", "CITY_STATE_ZIP"}:
                if re.match(r"^[A-Za-z\s.'-]+,\s*[A-Z]{2}(?:\s+\d{5})?$", entity.entity_value.strip()):
                    entity.confidence_score = max(entity.confidence_score, 0.95)

            if entity.entity_type in {"PHONE_NUMBER", "US_PHONE_NUMBER", "ORGANIZATION_CONTACT_INFO"}:
                if any(kw in line_prefix for kw in ["patient", "home", "mobile", "cell", "personal"]):
                    entity.entity_type = "PHONE_NUMBER"
                elif any(kw in line_prefix for kw in ["customer service", "support", "help desk", "inquiries", "contact us", "response line", "hotline", "office phone", "claims phone", "claims", "appeals", "toll-free", "toll free"]):
                    entity.entity_type = "ORGANIZATION_CONTACT_INFO"
                elif "patient" in context:
                    entity.entity_type = "PHONE_NUMBER"
                elif any(kw in context for kw in ["customer service", "support", "help desk", "inquiries", "contact us", "claims", "appeals"]):
                    entity.entity_type = "ORGANIZATION_CONTACT_INFO"
                elif re.match(r"^\+?1?[-. \t]?\(?(?:800|888|877|866|855|844|833)\)?[-. \t]?\d{3}[-. \t]?\d{4}$", entity.entity_value) and not any(kw in line_prefix for kw in ["patient", "home"]):
                    entity.entity_type = "ORGANIZATION_CONTACT_INFO"

            # 3. Dates: Contextual reclassification
            if entity.entity_type in {"DATE", "DATE_TIME"}:
                if any(kw in line_prefix for kw in ["eob date", "statement date", "print date", "created on", "invoice date", "generated on", "issue date"]):
                    entity.entity_type = "DOCUMENT_CREATION_DATE"
                elif any(kw in line_prefix for kw in ["date of birth", "dob", "birth date", "born", "dependent", "child", "spouse", "beneficiary"]):
                    entity.entity_type = "DATE_OF_BIRTH"
                elif any(kw in line_prefix for kw in ["date(s) of service", "service date", "admission date", "discharge date", "visit date", "date of service", "dos"]):
                    entity.entity_type = "DATE_OF_SERVICE"
                elif any(kw in line_prefix for kw in ["coverage date", "effective date", "enrollment date", "termination date"]):
                    entity.entity_type = "COVERAGE_DATE"
                elif any(kw in line_prefix for kw in ["due date", "payment due"]):
                    entity.entity_type = "DUE_DATE"

            # 4. Disease / Medication misclassified as PERSON or ORGANIZATION
            if entity.entity_type in {"PERSON", "ORGANIZATION"}:
                val_lower = entity.entity_value.lower()
                CLINICAL_DISEASES = {"cancer", "diabetes", "hypertension", "asthma", "arthritis", "depression", "anxiety", "copd", "leukemia", "lymphoma"}
                if val_lower in CLINICAL_DISEASES:
                    entity.entity_type = "DISEASE"
                else:
                    MED_NAMES = {
                        "aspirin", "atorvastatin", "metformin", "lisinopril", "amoxicillin", "omeprazole", "gabapentin",
                        "levothyroxine", "ozempic", "metoprolol", "losartan", "hydrochlorothiazide", "simvastatin",
                        "sertraline", "prednisone", "doxycycline", "ciprofloxacin", "clopidogrel", "eliquis", "xarelto",
                        "januvia", "farxiga", "jardiance", "humira", "keytruda", "dupixent", "adderall", "vyvanse",
                        "warfarin", "tramadol", "albuterol", "montelukast", "brilinta", "lipitor", "zocor", "synthroid",
                        "crestor", "align", "dicyclomine", "probiotic", "insulin", "ibuprofen", "paracetamol", "acetaminophen",
                    }
                    if any(med in val_lower for med in MED_NAMES):
                        entity.entity_type = "MEDICATION"
                    elif re.search(r"\b\d+\s*(?:mg|mcg|ml|g|tablets?|capsules?)\b", context) and any(kw in context for kw in ["rx", "take", "daily", "dispense", "oral", "dose", "tablet", "capsule", "medication", "prescribed"]):
                        entity.entity_type = "MEDICATION"

            # 5. Patient name contextual reclassification
            if entity.entity_type == "PERSON":
                preceding_240 = text[max(0, entity.start_char - 240):entity.start_char]
                has_name_label = bool(
                    re.search(
                        r"(?:^|\n)[ \t]*[\*•\-]?[ \t]*Name[ \t]*[:\-][ \t]*$",
                        preceding_240,
                        re.IGNORECASE,
                    )
                )
                patient_section = preceding_240.lower().rfind("patient information")
                next_section = max(
                    preceding_240.lower().rfind("appointment details"),
                    preceding_240.lower().rfind("medical history"),
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
        llm_provider = os.getenv("LLM_PROVIDER", "").lower()
        active_llm_label = "gpt-5.4-mini" if llm_provider in {"azure", "azure_openai", "azureopenai"} else "Gemma4:e4b"

        llm_keys = {
            "azure", "azureopenai", "azure_openai", "azure_detector",
            "gemma", "gemma4e4b", "gemma4:e4b", "gemma_detector", "gemma4", "gemma-4",
            "qwen", "qwen3b", "qwen3:4b", "qwen_validation", "llm"
        }

        display_names = {
            "regex": "Regex",
            "presidio": "Presidio",
            "medspacy": "MedSpaCy",
            "gliner": "GLiNER",
        }
        for k in llm_keys:
            display_names[k] = active_llm_label
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
