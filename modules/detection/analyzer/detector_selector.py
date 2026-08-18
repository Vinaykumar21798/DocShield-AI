from dataclasses import dataclass
from typing import Any, Callable, Optional

from modules.detection.analyzer.detection_strategy import DetectionStrategy, ExecutionPlan
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.pipeline_state import PipelineState


DetectorGetter = Callable[[], BaseDetector]


@dataclass(frozen=True)
class DetectorSelection:
    detector: Optional[BaseDetector]
    reason: str
    remaining_candidates: dict[str, Any]


class DetectorSelector:
    """
    Selects detectors based on document content and current pipeline state.
    Acts as the dynamic detector router.
    """

    MEDICAL_KEYWORDS = {
        "patient",
        "hospital",
        "doctor",
        "diagnosis",
        "prescription",
        "medication",
        "allergy",
        "clinical",
        "physician",
        "treatment",
        "mrn",
        "discharge",
        "lab",
        "radiology",
        "blood",
        "x-ray",
        "scan",
    }

    HEALTHCARE_CUES = {
        "patient",
        "hospital",
        "doctor",
        "diagnosis",
        "medication",
        "treatment",
        "mrn",
        "clinical",
        "physician",
        "nurse",
        "medical center",
        "discharge summary",
        "prescription",
        "disease",
        "symptom",
        "procedure",
        "laboratory",
        "lab report",
    }
    STRONG_HEALTHCARE_CUES = HEALTHCARE_CUES - {
        "patient",
    }

    CORPORATE_CUES = {
        "employee",
        "designation",
        "manager",
        "joining date",
        "office address",
        "resume",
        "job title",
        "work at",
        "corporation",
        "company",
        "meeting date",
        "employment",
    }
    LEGAL_CUES = {
        "agreement",
        "contract",
        "party",
        "parties",
        "terms and conditions",
        "signature",
        "legal",
        "court",
        "clause",
        "effective date",
    }
    FINANCIAL_CUES = {
        "account holder",
        "account number",
        "bank statement",
        "statement period",
        "transaction",
        "invoice",
        "amount due",
        "balance",
        "ifsc",
        "credit card",
        "debit card",
        "iban",
        "tax id",
    }

    DOMAIN_ROUTES = {
        "financial": ("regex", "presidio", "gliner", "qwen3b"),
        "healthcare": ("regex", "medspacy", "presidio", "gliner", "qwen3b"),
        "corporate": ("regex", "presidio", "gliner", "qwen3b"),
        "legal": ("regex", "presidio", "gliner", "qwen3b"),
        "generic": ("regex", "presidio", "gliner", "qwen3b"),
        "mixed": ("regex", "medspacy", "presidio", "gliner", "qwen3b"),
    }

    DOCUMENT_TYPE_DOMAINS = {
        "bank_statement": "financial",
        "contract": "legal",
        "financial": "financial",
        "generic": "generic",
        "healthcare": "healthcare",
        "identity_document": "generic",
        "insurance": "financial",
        "invoice": "financial",
        "lab_report": "healthcare",
        "legal": "legal",
        "medical": "healthcare",
        "medical_record": "healthcare",
        "prescription": "healthcare",
        "receipt": "financial",
        "tax_form": "financial",
    }

    def select(
        self,
        text: str,
        document_type: str | None = None,
    ) -> DetectionStrategy:
        domain = self.classify_domain(text, document_type=document_type)
        strategy = DetectionStrategy(
            document_type="medical" if domain == "healthcare" else domain,
            language="en",
            use_presidio=True,
            use_gliner=True,
            use_medspacy=domain in {"healthcare", "mixed"},
            use_qwen=True,
        )
        strategy.selected_detectors = list(self.route_for_domain(domain))
        return strategy

    def classify_domain(
        self,
        text: str,
        document_type: str | None = None,
    ) -> str:
        text_lower = text.lower()
        document_domain = self.domain_for_document_type(document_type)

        has_healthcare = any(
            cue in text_lower
            for cue in self.HEALTHCARE_CUES
        )

        if document_domain == "healthcare":
            return "healthcare"

        if document_domain is not None:
            if self.has_strong_healthcare_cue(text_lower):
                return "healthcare"
            return document_domain

        has_corporate = any(
            cue in text_lower
            for cue in self.CORPORATE_CUES
        )
        has_legal = any(
            cue in text_lower
            for cue in self.LEGAL_CUES
        )
        has_financial = any(
            cue in text_lower
            for cue in self.FINANCIAL_CUES
        )

        if has_healthcare:
            return "healthcare"

        domain_hits = sum((
            has_financial,
            has_legal,
            has_corporate,
        ))

        if domain_hits > 1:
            return "mixed"

        if has_financial:
            return "financial"
        if has_legal:
            return "legal"
        if has_corporate:
            return "corporate"
        return "generic"

    def has_strong_healthcare_cue(self, text_lower: str) -> bool:
        return any(
            cue in text_lower
            for cue in self.STRONG_HEALTHCARE_CUES
        )

    def domain_for_document_type(self, document_type: str | None) -> str | None:
        if not document_type:
            return None

        normalized = document_type.strip().lower()
        normalized = normalized.replace("-", "_").replace(" ", "_")
        if normalized == "unknown":
            return None
        return self.DOCUMENT_TYPE_DOMAINS.get(normalized)

    def route_for_domain(self, domain: str) -> tuple[str, ...]:
        return self.DOMAIN_ROUTES.get(domain, self.DOMAIN_ROUTES["generic"])

    def select_next_detector(
        self,
        state: PipelineState,
        detector_getters: dict[str, DetectorGetter],
        route: tuple[str, ...],
        stopping_candidate_threshold: int = 0,
        min_candidate_chars: int = 3,
        continuation_confidence_threshold: float = 0.80,
        exhaust_route: bool = False,
    ) -> DetectorSelection:
        remaining = state.remaining_candidate_summary(
            min_chars=min_candidate_chars,
        )

        low_confidence_count = sum(
            1
            for entity in state.resolved_entities
            if entity.confidence_score < continuation_confidence_threshold
        ) + len(state.pending_candidates)
        has_low_confidence_unresolved = low_confidence_count > 0

        if (
            not exhaust_route
            and
            state.executed_detectors
            and remaining["count"] <= stopping_candidate_threshold
            and not has_low_confidence_unresolved
        ):
            return DetectorSelection(
                detector=None,
                reason=(
                    "Stopping: no unresolved entity candidates remain "
                    f"(count={remaining['count']})."
                ),
                remaining_candidates=remaining,
            )

        routing_text = state.original_text if exhaust_route else state.current_text
        if not routing_text.strip():
            return DetectorSelection(
                detector=None,
                reason="Stopping: masked text is empty.",
                remaining_candidates=remaining,
            )

        executed = {name.lower() for name in state.executed_detectors}
        skipped_reasons = []

        for detector_key in route:
            key = detector_key.lower()
            if key in executed:
                continue

            getter = detector_getters.get(key)
            if getter is None:
                skipped_reasons.append(f"{detector_key}: unavailable")
                continue

            detector = getter()
            self._attach_context(detector, state, remaining)
            try:
                should_run = detector.should_run(routing_text, state)
            except Exception as exc:
                should_run = True
                skipped_reasons.append(
                    f"{detector.name}: should_run failed ({exc}); selected for recall"
                )

            if should_run:
                if remaining["count"] > stopping_candidate_threshold:
                    route_reason = f"{remaining['count']} candidate span(s) remain"
                elif low_confidence_count:
                    route_reason = (
                        f"{low_confidence_count} low-confidence entity span(s) remain "
                        f"below {continuation_confidence_threshold:.0%}"
                    )
                else:
                    route_reason = "detector should_run returned True"

                reason = (
                    f"Selected {detector.name}: route position {detector_key} "
                    f"matched because {route_reason}."
                )
                return DetectorSelection(
                    detector=detector,
                    reason=reason,
                    remaining_candidates=remaining,
                )

            state.log_skipped(detector.name)
            skipped_reasons.append(
                f"{detector.name}: should_run returned False"
            )

        reason = "Stopping: detector route exhausted."
        if skipped_reasons:
            reason = f"{reason} Skips: {'; '.join(skipped_reasons)}"

        return DetectorSelection(
            detector=None,
            reason=reason,
            remaining_candidates=remaining,
        )

    def plan_execution(
        self,
        state: PipelineState,
        detectors: list[BaseDetector],
    ) -> ExecutionPlan:
        """
        Backward-compatible one-shot plan builder.

        The detection service now uses select_next_detector for dynamic routing,
        but this method remains available for existing callers.
        """
        detector_map = {
            detector.name.lower(): detector
            for detector in detectors
        }
        route = self.route_for_domain(self.classify_domain(state.original_text))
        selected_detectors = []
        metadata = {"domain": self.classify_domain(state.original_text)}
        remaining = state.remaining_candidate_summary()

        for detector_key in route:
            if detector_key == "regex":
                continue

            detector = detector_map.get(detector_key)
            if detector is None:
                metadata[detector_key] = "Unavailable"
                continue

            self._attach_context(detector, state, remaining)
            try:
                if detector.should_run(state.current_text, state):
                    selected_detectors.append(detector)
                    metadata[detector.name] = "should_run evaluated to True"
                else:
                    state.log_skipped(detector.name)
                    metadata[detector.name] = "should_run evaluated to False"
            except Exception as exc:
                selected_detectors.append(detector)
                metadata[detector.name] = (
                    f"Error during should_run check: {exc}"
                )

        return ExecutionPlan(
            selected_detectors=selected_detectors,
            metadata=metadata,
        )

    @staticmethod
    def _attach_context(
        detector: BaseDetector,
        state: PipelineState,
        remaining: dict[str, Any],
    ) -> None:
        setattr(
            detector,
            "orchestration_context",
            {
                "remaining_text": state.current_text,
                "previous_entities": list(state.resolved_entities),
                "remaining_candidates": remaining,
                "executed_detectors": list(state.executed_detectors),
                "skipped_detectors": list(state.skipped_detectors),
            },
        )
