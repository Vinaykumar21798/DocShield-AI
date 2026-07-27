from modules.detection.analyzer.detection_strategy import DetectionStrategy, ExecutionPlan
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.pipeline_state import PipelineState


class DetectorSelector:
    """
    Selects detectors based on document content and plan.
    Acts as the Detector Router.
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

    def select(self, text: str) -> DetectionStrategy:
        text_lower = text.lower()

        is_medical = any(
            keyword in text_lower
            for keyword in self.MEDICAL_KEYWORDS
        )

        strategy = DetectionStrategy(
            document_type="medical" if is_medical else "generic",
            language="en",
            use_presidio=True,
            use_gliner=True,
            use_medspacy=is_medical,
            use_ollama=True,
        )

        strategy.selected_detectors = [
            "presidio",
            "gliner",
        ]

        if strategy.use_medspacy:
            strategy.selected_detectors.append("medspacy")

        return strategy

    def plan_execution(
        self,
        state: PipelineState,
        detectors: list[BaseDetector],
    ) -> ExecutionPlan:
        """
        Compiles an ExecutionPlan by querying self-contained detector heuristics
        and evaluating document domain context.
        """
        selected_detectors = []
        metadata = {}

        # Classify document domain based on original text
        text_lower = state.original_text.lower()
        
        healthcare_cues = {
            "patient", "hospital", "doctor", "diagnosis", "medication", "treatment", 
            "mrn", "clinical", "physician", "nurse", "medical center", "discharge summary",
            "prescription", "disease", "symptom", "procedure"
        }
        corporate_cues = {
            "employee", "designation", "manager", "joining date", "office address", 
            "resume", "job title", "work at", "corporation", "company", "meeting date"
        }
        financial_cues = {
            "account holder", "account number", "bank statement", "transaction", 
            "invoice", "balance", "ifsc", "credit card", "debit card"
        }

        # Check for presence of domain keywords
        has_healthcare = any(cue in text_lower for cue in healthcare_cues)
        has_corporate = any(cue in text_lower for cue in corporate_cues)
        has_financial = any(cue in text_lower for cue in financial_cues)

        # Resolve domain gating (Healthcare takes precedence, then Corporate, then Financial)
        is_healthcare = has_healthcare
        is_corporate = has_corporate and not has_healthcare
        is_financial = has_financial and not (has_healthcare or has_corporate)

        metadata["domain"] = "healthcare" if is_healthcare else (
            "corporate" if is_corporate else ("financial" if is_financial else "generic")
        )

        # Loop through all configured detectors (excluding Regex, which runs first)
        for detector in detectors:
            name_lower = detector.name.lower()
            if name_lower == "regex":
                continue

            # Domain gating rules
            if is_financial:
                # Bank statement -> Skip all downstream models (Presidio, GLiNER, MedSpaCy)
                state.log_skipped(detector.name)
                metadata[detector.name] = "Skipped (Financial Domain Gating)"
                continue

            if is_corporate and name_lower in {"gliner", "medspacy"}:
                # Corporate document -> Skip GLiNER and MedSpaCy
                state.log_skipped(detector.name)
                metadata[detector.name] = "Skipped (Corporate Domain Gating)"
                continue

            try:
                # Query the detector's internal routing heuristics
                if detector.should_run(state.current_text, state):
                    selected_detectors.append(detector)
                    metadata[detector.name] = "should_run evaluated to True"
                else:
                    state.log_skipped(detector.name)
                    metadata[detector.name] = "should_run evaluated to False"
            except Exception as e:
                # Fallback to including the detector if checking fails to ensure high recall
                selected_detectors.append(detector)
                metadata[detector.name] = f"Error during should_run check: {e}"

        return ExecutionPlan(
            selected_detectors=selected_detectors,
            metadata=metadata,
        )