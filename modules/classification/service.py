import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Pattern, Sequence, Set, Tuple

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


RE_CLEAN_PUNCT: Pattern = re.compile(r"[_\-:/\\]+")
RE_CLEAN_NON_ALPHANUM: Pattern = re.compile(r"[^a-z0-9# ]+")
RE_CLEAN_WHITESPACE: Pattern = re.compile(r"\s+")


def _normalize_signal_string(value: str) -> str:
    normalized = value.lower()
    normalized = RE_CLEAN_PUNCT.sub(" ", normalized)
    normalized = RE_CLEAN_NON_ALPHANUM.sub(" ", normalized)
    normalized = RE_CLEAN_WHITESPACE.sub(" ", normalized)
    return normalized.strip()


@dataclass(frozen=True)
class ClassificationSignal:
    """
    Weighted keyword or phrase used by the rules-based classifier.
    """

    text: str
    weight: float
    normalized_text: str = ""
    has_space: bool = False

    def __post_init__(self):
        if not self.normalized_text:
            norm = _normalize_signal_string(self.text)
            object.__setattr__(self, "normalized_text", norm)
            object.__setattr__(self, "has_space", " " in norm)


@dataclass(frozen=True)
class EvidenceGroup:
    """
    Semantic grouping of related document signals.
    """

    name: str
    weight: float
    signals: Tuple[ClassificationSignal, ...]
    min_matches: int = 1


@dataclass(frozen=True)
class ClassificationResult:
    """
    Classification output returned to the workflow layer with rich diagnostic evidence.
    """

    document_type: str
    confidence_score: float
    matched_signals: Tuple[str, ...]
    matched_groups: Tuple[str, ...] = tuple()
    reason: str = ""


MIN_CLASSIFICATION_SCORE = 2.5
MAX_CONFIDENCE_SCORE = 10.0
MAX_TEXT_CHARS = 25000


EVIDENCE_GROUP_RULES: Dict[
    DocumentType,
    Tuple[EvidenceGroup, ...],
] = {
    DocumentType.BANK_STATEMENT: (
        EvidenceGroup(
            name="banking_identity",
            weight=3.5,
            signals=(
                ClassificationSignal("account number", 3.0),
                ClassificationSignal("account no", 3.0),
                ClassificationSignal("a c no", 3.0),
                ClassificationSignal("acct no", 3.0),
                ClassificationSignal("account holder", 2.5),
                ClassificationSignal("ifsc", 3.0),
                ClassificationSignal("ifsc code", 3.0),
                ClassificationSignal("branch", 1.5),
                ClassificationSignal("micr", 2.0),
                ClassificationSignal("customer id", 1.5),
                ClassificationSignal("cif", 1.5),
                ClassificationSignal("bank name", 2.0),
            ),
        ),
        EvidenceGroup(
            name="banking_structure",
            weight=4.0,
            signals=(
                ClassificationSignal("bank statement", 4.0),
                ClassificationSignal("statement of account", 4.0),
                ClassificationSignal("account statement", 4.0),
                ClassificationSignal("passbook", 3.5),
                ClassificationSignal("statement period", 3.0),
                ClassificationSignal("account summary", 2.5),
                ClassificationSignal("e statement", 3.0),
                ClassificationSignal("transaction date", 2.0),
                ClassificationSignal("value date", 2.0),
                ClassificationSignal("txn date", 2.0),
            ),
        ),
        EvidenceGroup(
            name="banking_balance",
            weight=3.0,
            signals=(
                ClassificationSignal("opening balance", 2.5),
                ClassificationSignal("closing balance", 2.5),
                ClassificationSignal("available balance", 2.5),
                ClassificationSignal("current balance", 2.0),
                ClassificationSignal("ledger balance", 2.0),
                ClassificationSignal("clear balance", 2.0),
            ),
        ),
        EvidenceGroup(
            name="banking_transaction",
            weight=2.5,
            signals=(
                ClassificationSignal("debit", 1.5),
                ClassificationSignal("credit", 1.5),
                ClassificationSignal("deposits", 1.5),
                ClassificationSignal("withdrawals", 1.5),
                ClassificationSignal("withdrawal", 1.5),
                ClassificationSignal("upi", 1.5),
                ClassificationSignal("neft", 1.5),
                ClassificationSignal("rtgs", 1.5),
                ClassificationSignal("imps", 1.5),
                ClassificationSignal("cheque", 1.0),
                ClassificationSignal("chq", 1.0),
            ),
        ),
    ),
    DocumentType.INVOICE: (
        EvidenceGroup(
            name="invoice_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("invoice", 4.0),
                ClassificationSignal("invoice #", 3.5),
                ClassificationSignal("invoice number", 3.5),
                ClassificationSignal("tax invoice", 4.0),
                ClassificationSignal("commercial invoice", 4.0),
                ClassificationSignal("bill #", 2.5),
                ClassificationSignal("bill no", 2.5),
            ),
        ),
        EvidenceGroup(
            name="billing_parties",
            weight=3.0,
            signals=(
                ClassificationSignal("bill to", 2.5),
                ClassificationSignal("ship to", 2.5),
                ClassificationSignal("billed to", 2.5),
                ClassificationSignal("sold to", 2.0),
                ClassificationSignal("vendor", 1.5),
                ClassificationSignal("supplier", 1.5),
                ClassificationSignal("customer", 1.0),
            ),
        ),
        EvidenceGroup(
            name="financial_terms",
            weight=3.0,
            signals=(
                ClassificationSignal("amount due", 2.5),
                ClassificationSignal("payment terms", 2.0),
                ClassificationSignal("subtotal", 1.5),
                ClassificationSignal("due date", 1.5),
                ClassificationSignal("balance due", 2.0),
                ClassificationSignal("tax amount", 1.5),
                ClassificationSignal("gstin", 2.0),
                ClassificationSignal("vat #", 1.5),
            ),
        ),
        EvidenceGroup(
            name="line_items",
            weight=2.0,
            signals=(
                ClassificationSignal("description", 1.0),
                ClassificationSignal("qty", 1.0),
                ClassificationSignal("quantity", 1.0),
                ClassificationSignal("unit price", 1.5),
                ClassificationSignal("rate", 1.0),
                ClassificationSignal("line total", 1.5),
            ),
        ),
    ),
    DocumentType.RECEIPT: (
        EvidenceGroup(
            name="receipt_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("receipt", 4.0),
                ClassificationSignal("sales receipt", 4.0),
                ClassificationSignal("cash receipt", 4.0),
                ClassificationSignal("payment receipt", 4.0),
                ClassificationSignal("tax receipt", 3.5),
            ),
        ),
        EvidenceGroup(
            name="transaction_meta",
            weight=3.0,
            signals=(
                ClassificationSignal("transaction", 2.0),
                ClassificationSignal("cashier", 2.5),
                ClassificationSignal("store #", 2.0),
                ClassificationSignal("terminal #", 2.0),
                ClassificationSignal("register #", 2.0),
                ClassificationSignal("pos", 1.5),
            ),
        ),
        EvidenceGroup(
            name="payment_settlement",
            weight=3.0,
            signals=(
                ClassificationSignal("change due", 2.5),
                ClassificationSignal("cash tendered", 2.5),
                ClassificationSignal("payment method", 2.0),
                ClassificationSignal("paid by", 2.0),
                ClassificationSignal("visa", 1.0),
                ClassificationSignal("mastercard", 1.0),
            ),
        ),
    ),
    DocumentType.MEDICAL_RECORD: (
        EvidenceGroup(
            name="clinical_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("medical record", 4.0),
                ClassificationSignal("clinical record", 4.0),
                ClassificationSignal("progress note", 3.5),
                ClassificationSignal("history and physical", 4.0),
                ClassificationSignal("discharge summary", 4.0),
                ClassificationSignal("consultation note", 3.5),
                ClassificationSignal("chart note", 3.5),
            ),
        ),
        EvidenceGroup(
            name="patient_identity",
            weight=3.0,
            signals=(
                ClassificationSignal("patient", 2.5),
                ClassificationSignal("patient name", 3.0),
                ClassificationSignal("mrn", 3.0),
                ClassificationSignal("medical record number", 3.5),
                ClassificationSignal("date of birth", 2.0),
                ClassificationSignal("dob", 2.0),
                ClassificationSignal("encounter #", 2.0),
            ),
        ),
        EvidenceGroup(
            name="clinical_findings",
            weight=3.5,
            signals=(
                ClassificationSignal("diagnosis", 3.0),
                ClassificationSignal("clinical impression", 3.0),
                ClassificationSignal("assessment", 2.5),
                ClassificationSignal("symptoms", 2.0),
                ClassificationSignal("chief complaint", 3.0),
                ClassificationSignal("history of present illness", 3.0),
                ClassificationSignal("vital signs", 2.0),
                ClassificationSignal("allergies", 2.0),
            ),
        ),
        EvidenceGroup(
            name="provider_facility",
            weight=2.5,
            signals=(
                ClassificationSignal("physician", 2.5),
                ClassificationSignal("attending physician", 3.0),
                ClassificationSignal("doctor", 2.0),
                ClassificationSignal("dr", 1.5),
                ClassificationSignal("hospital", 2.0),
                ClassificationSignal("clinic", 2.0),
                ClassificationSignal("medical center", 2.0),
            ),
        ),
    ),
    DocumentType.LAB_REPORT: (
        EvidenceGroup(
            name="lab_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("lab report", 4.0),
                ClassificationSignal("laboratory report", 4.0),
                ClassificationSignal("diagnostic report", 4.0),
                ClassificationSignal("pathology report", 4.0),
                ClassificationSignal("test report", 3.0),
            ),
        ),
        EvidenceGroup(
            name="specimen_testing",
            weight=3.5,
            signals=(
                ClassificationSignal("laboratory", 3.0),
                ClassificationSignal("specimen", 3.0),
                ClassificationSignal("specimen type", 3.0),
                ClassificationSignal("collection date", 2.0),
                ClassificationSignal("reference range", 3.0),
                ClassificationSignal("normal range", 3.0),
                ClassificationSignal("test result", 2.5),
                ClassificationSignal("units", 1.5),
                ClassificationSignal("flag", 1.5),
                ClassificationSignal("collected", 1.5),
            ),
        ),
        EvidenceGroup(
            name="lab_findings",
            weight=2.5,
            signals=(
                ClassificationSignal("analyte", 2.0),
                ClassificationSignal("methodology", 2.0),
                ClassificationSignal("biological reference", 2.5),
                ClassificationSignal("pathologist", 2.5),
            ),
        ),
    ),
    DocumentType.PRESCRIPTION: (
        EvidenceGroup(
            name="rx_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("prescription", 4.0),
                ClassificationSignal("rx", 3.5),
                ClassificationSignal("rx #", 3.5),
                ClassificationSignal("prescription order", 4.0),
            ),
        ),
        EvidenceGroup(
            name="medication_order",
            weight=3.5,
            signals=(
                ClassificationSignal("dosage", 2.5),
                ClassificationSignal("frequency", 2.0),
                ClassificationSignal("sig", 2.0),
                ClassificationSignal("dispense", 2.5),
                ClassificationSignal("refill", 2.5),
                ClassificationSignal("refills", 2.5),
                ClassificationSignal("take one", 2.0),
                ClassificationSignal("take 1", 2.0),
                ClassificationSignal("tablets", 1.5),
                ClassificationSignal("capsules", 1.5),
            ),
        ),
        EvidenceGroup(
            name="pharmacy_prescriber",
            weight=2.5,
            signals=(
                ClassificationSignal("pharmacy", 2.5),
                ClassificationSignal("pharmacist", 2.0),
                ClassificationSignal("prescriber", 2.5),
                ClassificationSignal("dea #", 2.5),
            ),
        ),
    ),
    DocumentType.INSURANCE: (
        EvidenceGroup(
            name="policy_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("insurance", 4.0),
                ClassificationSignal("policy number", 3.5),
                ClassificationSignal("policy #", 3.5),
                ClassificationSignal("member id", 3.0),
                ClassificationSignal("subscriber id", 3.0),
                ClassificationSignal("group number", 3.0),
                ClassificationSignal("group #", 3.0),
            ),
        ),
        EvidenceGroup(
            name="claim_coverage",
            weight=3.5,
            signals=(
                ClassificationSignal("claim number", 3.5),
                ClassificationSignal("claim #", 3.5),
                ClassificationSignal("insured", 2.5),
                ClassificationSignal("dependent", 2.0),
                ClassificationSignal("coverage", 2.5),
                ClassificationSignal("copay", 2.0),
                ClassificationSignal("deductible", 2.5),
                ClassificationSignal("coinsurance", 2.0),
                ClassificationSignal("benefits", 2.0),
            ),
        ),
        EvidenceGroup(
            name="underwriting_financial",
            weight=2.5,
            signals=(
                ClassificationSignal("premium", 2.5),
                ClassificationSignal("effective date", 2.0),
                ClassificationSignal("expiration date", 2.0),
                ClassificationSignal("plan type", 2.0),
                ClassificationSignal("carrier", 1.5),
            ),
        ),
    ),
    DocumentType.TAX_FORM: (
        EvidenceGroup(
            name="tax_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("tax form", 4.0),
                ClassificationSignal("form w 2", 4.5),
                ClassificationSignal("form 1099", 4.5),
                ClassificationSignal("form 1040", 4.5),
                ClassificationSignal("schedule c", 3.5),
                ClassificationSignal("income tax return", 4.0),
                ClassificationSignal("itr", 3.0),
            ),
        ),
        EvidenceGroup(
            name="tax_period",
            weight=3.0,
            signals=(
                ClassificationSignal("tax year", 3.0),
                ClassificationSignal("assessment year", 3.0),
                ClassificationSignal("filing status", 2.5),
                ClassificationSignal("tax period", 2.5),
            ),
        ),
        EvidenceGroup(
            name="tax_accounting",
            weight=3.0,
            signals=(
                ClassificationSignal("taxpayer", 2.5),
                ClassificationSignal("withholding", 2.5),
                ClassificationSignal("wages", 2.0),
                ClassificationSignal("federal income tax", 3.0),
                ClassificationSignal("state income tax", 3.0),
                ClassificationSignal("pan", 2.0),
                ClassificationSignal("tan", 2.0),
            ),
        ),
    ),
    DocumentType.IDENTITY_DOCUMENT: (
        EvidenceGroup(
            name="id_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("passport", 4.5),
                ClassificationSignal("driver license", 4.5),
                ClassificationSignal("driving license", 4.5),
                ClassificationSignal("identity card", 3.5),
                ClassificationSignal("national id", 3.5),
                ClassificationSignal("aadhaar", 3.5),
                ClassificationSignal("pan card", 3.5),
                ClassificationSignal("voter id", 3.5),
            ),
        ),
        EvidenceGroup(
            name="id_attributes",
            weight=3.0,
            signals=(
                ClassificationSignal("date of birth", 2.5),
                ClassificationSignal("dob", 2.0),
                ClassificationSignal("nationality", 2.5),
                ClassificationSignal("gender", 1.5),
                ClassificationSignal("expiry date", 2.0),
                ClassificationSignal("date of issue", 2.0),
                ClassificationSignal("issuing authority", 2.5),
            ),
        ),
    ),
    DocumentType.CONTRACT: (
        EvidenceGroup(
            name="agreement_identity",
            weight=4.0,
            signals=(
                ClassificationSignal("this agreement", 4.0),
                ClassificationSignal("agreement entered into", 4.0),
                ClassificationSignal("agreement by and between", 4.0),
                ClassificationSignal("contract", 3.5),
                ClassificationSignal("memorandum of understanding", 4.0),
                ClassificationSignal("mou", 3.0),
                ClassificationSignal("non disclosure agreement", 4.0),
                ClassificationSignal("nda", 3.5),
                ClassificationSignal("lease agreement", 4.0),
                ClassificationSignal("agreement", 1.5),  # Weak standalone signal
            ),
        ),
        EvidenceGroup(
            name="legal_structure",
            weight=3.0,
            signals=(
                ClassificationSignal("effective date", 2.5),
                ClassificationSignal("party", 2.0),
                ClassificationSignal("parties", 2.0),
                ClassificationSignal("witnesseth", 3.0),
                ClassificationSignal("whereas", 2.5),
                ClassificationSignal("terms and conditions", 2.5),
                ClassificationSignal("governing law", 2.5),
                ClassificationSignal("jurisdiction", 2.0),
                ClassificationSignal("termination", 2.0),
            ),
        ),
        EvidenceGroup(
            name="execution",
            weight=3.0,
            signals=(
                ClassificationSignal("in witness whereof", 3.5),
                ClassificationSignal("signature", 2.0),
                ClassificationSignal("signed by", 2.5),
                ClassificationSignal("authorized signatory", 3.0),
            ),
        ),
    ),
}


# Flattened backwards-compatible rules mapping
CLASSIFICATION_RULES: Dict[
    DocumentType,
    Tuple[ClassificationSignal, ...],
] = {
    doc_type: tuple(sig for group in groups for sig in group.signals)
    for doc_type, groups in EVIDENCE_GROUP_RULES.items()
}


# =========================================================================
# PRE-COMPILED REGEX PATTERNS FOR OPTIMAL RUNTIME LATENCY
# =========================================================================

OCR_NORMALIZATION_PATTERNS: Tuple[Tuple[Pattern, str], ...] = (
    (re.compile(r"\bacc0unt\b"), "account"),
    (re.compile(r"\ba/c\s+no\b"), "account no"),
    (re.compile(r"\ba/c\s+number\b"), "account number"),
    (re.compile(r"\ba/c\b"), "account"),
    (re.compile(r"\bacct\s+no\b"), "account no"),
    (re.compile(r"\bacct\s+number\b"), "account number"),
    (re.compile(r"\bacct\b"), "account"),
    (re.compile(r"\bstaternent\b"), "statement"),
    (re.compile(r"\bstatment\b"), "statement"),
    (re.compile(r"\bdiagno[s5]is\b"), "diagnosis"),
    (re.compile(r"\bpat[i1]ent\b"), "patient"),
    (re.compile(r"\bphys[i1]c[i1]an\b"), "physician"),
    (re.compile(r"\bhosp[i1]tal\b"), "hospital"),
    (re.compile(r"\bprescr[i1]pt[i1]on\b"), "prescription"),
    (re.compile(r"\b[i1]nsurance\b"), "insurance"),
    (re.compile(r"\b[i1]nvo[i1]ce\b"), "invoice"),
    (re.compile(r"\brece[i1]pt\b"), "receipt"),
    (re.compile(r"\bpol[i1]cy\b"), "policy"),
    (re.compile(r"\b[i1]fsc\s+c0de\b"), "ifsc code"),
    (re.compile(r"\bstatement\s+of\s+accounts?\b"), "statement of account"),
    # Regional British / Commonwealth spelling normalization
    (re.compile(r"\bdriving\s+licence\b"), "driving license"),
    (re.compile(r"\bdriver\s+licence\b"), "driver license"),
    (re.compile(r"\blicence\b"), "license"),
)

# Pre-compile exact word-boundary regexes for all single-word signals
PRECOMPILED_WORD_BOUNDARIES: Dict[str, Pattern] = {
    sig_norm: re.compile(rf"\b{re.escape(sig_norm)}\b")
    for group_tuple in EVIDENCE_GROUP_RULES.values()
    for group in group_tuple
    for sig in group.signals
    if " " not in (sig_norm := _normalize_signal_string(sig.text))
}



class DocumentClassificationService:
    """
    Robust, evidence-group based deterministic document classifier.
    Combines semantic evidence groups, terminology normalization, pre-compiled regex matching,
    and conservative OCR error handling.
    """

    def __init__(
        self,
        group_rules: Optional[
            Mapping[DocumentType, Sequence[EvidenceGroup]]
        ] = None,
        minimum_score: float = MIN_CLASSIFICATION_SCORE,
        max_confidence_score: float = MAX_CONFIDENCE_SCORE,
    ):
        self.group_rules = group_rules or EVIDENCE_GROUP_RULES
        self.minimum_score = minimum_score
        self.max_confidence_score = max_confidence_score
        self.rules = CLASSIFICATION_RULES

    def classify(
        self,
        document: Document,
        extracted_text: Optional[str] = None,
    ) -> ClassificationResult:
        normalized_text = self._build_classification_text(
            document,
            extracted_text,
        )

        if not normalized_text.strip():
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN.value,
                confidence_score=0.0,
                matched_signals=tuple(),
                matched_groups=tuple(),
                reason="Document and extracted text are empty.",
            )

        scored_candidates: List[Tuple[DocumentType, float, int, int, List[str], List[str]]] = []

        for doc_type, groups in self.group_rules.items():
            total_score, active_groups, total_groups, matches, group_names = (
                self._score_document_groups(normalized_text, groups)
            )
            if active_groups > 0:
                scored_candidates.append((
                    doc_type,
                    total_score,
                    active_groups,
                    total_groups,
                    matches,
                    group_names,
                ))

        if not scored_candidates:
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN.value,
                confidence_score=0.0,
                matched_signals=tuple(),
                matched_groups=tuple(),
                reason="No matching classification evidence groups found.",
            )

        # Sort by total_score and group diversity
        scored_candidates.sort(
            key=lambda x: (x[1] * (x[2] / max(1, x[3])), x[1]),
            reverse=True,
        )

        best_type, best_score, active_groups, total_groups, best_matches, active_group_names = (
            scored_candidates[0]
        )

        # Require minimum aggregate score and evidence diversity
        diversity_ratio = active_groups / max(1, total_groups)
        has_primary_identity = any(
            ("identity" in g or "structure" in g) and g != "agreement_identity"
            for g in active_group_names
        ) or (
            "agreement_identity" in active_group_names
            and any(sig != "agreement" for sig in best_matches)
        )

        # Standalone weak keyword / single-group isolation check:
        # If only 1 group matched without strong primary structural/identity phrases and score is low, reject to UNKNOWN.
        if active_groups == 1 and not has_primary_identity and best_score < 3.5:
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN.value,
                confidence_score=0.15,
                matched_signals=tuple(best_matches),
                matched_groups=tuple(active_group_names),
                reason=f"Insufficient diversity for {best_type.value}: only 1 weak group matched without primary structural evidence.",
            )

        if best_score < self.minimum_score:
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN.value,
                confidence_score=0.0,
                matched_signals=tuple(),
                matched_groups=tuple(),
                reason=f"Score {best_score:.2f} is below minimum threshold ({self.minimum_score}).",
            )

        # Calculate calibrated confidence
        second_score = scored_candidates[1][1] if len(scored_candidates) > 1 else 0.0
        confidence = self._calculate_calibrated_confidence(
            best_score=best_score,
            second_score=second_score,
            diversity_ratio=diversity_ratio,
            has_primary_identity=has_primary_identity,
        )

        return ClassificationResult(
            document_type=best_type.value,
            confidence_score=confidence,
            matched_signals=tuple(best_matches),
            matched_groups=tuple(active_group_names),
            reason=f"Classified as {best_type.value} with {active_groups}/{total_groups} active evidence groups (score={best_score:.1f}).",
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
        return self._normalize_classification_text(raw_text[:MAX_TEXT_CHARS])

    @staticmethod
    def _score_document_groups(
        text: str,
        groups: Sequence[EvidenceGroup],
    ) -> Tuple[float, int, int, List[str], List[str]]:
        total_score = 0.0
        active_group_count = 0
        all_matches: List[str] = []
        active_group_names: List[str] = []

        for group in groups:
            group_score = 0.0
            group_matches = []
            for signal in group.signals:
                if DocumentClassificationService._contains_signal_fast(text, signal):
                    group_score += signal.weight
                    group_matches.append(signal.text)

            if len(group_matches) >= group.min_matches:
                active_group_count += 1
                active_group_names.append(group.name)
                total_score += group_score * (1.0 + (group.weight / 10.0))
                all_matches.extend(group_matches)

        return total_score, active_group_count, len(groups), all_matches, active_group_names

    @staticmethod
    def _contains_signal_fast(text: str, signal: ClassificationSignal) -> bool:
        if signal.has_space:
            return signal.normalized_text in text

        compiled = PRECOMPILED_WORD_BOUNDARIES.get(signal.normalized_text)
        if compiled is not None:
            return compiled.search(text) is not None

        return signal.normalized_text in text

    @staticmethod
    def _contains_signal(text: str, signal: str) -> bool:
        norm = _normalize_signal_string(signal)
        if " " in norm:
            return norm in text

        compiled = PRECOMPILED_WORD_BOUNDARIES.get(norm)
        if compiled is not None:
            return compiled.search(text) is not None

        return re.search(rf"\b{re.escape(norm)}\b", text) is not None

    @staticmethod
    def _normalize_signal(value: str) -> str:
        return _normalize_signal_string(value)

    @staticmethod
    def _normalize_classification_text(value: str) -> str:
        """
        Conservative normalization with OCR character and terminology mapping for classification evidence.
        """
        t = value.lower()
        # Fast-path: only run OCR / spelling substitution passes if indicator substrings or digits exist
        if any(char in t for char in ("0", "1", "5", "licen", "stater", "statm", "diagno", "acct", "a/c")):
            for pattern, repl in OCR_NORMALIZATION_PATTERNS:
                t = pattern.sub(repl, t)

        t = RE_CLEAN_PUNCT.sub(" ", t)
        t = RE_CLEAN_NON_ALPHANUM.sub(" ", t)
        t = RE_CLEAN_WHITESPACE.sub(" ", t)
        return t.strip()

    @staticmethod
    def _file_suffix(filename: Optional[str]) -> str:
        if not filename:
            return ""
        return Path(filename).suffix.lstrip(".")

    def _calculate_calibrated_confidence(
        self,
        best_score: float,
        second_score: float,
        diversity_ratio: float,
        has_primary_identity: bool,
    ) -> float:
        """
        Calibrates confidence based on signal score, evidence diversity, margin over competing types,
        and primary identity presence.
        """
        # Base confidence from score
        raw_conf = min(best_score / self.max_confidence_score, 1.0)

        # Diversity multiplier
        div_multiplier = 0.50 + (0.50 * diversity_ratio)
        identity_bonus = 0.10 if has_primary_identity else 0.0

        # Margin penalty if competing type is very close
        margin_penalty = 0.0
        if second_score > 0 and (best_score - second_score) < 2.0:
            margin_penalty = 0.10

        calibrated = (raw_conf * div_multiplier) + identity_bonus - margin_penalty
        return round(max(0.20, min(calibrated, 0.98)), 4)


document_classification_service = DocumentClassificationService()


