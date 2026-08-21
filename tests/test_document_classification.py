import pytest
from database.models import Document
from modules.classification.service import DocumentClassificationService, DocumentType, document_classification_service


def create_test_doc(filename="doc.pdf", file_type="pdf"):
    doc = Document()
    doc.filename = filename
    doc.stored_filename = filename
    doc.file_type = file_type
    return doc


def test_1_bank_statement_alternate_phrasing_city_union_bank():
    """Test 1: Indian/Regional Bank Statement with 'Statement of Account', IFSC, Account No -> BANK_STATEMENT."""
    doc = create_test_doc("city_union_bank_stmt.pdf")
    text = """
    City Union Bank Ltd.
    Statement of Account
    Account No: 500101013522943
    IFSC Code: CIUB0000001
    Branch: Downtown Branch
    Opening Balance: 12,450.00
    Closing Balance: 15,900.00
    Txn Date | Value Date | Description | Debit | Credit | Balance
    10/01/2026 | 10/01/2026 | UPI/Transfer | 500.00 | 0.00 | 11,950.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.BANK_STATEMENT.value
    assert res.confidence_score >= 0.85
    assert "banking_identity" in res.matched_groups
    assert "banking_structure" in res.matched_groups
    assert "banking_balance" in res.matched_groups


def test_2_bank_statement_passbook_and_acct_no():
    """Test 2: Passbook statement with 'Acct No' and 'Available Balance' -> BANK_STATEMENT."""
    doc = create_test_doc("passbook_statement.pdf")
    text = """
    State Bank Passbook
    Acct No: 9988221100
    IFSC: SBIN0001234
    Available Balance: $4,500.00
    Withdrawals: 200.00
    Deposits: 1,000.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.BANK_STATEMENT.value
    assert res.confidence_score >= 0.80


def test_3_ocr_noisy_bank_statement():
    """Test 3: OCR noisy bank statement ('Acc0unt Statement', 'IFSC C0de', 'Staternent') -> BANK_STATEMENT."""
    doc = create_test_doc("scanned_bank_doc.pdf")
    text = """
    Acc0unt Statement
    IFSC C0de: HDFC0001829
    A/C No: 1092837465
    Staternent Period: Jan 2026
    Closing Balance: 28,000.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.BANK_STATEMENT.value
    assert res.confidence_score >= 0.75


def test_4_standard_invoice():
    """Test 4: Invoice with Bill To, Subtotal, Amount Due -> INVOICE."""
    doc = create_test_doc("invoice_1042.pdf")
    text = """
    TAX INVOICE
    Invoice Number: INV-2026-001
    Bill To: Acme Corp
    Ship To: Acme Warehouse
    Amount Due: $1,250.00
    Payment Terms: Net 30
    Due Date: 15/02/2026
    Subtotal: $1,150.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.INVOICE.value
    assert res.confidence_score >= 0.85
    assert "invoice_identity" in res.matched_groups


def test_5_retail_receipt():
    """Test 5: Retail Receipt with Cashier, Change Due, Store # -> RECEIPT."""
    doc = create_test_doc("store_receipt.pdf")
    text = """
    SALES RECEIPT
    Store #4421
    Cashier: Sarah M.
    Transaction: 99182374
    Items Purchased:
    - Office Supplies: $45.00
    Cash Tendered: $50.00
    Change Due: $5.00
    Payment Method: Cash
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.RECEIPT.value
    assert res.confidence_score >= 0.85


def test_6_medical_record_clinical_note():
    """Test 6: Clinical Encounter with Patient, Diagnosis, Physician, Hospital -> MEDICAL_RECORD."""
    doc = create_test_doc("clinical_encounter.pdf")
    text = """
    DISCHARGE SUMMARY
    Patient Name: Eleanor Vance
    MRN: MR-883921
    Date of Birth: 04/12/1980
    Attending Physician: Dr. Robert Miller, MD
    Hospital: St. Jude Medical Center
    Chief Complaint: Acute chest pain
    Diagnosis: Malignant hypertension, essential
    History of Present Illness: Patient presented with severe headache.
    Allergies: Penicillin
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.MEDICAL_RECORD.value
    assert res.confidence_score >= 0.90
    assert "clinical_identity" in res.matched_groups
    assert "patient_identity" in res.matched_groups


def test_7_diagnostic_lab_report():
    """Test 7: Laboratory Diagnostic Report -> LAB_REPORT."""
    doc = create_test_doc("lab_blood_work.pdf")
    text = """
    LABORATORY TEST REPORT
    Laboratory: Quest Diagnostics
    Specimen Type: Blood Serum
    Collection Date: 12/01/2026
    Test Result:
    - Glucose, Fasting: 110 mg/dL | Reference Range: 70 - 99 | FLAG: High
    - HbA1c: 6.4% | Normal Range: 4.0 - 5.6
    Biological Reference: Standard
    Pathologist: Dr. Karen White
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.LAB_REPORT.value
    assert res.confidence_score >= 0.85


def test_8_pharmacy_prescription():
    """Test 8: Prescription order with Rx, dosage, refills, pharmacy -> PRESCRIPTION."""
    doc = create_test_doc("rx_slip.pdf")
    text = """
    PRESCRIPTION ORDER
    Rx #: 8829103
    Pharmacy: Walgreens Pharmacy #104
    Prescriber: Dr. John Smith, MD
    DEA #: AB1234567
    Medication: Lisinopril 20mg Tablets
    Sig: Take 1 tablet daily by mouth
    Dispense: 30 tablets
    Refills: 3
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.PRESCRIPTION.value
    assert res.confidence_score >= 0.85


def test_9_health_insurance_policy():
    """Test 9: Insurance policy & claim benefits -> INSURANCE."""
    doc = create_test_doc("health_policy.pdf")
    text = """
    HEALTH INSURANCE POLICY SCHEDULE
    Policy Number: POL-9928192
    Member ID: MEM-1029384
    Group Number: GRP-55201
    Insured: Arthur Dent
    Coverage: Comprehensive Medical & Dental
    Deductible: $1,500.00
    Copay: $25.00 Specialist
    Coinsurance: 80/20
    Premium: $450.00 monthly
    Effective Date: 01/01/2026
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.INSURANCE.value
    assert res.confidence_score >= 0.85


def test_10_tax_return_form():
    """Test 10: Tax Form W-2 / 1099 -> TAX_FORM."""
    doc = create_test_doc("w2_statement.pdf")
    text = """
    FORM W-2 Wage and Tax Statement
    Tax Year: 2025
    Taxpayer: John Doe
    Wages, tips, other comp: $85,000.00
    Federal Income Tax Withheld: $12,500.00
    Social Security Wages: $85,000.00
    State Income Tax: $3,400.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.TAX_FORM.value
    assert res.confidence_score >= 0.85


def test_11_government_identity_document():
    """Test 11: Passport / Driver License -> IDENTITY_DOCUMENT."""
    doc = create_test_doc("passport_scan.pdf")
    text = """
    PASSPORT
    Country: United States of America
    Date of Birth: 15 AUG 1985
    Nationality: USA
    Gender: M
    Date of Issue: 10 JAN 2020
    Expiry Date: 09 JAN 2030
    Issuing Authority: United States Department of State
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.IDENTITY_DOCUMENT.value
    assert res.confidence_score >= 0.85


def test_12_legal_contract_agreement():
    """Test 12: Non-Disclosure Agreement / Contract -> CONTRACT."""
    doc = create_test_doc("nda_agreement.pdf")
    text = """
    NON-DISCLOSURE AGREEMENT
    This Agreement is entered into on Effective Date: January 15, 2026
    by and between the Parties:
    Whereas, Party A and Party B desire to disclose confidential information.
    Terms and Conditions:
    Governing Law and Jurisdiction: State of California.
    In Witness Whereof, the parties have executed this Agreement.
    Authorized Signatory: John Doe
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.CONTRACT.value
    assert res.confidence_score >= 0.85


def test_13_isolated_weak_keyword_does_not_falsely_classify():
    """Test 13: An isolated word like 'account' or 'balance' in general prose returns UNKNOWN."""
    doc = create_test_doc("memo.txt")
    text = "Please take into account that we need to balance our priorities this quarter."
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.UNKNOWN.value
    assert res.confidence_score <= 0.20


def test_14_short_document_with_clear_evidence():
    """Test 14: Short document with 2 strong signals is correctly classified."""
    doc = create_test_doc("short_rx.pdf")
    text = "Rx Order\nMedication: Amoxicillin 500mg\nTake one capsule daily\nRefills: 2"
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.PRESCRIPTION.value
    assert res.confidence_score >= 0.70
