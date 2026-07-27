from __future__ import annotations

import logging
import os
import time

from modules.detection.confidence import ConfidenceCalculator
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


class DetectionService:
    """
    Sequential Detection Pipeline

    Regex
        ↓
    Presidio
        ↓
    GLiNER
        ↓
    MedSpaCy
        ↓
    Confidence
        ↓
    Ollama (LOW confidence only)
    """

    def __init__(self):
        #
        # Lightweight detector
        #
        self.regex = RegexDetector()

        #
        # Heavy detectors
        #
        self._presidio = None
        self._gliner = None
        self._medspacy = None
        self._qwen3b = None

        #
        # Validator
        #
        self.validator = OllamaValidator()

        #
        # Detector Router
        #
        self.router = DetectorSelector()

    ###############################################################

    @property
    def presidio(self):
        if self._presidio is None:
            logger.info("Loading Presidio...")
            self._presidio = PresidioDetector()
        return self._presidio

    ###############################################################

    @property
    def gliner(self):
        if self._gliner is None:
            logger.info("Loading GLiNER...")
            self._gliner = GLiNERDetector()
        return self._gliner

    ###############################################################

    @property
    def medspacy(self):
        if self._medspacy is None:
            logger.info("Loading MedSpaCy...")
            self._medspacy = MedSpaCyDetector()
        return self._medspacy

    ###############################################################

    @property
    def qwen3b(self):
        if self._qwen3b is None:
            logger.info("Loading Qwen 3B...")
            self._qwen3b = Qwen3BDetector()
        return self._qwen3b


    ###############################################################

    def _run_detector(
        self,
        detector,
        state: PipelineState,
        page_number: int,
        custom_text: str | None = None,
    ):
        """
        Executes one detector and updates PipelineState.
        """
        run_text = custom_text if custom_text is not None else state.current_text
        if not run_text or not run_text.strip():
            return

        try:
            start_time = time.perf_counter()
            entities = detector.detect(
                run_text,
                page_number,
            )
            duration = time.perf_counter() - start_time
            state.log_time(detector.name, duration)

            if entities:
                state.add_entities(
                    entities,
                    detector.name,
                )
                logger.info(
                    "%s detected %d entities",
                    detector.name,
                    len(entities),
                )
            else:
                state.add_entities([], detector.name)

        except Exception as exc:
            logger.exception(
                "%s detector failed",
                detector.name,
            )
            raise DetectionError(
                f"{detector.name} failed"
            ) from exc


    ###############################################################

    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[DetectionResult]:
        """
        Main detection pipeline.
        """
        if not text:
            return []

        current_stage = "INITIALIZATION"
        try:
            state = PipelineState(
                original_text=text,
            )

            #######################################################
            # Stage 1: Regex Baseline
            #######################################################
            current_stage = "REGEX_BASELINE"
            start_stage = time.perf_counter()
            self._run_detector(
                self.regex,
                state,
                page_number,
            )
            stage_duration = time.perf_counter() - start_stage
            regex_entities = [e for e in state.resolved_entities if e.detector == "regex"]
            logger.info(
                "\n--- [Telemetry Report] ---"
                f"\nPipeline Stage: {current_stage}"
                f"\nDetector: regex"
                f"\nExecution Time: {stage_duration:.3f}s"
                f"\nDetected Entities: {len(regex_entities)}"
                f"\nAccepted: {len(regex_entities)}"
                f"\nRejected: 0"
                f"\nEscalated: 0"
                f"\nPersisted: 0 (Pending Stage 5)"
                "\n--------------------------"
            )

            #######################################################
            # Stage 2: Routing & Execution Plan
            #######################################################
            current_stage = "DETECTOR_ROUTING"
            detectors_list = [
                self.regex,
                self.presidio,
                self.gliner,
                self.medspacy,
            ]
            plan = self.router.plan_execution(state, detectors_list)

            current_stage = "PLANS_EXECUTION"
            # Execute the plan (only active detectors in plan)
            regex_masked_text = state.current_text
            for detector in plan.selected_detectors:
                start_det = time.perf_counter()
                self._run_detector(
                    detector,
                    state,
                    page_number,
                    custom_text=regex_masked_text,
                )
                det_duration = time.perf_counter() - start_det
                det_entities = [e for e in state.resolved_entities if e.detector == detector.name]
                logger.info(
                    "\n--- [Telemetry Report] ---"
                    f"\nPipeline Stage: {current_stage}"
                    f"\nDetector: {detector.name}"
                    f"\nExecution Time: {det_duration:.3f}s"
                    f"\nDetected Entities: {len(det_entities)}"
                    f"\nAccepted: {len(det_entities)}"
                    f"\nRejected: 0"
                    f"\nEscalated: 0"
                    f"\nPersisted: 0 (Pending Stage 5)"
                    "\n--------------------------"
                )

            #######################################################
            # Stage 3: Confidence & Escalation Heuristics
            #######################################################
            current_stage = "CONFIDENCE_CALIBRATION"
            entities = ConfidenceCalculator.calculate(
                state.resolved_entities
            )

            current_stage = "SEMANTIC_REASONING_DECISION"
            # Determine if Qwen 3B SLM semantic reasoning is needed
            if self.qwen3b.should_run(state.current_text, state):
                current_stage = "SEMANTIC_REASONING_EXECUTION"
                start_qwen = time.perf_counter()
                logger.info("Semantic reasoning required. Executing Qwen 3B SLM...")
                self._run_detector(
                    self.qwen3b,
                    state,
                    page_number,
                )
                qwen_duration = time.perf_counter() - start_qwen
                qwen_entities = [e for e in state.resolved_entities if e.detector == "qwen3b"]
                logger.info(
                    "\n--- [Telemetry Report] ---"
                    f"\nPipeline Stage: {current_stage}"
                    f"\nDetector: qwen3b"
                    f"\nExecution Time: {qwen_duration:.3f}s"
                    f"\nDetected Entities: {len(qwen_entities)}"
                    f"\nAccepted: {len(qwen_entities)}"
                    f"\nRejected: 0"
                    f"\nEscalated: 0"
                    f"\nPersisted: 0 (Pending Stage 5)"
                    "\n--------------------------"
                )
                # Recalibrate confidence levels after Qwen 3B extracts/updates entities
                entities = ConfidenceCalculator.calculate(
                    state.resolved_entities
                )

            #######################################################
            # Stage 4: High-Reasoning LLM Validation (Qwen 8B)
            #######################################################
            current_stage = "LLM_VALIDATION"
            high_entities = []
            low_entities = []

            for entity in entities:
                level = entity.metadata.get(
                    "confidence_level",
                    "HIGH",
                )
                if level == "LOW":
                    low_entities.append(entity)
                else:
                    high_entities.append(entity)

            escalated_count = len(low_entities)
            accepted_count = len(high_entities)
            rejected_count = 0

            if low_entities and os.getenv("BYPASS_LLM") != "true":
                logger.info(
                    "Validating %d low confidence entities via Qwen 8B LLM...",
                    len(low_entities),
                )
                start_val = time.perf_counter()
                low_entities = self.validator.validate_batch(
                    context=text,
                    entities=low_entities,
                )
                val_duration = time.perf_counter() - start_val
                
                # Count accepted vs rejected
                for e in low_entities:
                    if e.metadata.get("valid", True):
                        accepted_count += 1
                    else:
                        rejected_count += 1
                
                logger.info(
                    "\n--- [Telemetry Report] ---"
                    f"\nPipeline Stage: {current_stage}"
                    f"\nDetector: qwen8b_validator"
                    f"\nExecution Time: {val_duration:.3f}s"
                    f"\nDetected Entities: {len(low_entities)}"
                    f"\nAccepted: {accepted_count}"
                    f"\nRejected: {rejected_count}"
                    f"\nEscalated: {escalated_count}"
                    f"\nPersisted: 0 (Pending Stage 5)"
                    "\n--------------------------"
                )
            elif low_entities:
                logger.info("BYPASS_LLM is set to true. Skipping Qwen 8B validation for %d low confidence entities.", len(low_entities))

            #######################################################
            # Finalization & Telemetry Logging
            #######################################################
            current_stage = "FINALIZATION"
            results = high_entities + low_entities

            # Remove invalid entities
            results = [
                entity
                for entity in results
                if entity.metadata.get(
                    "valid",
                    True,
                )
            ]

            # Normalize entity types and assign privacy categories (PII/PHI)
            results = EntityMapper.normalize(results)

            # 1. Apply deduplication (removes duplicates of the same type and value)
            results = Deduplicator.deduplicate(results)

            # 2. Resolve overlapping character boundaries by prioritizing authoritative detector ownership
            AUTHORITATIVE_OWNERS = {
                # Regex
                "email": "regex", "phone_number": "regex", "us_phone_number": "regex",
                "pan_number": "regex", "passport_number": "regex", "aadhaar_number": "regex",
                "ssn": "regex", "mrn": "regex", "insurance_id": "regex", "claim_number": "regex",
                "ifsc_code": "regex", "upi_id": "regex", "url": "regex", "ip_address": "regex",
                "zip_code": "regex", "pin_code": "regex", "date_of_birth": "regex",
                "credit_card": "regex", "cpt_code": "regex", "icd10_code": "regex",
                
                # Presidio
                "person": "presidio", "location": "presidio", "date_time": "presidio",
                "organization": "presidio", "address": "presidio",
                
                # GLiNER
                "doctor": "gliner", "patient": "gliner", "hospital": "gliner",
                "nurse": "gliner", "physician": "gliner", "healthcare staff": "gliner",
                "healthcare_staff": "gliner", "medical facility": "gliner",
                "medical_facility": "gliner", "healthcare organization": "gliner",
                "healthcare_organization": "gliner",
                
                # MedSpaCy
                "problem": "medspacy", "medication": "medspacy", "procedure": "medspacy",
                "lab": "medspacy", "symptom": "medspacy", "diagnosis": "medspacy",
                "allergy": "medspacy", "vital_sign": "medspacy", "disease": "medspacy",
                "clinical_findings": "medspacy", "clinical finding": "medspacy",
                "clinical_finding": "medspacy"
            }

            DETECTOR_PRIORITY = {
                "regex": 4,
                "presidio": 3,
                "gliner": 2,
                "medspacy": 1,
                "qwen3b": 0,
                "qwen8b": 0
            }

            SPECIALIZED_TYPES = {
                # Regex
                "email", "phone_number", "us_phone_number", "pan_number", "passport_number", "aadhaar_number",
                "ssn", "mrn", "insurance_id", "claim_number", "ifsc_code", "upi_id", "url", "ip_address",
                "zip_code", "pin_code", "date_of_birth", "credit_card", "cpt_code", "icd10_code",
                
                # Clinical / Healthcare
                "doctor", "patient", "nurse", "physician", "healthcare_staff", "healthcare staff",
                "medical_facility", "medical facility", "healthcare_organization", "healthcare organization",
                "hospital", "disease", "problem", "medication", "procedure", "lab", "symptom", "diagnosis",
                "allergy", "vital_sign", "clinical_finding", "clinical finding"
            }

            def get_sorting_key(entity: DetectionResult):
                ent_type_lower = entity.entity_type.lower()
                det_name_lower = entity.detector.lower()
                
                # Match authoritative owner?
                owner = AUTHORITATIVE_OWNERS.get(ent_type_lower)
                is_authoritative = 1 if (owner == det_name_lower) else 0
                
                # Is it a specialized clinical/healthcare type (vs generic person/org)?
                type_rank = 1 if ent_type_lower in SPECIALIZED_TYPES else 0
                
                # Traditional detector priority: Regex (4) > Presidio (3) > GLiNER (2) > MedSpaCy (1) > Qwen (0)
                det_priority = DETECTOR_PRIORITY.get(det_name_lower, 0)
                
                # Criteria: (is_authoritative, type_rank, det_priority, confidence_score, span_length)
                return (
                    is_authoritative,
                    type_rank,
                    det_priority,
                    entity.confidence_score,
                    entity.end_char - entity.start_char
                )

            # Sort descending (reverse=True) so authoritative matches go first
            results.sort(key=get_sorting_key, reverse=True)

            non_overlapping = []
            for entity in results:
                overlap = False
                for accepted in non_overlapping:
                    if entity.page_number == accepted.page_number:
                        # Standard range overlap check
                        if entity.start_char < accepted.end_char and entity.end_char > accepted.start_char:
                            overlap = True
                            break
                if not overlap:
                    non_overlapping.append(entity)

            results = non_overlapping

            # Update the pipeline state's final entities and telemetry
            state.resolved_entities = results
            state.finalize_confidence_summary()

            # Sort by document position for return predictability
            results.sort(
                key=lambda entity: (
                    entity.page_number,
                    entity.start_char,
                )
            )


            logger.info(
                "Detection complete. %d entities. Skipped detectors: %s. Telemetry: %s",
                len(results),
                state.skipped_detectors,
                state.execution_time,
            )

            return results

        except Exception as exc:
            logger.exception("Detection pipeline failed at stage: %s", current_stage)
            raise DetectionError(
                f"Detection failed at Stage {current_stage}: {exc}"
            ) from exc