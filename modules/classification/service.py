import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

from database.models import Document


class DocumentType(str, Enum):
    """
    Supported enterprise document categories for deterministic classification.
    """

    INVOICE = "INVOICE"
    RECEIPT = "RECEIPT"
    MEDICAL_RECORD = "MEDICAL_RECORD"
    LAB_REPORT = "LAB_REPORT"
    PRESCRIPTION = "PRESCRIPTION"
    INSURANCE = "INSURANCE"
    BANK_STATEMENT = "BANK_STATEMENT"
    TAX_FORM = "TAX_FORM"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    CONTRACT = "CONTRACT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ClassificationSignal:
    """
    Weighted keyword or phrase used by the rules-based classifier.
    """

    text: str
    weight: float


@dataclass(frozen=True)
class ClassificationResult:
    """
    Classification output returned to the workflow layer.
    """

    document_type: str
    confidence_score: float
    matched_signals: Tuple[str, ...]


MIN_CLASSIFICATION_SCORE = 2.0
MAX_CONFIDENCE_SCORE = 10.0
MAX_TEXT_CHARS = 25000


CLASSIFICATION_RULES: Dict[
    DocumentType,
    Tuple[ClassificationSignal, ...],
] = {
    DocumentType.INVOICE: (
        ClassificationSignal("invoice", 4.0),
        ClassificationSignal("invoice #", 3.0),
        ClassificationSignal("invoice number", 3.0),
        ClassificationSignal("bill to", 2.0),
        ClassificationSignal("ship to", 2.0),
        ClassificationSignal("amount due", 2.0),
        ClassificationSignal("payment terms", 1.5),
        ClassificationSignal("subtotal", 1.0),
        ClassificationSignal("due date", 1.0),
    ),
    DocumentType.RECEIPT: (
        ClassificationSignal("receipt", 4.0),
        ClassificationSignal("transaction", 2.0),
        ClassificationSignal("cashier", 2.0),
        ClassificationSignal("change due", 2.0),
        ClassificationSignal("store #", 1.5),
        ClassificationSignal("payment method", 1.0),
    ),
    DocumentType.MEDICAL_RECORD: (
        ClassificationSignal("medical record", 4.0),
        ClassificationSignal("patient", 2.5),
        ClassificationSignal("diagnosis", 2.5),
        ClassificationSignal("physician", 2.0),
        ClassificationSignal("hospital", 2.0),
        ClassificationSignal("clinic", 1.5),
        ClassificationSignal("mrn", 1.5),
    ),
    DocumentType.LAB_REPORT: (
        ClassificationSignal("lab report", 4.0),
        ClassificationSignal("laboratory", 3.0),
        ClassificationSignal("specimen", 2.5),
        ClassificationSignal("reference range", 2.5),
        ClassificationSignal("test result", 2.0),
        ClassificationSignal("collected", 1.0),
    ),
    DocumentType.PRESCRIPTION: (
        ClassificationSignal("prescription", 4.0),
        ClassificationSignal("rx", 3.0),
        ClassificationSignal("dosage", 2.0),
        ClassificationSignal("refill", 2.0),
        ClassificationSignal("pharmacy", 2.0),
        ClassificationSignal("take one", 1.5),
    ),
    DocumentType.INSURANCE: (
        ClassificationSignal("insurance", 4.0),
        ClassificationSignal("policy number", 3.0),
        ClassificationSignal("claim number", 3.0),
        ClassificationSignal("insured", 2.0),
        ClassificationSignal("premium", 2.0),
        ClassificationSignal("coverage", 2.0),
    ),
    DocumentType.BANK_STATEMENT: (
        ClassificationSignal("bank statement", 4.0),
        ClassificationSignal("statement period", 3.0),
        ClassificationSignal("account summary", 2.5),
        ClassificationSignal("opening balance", 2.0),
        ClassificationSignal("closing balance", 2.0),
        ClassificationSignal("deposits", 1.5),
        ClassificationSignal("withdrawals", 1.5),
    ),
    DocumentType.TAX_FORM: (
        ClassificationSignal("tax form", 4.0),
        ClassificationSignal("form w 2", 4.0),
        ClassificationSignal("form 1099", 4.0),
        ClassificationSignal("tax year", 3.0),
        ClassificationSignal("taxpayer", 2.0),
        ClassificationSignal("withholding", 2.0),
    ),
    DocumentType.IDENTITY_DOCUMENT: (
        ClassificationSignal("passport", 4.0),
        ClassificationSignal("driver license", 4.0),
        ClassificationSignal("identity card", 3.0),
        ClassificationSignal("date of birth", 2.0),
        ClassificationSignal("national id", 2.0),
        ClassificationSignal("aadhaar", 2.0),
    ),
    DocumentType.CONTRACT: (
        ClassificationSignal("agreement", 3.0),
        ClassificationSignal("contract", 3.0),
        ClassificationSignal("effective date", 2.0),
        ClassificationSignal("party", 1.5),
        ClassificationSignal("terms and conditions", 1.5),
        ClassificationSignal("signature", 1.0),
    ),
}


class DocumentClassificationService:
    """
    Deterministic document classifier.

    The service intentionally avoids ML/LLM dependencies. It uses weighted
    domain signals so the orchestration layer can perform real classification
    now, while keeping the implementation replaceable later.
    """

    def __init__(
        self,
        rules: Optional[
            Mapping[DocumentType, Sequence[ClassificationSignal]]
        ] = None,
        minimum_score: float = MIN_CLASSIFICATION_SCORE,
        max_confidence_score: float = MAX_CONFIDENCE_SCORE,
    ):
        self.rules = rules or CLASSIFICATION_RULES
        self.minimum_score = minimum_score
        self.max_confidence_score = max_confidence_score

    def classify(
        self,
        document: Document,
        extracted_text: Optional[str] = None,
    ) -> ClassificationResult:
        normalized_text = self._build_classification_text(
            document,
            extracted_text,
        )

        best_type = DocumentType.UNKNOWN
        best_score = 0.0
        best_matches: Tuple[str, ...] = tuple()

        for document_type, signals in self.rules.items():
            score, matches = self._score_document_type(
                normalized_text,
                signals,
            )
            if score > best_score:
                best_type = document_type
                best_score = score
                best_matches = matches

        if best_score < self.minimum_score:
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN.value,
                confidence_score=0.0,
                matched_signals=tuple(),
            )

        return ClassificationResult(
            document_type=best_type.value,
            confidence_score=self._to_confidence(best_score),
            matched_signals=best_matches,
        )

    def _build_classification_text(
        self,
        document: Document,
        extracted_text: Optional[str],
    ) -> str:
        values = [
            document.filename,
            document.stored_filename,
            document.file_type,
            self._file_suffix(document.filename),
            extracted_text or "",
        ]
        raw_text = " ".join(value for value in values if value)
        return self._normalize(raw_text[:MAX_TEXT_CHARS])

    @staticmethod
    def _score_document_type(
        text: str,
        signals: Sequence[ClassificationSignal],
    ) -> Tuple[float, Tuple[str, ...]]:
        score = 0.0
        matches = []

        for signal in signals:
            if DocumentClassificationService._contains_signal(
                text,
                signal.text,
            ):
                score += signal.weight
                matches.append(signal.text)

        return score, tuple(matches)

    @staticmethod
    def _contains_signal(text: str, signal: str) -> bool:
        normalized_signal = DocumentClassificationService._normalize(signal)
        if " " in normalized_signal:
            return normalized_signal in text

        return re.search(
            rf"\b{re.escape(normalized_signal)}\b",
            text,
        ) is not None

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = value.lower()
        normalized = re.sub(r"[_\-:/\\]+", " ", normalized)
        normalized = re.sub(r"[^a-z0-9# ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _file_suffix(filename: Optional[str]) -> str:
        if not filename:
            return ""
        return Path(filename).suffix.lstrip(".")

    def _to_confidence(self, score: float) -> float:
        confidence = score / self.max_confidence_score
        return round(min(confidence, 1.0), 4)


document_classification_service = DocumentClassificationService()

