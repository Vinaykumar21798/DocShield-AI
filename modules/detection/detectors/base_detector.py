from abc import ABC, abstractmethod

from modules.detection.models.detection_result import DetectionResult


class BaseDetector(ABC):
    """
    Abstract base class for all detection engines.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the detector name.
        """
        pass

    @abstractmethod
    def detect(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[DetectionResult]:
        """
        Detect entities from text.

        Args:
            text: Extracted text from OCR/Native PDF.
            page_number: Page number of the document.

        Returns:
            List of DetectionResult objects.
        """
        pass

    def should_run(self, text: str, state: "PipelineState") -> bool:
        """
        Evaluates heuristic checks to decide if this detector should run.
        Can be overridden by subclasses.
        """
        return True

    def clean_text_of_labels(self, text: str) -> str:
        """
        Strips common PII/PHI field labels, headers, digits, and punctuation.
        Returns empty string if only labels/punctuation/whitespaces remain.
        """
        import re
        text_lower = text.lower()
        labels_to_remove = [
            "email", "phone", "mobile", "contact", "pan", "aadhaar", "passport", "ssn", "mrn",
            "insurance id", "insurance", "policy", "claim number", "claim", "ifsc code", "ifsc",
            "upi id", "upi", "pin code", "pin", "zip code", "zip", "url", "ip address", "ip",
            "passport number", "aadhaar number", "pan number", "phone number", "date of birth", "dob",
            "customer name", "account holder", "account number", "patient name", "patient", "doctor",
            "consultant", "hospital", "address", "diagnosis", "medication", "medicines", "cpt", "icd",
            "history", "symptom", "procedure", "vital signs", "lab", "laboratory", "results",
            "date", "time", "location", "organization", "person", "gender", "age", "sex"
        ]
        
        # Replace labels with spaces (matching whole words only)
        cleaned = text_lower
        for label in labels_to_remove:
            cleaned = re.sub(rf'\b{re.escape(label)}\b', ' ', cleaned)
            
        # Remove non-alphabetic tokens and numbers
        cleaned = re.sub(r'[\W\d_]+', ' ', cleaned)
        
        # Filter out words shorter than 3 characters (e.g. leftover punctuation, short label words, single letters)
        words = [w for w in cleaned.split() if len(w) >= 3]
        if not words:
            return ""
        return " ".join(words)
