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
        "financial": ("regex", "gliner"),
        "healthcare": ("regex", "medspacy", "gliner"),
        "corporate": ("regex", "gliner", "presidio"),
        "legal": ("regex", "gliner", "presidio"),
        "generic": ("regex", "presidio", "gliner", "medspacy"),
        "mixed": ("regex", "presidio", "gliner", "medspacy"),
    }

    def select(self, text: str) -> DetectionStrategy:
        domain = self.classify_domain(text)
        strategy = DetectionStrategy(
            document_type="medical" if domain == "healthcare" else domain,
            language="en",
            use_presidio=domain in {"corporate", "legal", "generic", "mixed"},
            use_gliner=True,
            use_medspacy=domain in {"healthcare", "generic", "mixed"},
            use_ollama=True,
        )
        strategy.selected_detectors = list(self.route_for_domain(domain))
        return strategy

    def classify_domain(self, text: str) -> str:
        text_lower = text.lower()

        has_healthcare = any(
            cue in text_lower
            for cue in self.HEALTHCARE_CUES
        )
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

        domain_hits = sum((
            has_healthcare,
            has_financial,
            has_legal,
            has_corporate,
        ))

        if domain_hits > 1:
            return "mixed"

        if has_healthcare:
            return "healthcare"
        if has_financial:
            return "financial"
        if has_legal:
            return "legal"
        if has_corporate:
            return "corporate"
        return "generic"

    def route_for_domain(self, domain: str) -> tuple[str, ...]:
        return self.DOMAIN_ROUTES.get(domain, self.DOMAIN_ROUTES["generic"])

    def select_next_detector(
        self,
        state: PipelineState,
        detector_getters: dict[str, DetectorGetter],
        route: tuple[str, ...],
        stopping_candidate_threshold: int = 0,
        min_candidate_chars: int = 3,
    ) -> DetectorSelection:
        remaining = state.remaining_candidate_summary(
            min_chars=min_candidate_chars,
        )

        if (
            state.executed_detectors
            and remaining["count"] <= stopping_candidate_threshold
        ):
            return DetectorSelection(
                detector=None,
                reason=(
                    "Stopping: no unresolved entity candidates remain "
                    f"(count={remaining['count']})."
                ),
                remaining_candidates=remaining,
            )

        if not state.current_text.strip():
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
                should_run = detector.should_run(state.current_text, state)
            except Exception as exc:
                should_run = True
                skipped_reasons.append(
                    f"{detector.name}: should_run failed ({exc}); selected for recall"
                )

            if should_run:
                reason = (
                    f"Selected {detector.name}: route position {detector_key} "
                    f"matched and {remaining['count']} candidate span(s) remain."
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