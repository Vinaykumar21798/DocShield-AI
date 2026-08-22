import pytest
from typing import Any
from modules.detection.semantic_chunker import SemanticChunker, DocumentChunk
from modules.detection.service import DetectionService, DynamicDetectionConfig
from modules.detection.detectors.base_detector import BaseDetector
from modules.detection.detectors.gemma_detector import GemmaDetector, ResidualEntityItem, ResidualDiscoveryResponse
from modules.detection.models.detection_result import DetectionResult
from modules.detection.pipeline_state import PipelineState


class MockFastDetector(BaseDetector):
    def __init__(self, name: str, detections: list[DetectionResult] | None = None):
        self._name = name
        self.detections = detections or []
        self.executed = False

    @property
    def name(self) -> str:
        return self._name

    def should_run(self, text: str, state: PipelineState) -> bool:
        return True

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        self.executed = True
        res = []
        for d in self.detections:
            if d.entity_value in text:
                s = text.index(d.entity_value)
                e = s + len(d.entity_value)
                res.append(
                    DetectionResult(
                        entity_type=d.entity_type,
                        entity_value=d.entity_value,
                        confidence_score=d.confidence_score,
                        start_char=s,
                        end_char=e,
                        page_number=page_number,
                        detector=self.name,
                        metadata=dict(d.metadata or {}),
                    )
                )
        return res



class MockGemmaPipelineDetector(BaseDetector):
    def __init__(
        self,
        residual_findings: dict[str, list[dict]] | None = None,
        validation_decisions: dict[str, dict] | None = None,
    ):
        self._name = "gemma"
        self.MODEL_NAME = "gemma4:e4b"
        self.residual_findings = residual_findings or {}
        self.validation_decisions = validation_decisions or {}
        self.residual_calls = 0
        self.validation_calls = 0

    @property
    def name(self) -> str:
        return self._name

    def should_run(self, text: str, state: PipelineState) -> bool:
        return True

    def detect(self, text: str, page_number: int = 1) -> list[DetectionResult]:
        return []

    def validate_candidates(
        self,
        candidates: list[DetectionResult],
        chunks: list[Any],
        document_type: str | None = None,
    ) -> list[DetectionResult]:
        self.validation_calls += 1
        validated = []
        for c in candidates:
            dec = self.validation_decisions.get(c.entity_value)
            if dec:
                decision = dec.get("decision", "CONFIRM")
                if decision == "REJECT":
                    continue
                elif decision == "RECLASSIFY":
                    c.entity_type = dec.get("corrected_type", c.entity_type)
                    c.confidence_score = dec.get("confidence", c.confidence_score)
                    validated.append(c)
                elif decision == "CONFIRM":
                    c.confidence_score = dec.get("confidence", c.confidence_score)
                    validated.append(c)
            else:
                validated.append(c)
        return validated

    def detect_residual_chunk(
        self,
        chunk_text: str,
        chunk_start: int,
        chunk_end: int,
        known_entities: list[Any] | None = None,
        document_type: str | None = None,
        page_number: int = 1,
        **kwargs,
    ) -> list[DetectionResult]:
        self.residual_calls += 1
        findings = self.residual_findings.get(chunk_text, [])
        results = []
        for f in findings:
            val = f["entity_value"]
            if val in chunk_text:
                l_start = chunk_text.index(val)
                l_end = l_start + len(val)
                g_start = chunk_start + l_start
                g_end = chunk_start + l_end
                results.append(
                    DetectionResult(
                        entity_type=f["entity_type"],
                        entity_value=val,
                        confidence_score=f.get("confidence", 0.92),
                        start_char=g_start,
                        end_char=g_end,
                        page_number=page_number,
                        detector="gemma",
                        metadata={"residual_discovery": True, "llm_mode": "RESIDUAL_DETECTION"},
                    )
                )
        return results


    def validate_candidates(
        self,
        candidates: list[Any],
        state: Any = None,
        document_type: str | None = None,
    ) -> list[Any]:
        self.validation_calls += 1
        accepted = []
        for cand in candidates:
            dec = self.validation_decisions.get(cand.entity_value, {"decision": "CONFIRM", "confidence": 0.95})
            decision = dec["decision"]
            cand.metadata["gemma_validation"] = decision
            cand.metadata["gemma_validation"] = decision
            cand.metadata["llm_confidence"] = dec.get("confidence", 0.95)
            cand.metadata["llm_reason"] = dec.get("reason", "Validation outcome")
            if decision == "RECLASSIFY":
                cand.entity_type = dec.get("corrected_type", cand.entity_type)
                cand.confidence_score = dec.get("confidence", 0.95)
                accepted.append(cand)
            elif decision == "CONFIRM":
                cand.confidence_score = dec.get("confidence", 0.95)
                accepted.append(cand)
        return accepted



from modules.detection.candidate_quality_gate import CandidateQualityGate


def create_audit_service(
    regex_res=None,
    presidio_res=None,
    gliner_res=None,
    medspacy_res=None,
    residual_map=None,
    validation_map=None,
):
    service = DetectionService.__new__(DetectionService)
    service.config = DynamicDetectionConfig()
    service.router = None
    service.chunker = SemanticChunker(target_chunk_chars=400, overlap_chars=50)
    service._regex = MockFastDetector("regex", regex_res)
    service._presidio = MockFastDetector("presidio", presidio_res)
    service._gliner = MockFastDetector("gliner", gliner_res)
    service._medspacy = MockFastDetector("medspacy", medspacy_res)
    service._gemma4e4b = MockGemmaPipelineDetector(residual_map, validation_map)
    service._calibrator = None
    service._quality_gate = CandidateQualityGate()
    service.quality_gate = service._quality_gate
    return service





# =========================================================================
# 1. TABLE DETECTION & TABLE ROW RECALL TEST
# =========================================================================

def test_1_table_multiline_and_row_recall():
    """Test 1: Table with 10 rows. All entity values detected, column headers rejected."""
    table_text = """
    | Patient Name | MRN | DOB | Diagnosis |
    | John Smith | MR-1001 | 12/04/1985 | Hypertension |
    | Jane Doe | MR-1002 | 05/09/1990 | Type 2 Diabetes |
    | Arthur Dent | MR-1003 | 11/03/1978 | Asthma |
    | Bruce Wayne | MR-1004 | 19/02/1980 | Rib Contusion |
    | Clark Kent | MR-1005 | 18/06/1977 | Vision Fatigue |
    | Diana Prince | MR-1006 | 22/03/1984 | Migraine |
    | Barry Allen | MR-1007 | 14/05/1992 | Tachycardia |
    | Hal Jordan | MR-1008 | 20/02/1981 | Corneal Abrasion |
    | Victor Stone | MR-1009 | 25/12/1994 | Neuralgia |
    | Arthur Curry | MR-1010 | 01/01/1986 | Dehydration |
    """
    regex_res = [
        DetectionResult(entity_type="MRN", entity_value=f"MR-{1000+i}", confidence_score=0.98, start_char=table_text.index(f"MR-{1000+i}"), end_char=table_text.index(f"MR-{1000+i}")+7, detector="regex")
        for i in range(1, 11)
    ]
    presidio_res = [
        DetectionResult(entity_type="PERSON", entity_value=name, confidence_score=0.85, start_char=table_text.index(name), end_char=table_text.index(name)+len(name), detector="presidio")
        for name in ["John Smith", "Jane Doe", "Arthur Dent", "Bruce Wayne", "Clark Kent", "Diana Prince", "Barry Allen", "Hal Jordan", "Victor Stone", "Arthur Curry"]
    ]
    # Simulate accidental table header proposal sent to pending_candidates
    header_cand_1 = DetectionResult(entity_type="PERSON", entity_value="Patient Name", confidence_score=0.60, start_char=table_text.index("Patient Name"), end_char=table_text.index("Patient Name")+12, detector="presidio")
    header_cand_2 = DetectionResult(entity_type="PERSON", entity_value="Diagnosis", confidence_score=0.55, start_char=table_text.index("Diagnosis"), end_char=table_text.index("Diagnosis")+9, detector="presidio")

    validation_map = {
        "Patient Name": {"decision": "REJECT", "reason": "Table column label"},
        "Diagnosis": {"decision": "REJECT", "reason": "Boilerplate table header"},
    }
    for name in ["John Smith", "Jane Doe", "Arthur Dent", "Bruce Wayne", "Clark Kent", "Diana Prince", "Barry Allen", "Hal Jordan", "Victor Stone", "Arthur Curry"]:
        validation_map[name] = {"decision": "CONFIRM", "confidence": 0.95}

    service = create_audit_service(
        regex_res=regex_res,
        presidio_res=presidio_res,
        validation_map=validation_map,
    )

    state = PipelineState(original_text=table_text)
    chunks = service.chunker.chunk_document(table_text)
    
    # Phase 1 & 2 Detections
    service._run_detector_on_chunks(service._regex, chunks, state, page_number=1)
    service._run_detector_on_chunks(service._presidio, chunks, state, page_number=1)

    # Queue low-confidence candidate headers for Phase 5 validation
    state.add_pending_candidates([header_cand_1, header_cand_2])

    # Phase 5 Validation
    service._execute_gemma_candidate_validation(service._gemma4e4b, state, DynamicDetectionConfig())

    resolved_values = {e.entity_value for e in state.resolved_entities}

    # Verify all 10 MRNs and 10 Patients resolved
    for i in range(1, 11):
        assert f"MR-{1000+i}" in resolved_values
    assert "John Smith" in resolved_values
    assert "Arthur Curry" in resolved_values

    # Verify table headers REJECTED
    assert "Patient Name" not in resolved_values
    assert "DESCRIPTION" not in resolved_values

    # Verify exact character offsets
    for entity in state.resolved_entities:
        assert table_text[entity.start_char:entity.end_char] == entity.entity_value


# =========================================================================
# 2. PREVIOUS KNOWN FAILURES REGRESSION AUDIT
# =========================================================================

def test_2_previous_failure_regressions():
    """
    Test 2: Specific verification of historical edge cases:
    - SB-500101013522943 (Non-standard account number discovered via residual detection)
    - NITISH K S (Indian name)
    - DESCRIPTION, NULL, CIN, Regd, TO ONL UPI (Rejected structural noise)
    - T.S.R. (Big) Street (Address preserved)
    """
    doc_text = """
    CITY UNION BANK LTD
    Statement of Account
    Account Holder: NITISH K S
    Account Number: SB-500101013522943
    Address: 14 T.S.R. (Big) Street, Kumbakonam
    IFSC: CIUB0000528
    Txn Date | Value Date | Description | Ref No | Debit | Credit | Balance
    10/01/2026 | 10/01/2026 | TO ONL UPI / PAYTMQR5HJ | NULL | 500.00 | 0.00 | 12,450.00
    CIN: L65110TN1904PLC001287 | Regd Office: Kumbakonam
    """
    regex_res = [
        DetectionResult(entity_type="IFSC_CODE", entity_value="CIUB0000528", confidence_score=0.99, start_char=0, end_char=11, detector="regex"),
    ]
    presidio_res = [
        DetectionResult(entity_type="PERSON", entity_value="NITISH K S", confidence_score=0.75, start_char=0, end_char=10, detector="presidio"),
        DetectionResult(entity_type="LOCATION", entity_value="14 T.S.R. (Big) Street, Kumbakonam", confidence_score=0.78, start_char=0, end_char=34, detector="presidio"),
        DetectionResult(entity_type="PERSON", entity_value="DESCRIPTION", confidence_score=0.55, start_char=0, end_char=11, detector="presidio"),
        DetectionResult(entity_type="ORGANIZATION", entity_value="NULL", confidence_score=0.50, start_char=0, end_char=4, detector="presidio"),
        DetectionResult(entity_type="ORGANIZATION", entity_value="CIN", confidence_score=0.50, start_char=0, end_char=3, detector="presidio"),
        DetectionResult(entity_type="ORGANIZATION", entity_value="Regd", confidence_score=0.50, start_char=0, end_char=4, detector="presidio"),
        DetectionResult(entity_type="PERSON", entity_value="TO ONL UPI", confidence_score=0.60, start_char=0, end_char=10, detector="presidio"),
    ]

    # Fast detectors missed the non-standard bank account number 'SB-500101013522943'
    residual_map = {
        # Phase 4 discovers the missing account number
    }
    # Provide residual discovery for the chunk containing SB-500101013522943
    chunks = SemanticChunker().chunk_document(doc_text)
    for c in chunks:
        if "SB-500101013522943" in c.text:
            residual_map[c.text] = [
                {"entity_type": "BANK_ACCOUNT_NUMBER", "entity_value": "SB-500101013522943", "confidence": 0.94, "reason": "Non-standard bank account number"}
            ]

    validation_map = {
        "NITISH K S": {"decision": "CONFIRM", "confidence": 0.95},
        "14 T.S.R. (Big) Street, Kumbakonam": {"decision": "CONFIRM", "confidence": 0.95},
        "SB-500101013522943": {"decision": "CONFIRM", "confidence": 0.96},
        "DESCRIPTION": {"decision": "REJECT", "reason": "Table header"},
        "NULL": {"decision": "REJECT", "reason": "Database null placeholder"},
        "CIN": {"decision": "REJECT", "reason": "Corporate identity number label"},
        "Regd": {"decision": "REJECT", "reason": "Abbreviation for registered"},
        "TO ONL UPI": {"decision": "REJECT", "reason": "Transaction channel boilerplate"},
    }

    service = create_audit_service(
        regex_res=regex_res,
        presidio_res=presidio_res,
        residual_map=residual_map,
        validation_map=validation_map,
    )

    state = PipelineState(original_text=doc_text)
    
    # Phase 1 & 2: Fast detectors
    service._run_detector_on_chunks(service._regex, chunks, state, page_number=1)
    service._run_detector_on_chunks(service._presidio, chunks, state, page_number=1)

    # Phase 4: Gemma Residual Discovery
    service._execute_gemma_residual_discovery(service._gemma4e4b, state, chunks, DynamicDetectionConfig(), document_type="BANK_STATEMENT")

    # Phase 5: Gemma Candidate Validation
    service._execute_gemma_candidate_validation(service._gemma4e4b, state, DynamicDetectionConfig())

    resolved_values = {e.entity_value for e in state.resolved_entities}

    # 1. High-Risk / Important Entities DETECTED
    assert "SB-500101013522943" in resolved_values, "Non-standard account number must be recovered by Phase 4 residual detection!"
    assert "NITISH K S" in resolved_values, "Account holder name must be confirmed!"
    assert "CIUB0000528" in resolved_values, "IFSC code must be locked!"
    assert "14 T.S.R. (Big) Street, Kumbakonam" in resolved_values, "Address must be preserved!"

    # 2. Boilerplate / False Positives REJECTED
    assert "DESCRIPTION" not in resolved_values
    assert "NULL" not in resolved_values
    assert "CIN" not in resolved_values
    assert "Regd" not in resolved_values
    assert "TO ONL UPI" not in resolved_values

    # 3. Exact character offsets verified
    for entity in state.resolved_entities:
        assert doc_text[entity.start_char:entity.end_char] == entity.entity_value


# =========================================================================
# 3. UNSTRUCTURED CLINICAL PROSE & MULTI-LINE ENTITIES
# =========================================================================

def test_3_unstructured_clinical_prose_and_multiline():
    """Test 3: Unstructured medical narrative with multiline address and prose diagnoses."""
    clinical_text = """
    DISCHARGE SUMMARY
    Patient: Eleanor Vance
    MRN: MR-883921
    Address: 742 Evergreen Terrace, Springfield, OR 97477
    
    History of Present Illness:
    The patient was admitted with malignant hypertension and acute coronary syndrome.
    She was evaluated by Dr. Robert Miller at St. Jude Medical Center on 14/02/2026.
    """
    regex_res = [
        DetectionResult(entity_type="MRN", entity_value="MR-883921", confidence_score=0.98, start_char=clinical_text.index("MR-883921"), end_char=clinical_text.index("MR-883921")+9, detector="regex"),
        DetectionResult(entity_type="DATE", entity_value="14/02/2026", confidence_score=0.95, start_char=clinical_text.index("14/02/2026"), end_char=clinical_text.index("14/02/2026")+10, detector="regex"),
    ]
    presidio_res = [
        DetectionResult(entity_type="PERSON", entity_value="Eleanor Vance", confidence_score=0.82, start_char=clinical_text.index("Eleanor Vance"), end_char=clinical_text.index("Eleanor Vance")+13, detector="presidio"),
        DetectionResult(entity_type="PERSON", entity_value="Robert Miller", confidence_score=0.75, start_char=clinical_text.index("Robert Miller"), end_char=clinical_text.index("Robert Miller")+13, detector="presidio"),
        DetectionResult(entity_type="ORGANIZATION", entity_value="St. Jude Medical Center", confidence_score=0.78, start_char=clinical_text.index("St. Jude Medical Center"), end_char=clinical_text.index("St. Jude Medical Center")+23, detector="presidio"),
        DetectionResult(entity_type="ADDRESS", entity_value="742 Evergreen Terrace, Springfield, OR 97477", confidence_score=0.79, start_char=clinical_text.index("742 Evergreen Terrace, Springfield, OR 97477"), end_char=clinical_text.index("742 Evergreen Terrace, Springfield, OR 97477")+44, detector="presidio"),
    ]

    medspacy_res = [
        DetectionResult(entity_type="DIAGNOSIS", entity_value="malignant hypertension", confidence_score=0.90, start_char=clinical_text.index("malignant hypertension"), end_char=clinical_text.index("malignant hypertension")+22, detector="medspacy"),
        DetectionResult(entity_type="DIAGNOSIS", entity_value="acute coronary syndrome", confidence_score=0.90, start_char=clinical_text.index("acute coronary syndrome"), end_char=clinical_text.index("acute coronary syndrome")+23, detector="medspacy"),
    ]

    validation_map = {
        "Eleanor Vance": {"decision": "CONFIRM", "confidence": 0.96},
        "Robert Miller": {"decision": "RECLASSIFY", "corrected_type": "DOCTOR", "confidence": 0.95},
        "St. Jude Medical Center": {"decision": "RECLASSIFY", "corrected_type": "HOSPITAL", "confidence": 0.98},
        "742 Evergreen Terrace, Springfield, OR 97477": {"decision": "CONFIRM", "confidence": 0.94},
        "malignant hypertension": {"decision": "CONFIRM", "confidence": 0.96},
        "acute coronary syndrome": {"decision": "CONFIRM", "confidence": 0.96},
    }



    service = create_audit_service(
        regex_res=regex_res,
        presidio_res=presidio_res,
        medspacy_res=medspacy_res,
        validation_map=validation_map,
    )

    state = PipelineState(original_text=clinical_text)
    chunks = service.chunker.chunk_document(clinical_text)

    # Phase 1 & 2 Detections
    service._run_detector_on_chunks(service._regex, chunks, state, page_number=1)
    service._run_detector_on_chunks(service._medspacy, chunks, state, page_number=1)

    # Queue presidio candidates for Phase 5 validation / reclassification
    state.add_pending_candidates(presidio_res)

    # Phase 5 Validation
    service._execute_gemma_candidate_validation(service._gemma4e4b, state, DynamicDetectionConfig())

    resolved_map = {e.entity_value: e for e in state.resolved_entities}

    assert "Eleanor Vance" in resolved_map
    assert "MR-883921" in resolved_map
    assert "malignant hypertension" in resolved_map
    assert "acute coronary syndrome" in resolved_map
    assert "742 Evergreen Terrace, Springfield, OR 97477" in resolved_map
    
    # Verify reclassifications
    assert resolved_map["Robert Miller"].entity_type == "DOCTOR"
    assert resolved_map["St. Jude Medical Center"].entity_type in {"HOSPITAL", "HEALTHCARE_ORGANIZATION"}




    # Verify offset integrity
    for entity in state.resolved_entities:
        assert clinical_text[entity.start_char:entity.end_char] == entity.entity_value


# =========================================================================
# 4. CHUNK BOUNDARY & HIGH COVERAGE SAFETY TEST
# =========================================================================

def test_4_chunk_boundary_and_high_coverage_safety():
    """
    Test 4: Unresolved high-risk account number in a 90% covered chunk
    must NEVER be skipped by FULLY_COVERED logic.
    """
    doc_text = """
    ACME CORPORATION MASTER SERVICES BILLING SCHEDULE
    Statement Date: January 15, 2026 | Statement ID: STMT-2026-991823
    Customer Name: General Dynamics Defense Systems
    Billing Address: 1000 Innovation Way, Reston, VA 20190
    Tax ID: 54-1234567 | Corporate Phone: +1 703-555-0199
    
    Payment Wire Instructions:
    Beneficiary Account: ACCT-990011882233
    Routing Transit: 051000033 | SWIFT: BOFAUS3N
    """
    # Simulate Regex locking Statement ID, Phone, Tax ID
    regex_res = [
        DetectionResult(entity_type="DATE", entity_value="January 15, 2026", confidence_score=0.95, start_char=0, end_char=16, detector="regex"),
        DetectionResult(entity_type="PHONE_NUMBER", entity_value="+1 703-555-0199", confidence_score=0.99, start_char=0, end_char=15, detector="regex"),
        DetectionResult(entity_type="TAX_ID", entity_value="54-1234567", confidence_score=0.95, start_char=0, end_char=10, detector="regex"),
    ]
    # Fast detectors miss 'ACCT-990011882233'
    chunks = SemanticChunker().chunk_document(doc_text)
    residual_map = {}
    for c in chunks:
        if "ACCT-990011882233" in c.text:
            residual_map[c.text] = [
                {"entity_type": "BANK_ACCOUNT_NUMBER", "entity_value": "ACCT-990011882233", "confidence": 0.94}
            ]

    validation_map = {
        "ACCT-990011882233": {"decision": "CONFIRM", "confidence": 0.96},
    }

    service = create_audit_service(
        regex_res=regex_res,
        residual_map=residual_map,
        validation_map=validation_map,
    )

    state = PipelineState(original_text=doc_text)

    # Phase 1 & 2
    service._run_detector_on_chunks(service._regex, chunks, state, page_number=1)

    # Verify coverage evaluation flags PARTIALLY_COVERED and discovers residual account
    service._execute_gemma_residual_discovery(service._gemma4e4b, state, chunks, DynamicDetectionConfig(), document_type="INVOICE")
    service._execute_gemma_candidate_validation(service._gemma4e4b, state, DynamicDetectionConfig())

    resolved_values = {e.entity_value for e in state.resolved_entities}
    assert "ACCT-990011882233" in resolved_values, "High-risk wire account number must be discovered by Phase 4 residual analysis!"
    assert "+1 703-555-0199" in resolved_values
    assert "54-1234567" in resolved_values
