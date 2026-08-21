import time
import pytest
from database.models import Document
from modules.classification.service import (
    DocumentClassificationService,
    DocumentType,
    document_classification_service,
)


def create_test_doc(filename="test_unseen.pdf", file_type="pdf"):
    doc = Document()
    doc.filename = filename
    doc.stored_filename = filename
    doc.file_type = file_type
    return doc


# =========================================================================
# 1. UNSEEN BANK STATEMENTS (UK, Euro, Australian, Passbook)
# =========================================================================

def test_unseen_bank_1_uk_barclays_current_account():
    """Unseen UK banking format: Sort code, Account Number, Statement of Fees, Money in/out."""
    doc = create_test_doc("barclays_current_account.pdf")
    text = """
    Barclays Bank UK PLC
    Statement of Account
    Sort Code: 20-04-15
    Account Number: 88219401
    Account Holder: Oliver Twist
    Branch: High Street Canary Wharf
    Statement Period: 01 Jan 2026 to 31 Jan 2026
    Opening Balance: £2,450.00
    Closing Balance: £3,120.00
    Transactions:
    12 Jan | Direct Debit - Council Tax | £150.00 | Debit
    15 Jan | Faster Payment / Transfer | £820.00 | Credit
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.BANK_STATEMENT.value
    assert res.confidence_score >= 0.85
    assert "banking_identity" in res.matched_groups
    assert "banking_structure" in res.matched_groups


def test_unseen_bank_2_euro_deutsche_statement():
    """Unseen Euro format: IBAN, Statement of Account, Value Date, Debit/Credit."""
    doc = create_test_doc("deutsche_bank_auszug.pdf")
    text = """
    Deutsche Bank Frankfurt
    Account Statement / Statement of Account
    Account Holder: Hans Gruber
    Account No: 99482019
    Value Date: 2026-02-01
    Opening Balance: EUR 14,200.00
    Closing Balance: EUR 12,850.00
    Withdrawals: EUR 1,350.00
    Deposits: EUR 0.00
    Txn Date: 2026-01-28 | Wire Transfer / SEPA | Debit
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.BANK_STATEMENT.value
    assert res.confidence_score >= 0.85


def test_unseen_bank_3_australian_savings_passbook():
    """Unseen Australian Passbook: BSB, Acct No, Available Balance, Deposits."""
    doc = create_test_doc("commbank_passbook.pdf")
    text = """
    Commonwealth Bank of Australia
    Passbook Account Summary
    Acct No: 1029 3847 56
    Branch: Sydney CBD
    Available Balance: $8,940.50
    Ledger Balance: $8,940.50
    Deposits: $1,200.00
    Withdrawal: $450.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.BANK_STATEMENT.value
    assert res.confidence_score >= 0.80


# =========================================================================
# 2. UNSEEN MEDICAL RECORDS (Specialist Consultation, Oncology Progress)
# =========================================================================

def test_unseen_medical_1_cardiology_consult():
    """Unseen Cardiology Consultation: History & Physical, Attending Physician, Diagnosis."""
    doc = create_test_doc("cardio_consult.pdf")
    text = """
    METROPOLITAN HEART INSTITUTE
    HISTORY AND PHYSICAL EXAMINATION
    Patient Name: Gregory House
    MRN: CARD-99102
    DOB: 11/06/1959
    Attending Physician: Dr. Lisa Cuddy, MD
    Chief Complaint: Exertional chest tightness
    History of Present Illness: Symptoms onset 3 weeks ago with exertion.
    Diagnosis: Coronary artery atherosclerotic disease
    Allergies: Morphine, Codeine
    Vital Signs: BP 145/92 mmHg, Pulse 76 bpm
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.MEDICAL_RECORD.value
    assert res.confidence_score >= 0.90


def test_unseen_medical_2_oncology_progress_note():
    """Unseen Oncology Progress Note: Progress note, Clinical impression, Hospital."""
    doc = create_test_doc("oncology_progress.pdf")
    text = """
    MEMORIAL CANCER CENTER
    PROGRESS NOTE / CHART NOTE
    Patient: Walter White
    Medical Record Number: ONC-44210
    Encounter #: ENC-882190
    Attending: Dr. Aris Thorne
    Hospital: Memorial Regional Hospital
    Clinical Impression: Non-small cell lung carcinoma, stable on chemo.
    Symptoms: Mild fatigue, no hemoptysis.
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.MEDICAL_RECORD.value
    assert res.confidence_score >= 0.90


# =========================================================================
# 3. UNSEEN LAB REPORTS (Microbiology, Pathology Panel)
# =========================================================================

def test_unseen_lab_1_microbiology_culture():
    """Unseen Lab report: Diagnostic report, specimen type, test result, reference range."""
    doc = create_test_doc("microbiology_panel.pdf")
    text = """
    BIO-REFERENCE DIAGNOSTIC REPORT
    Laboratory: BioReference Health Labs
    Specimen Type: Clean Catch Urine
    Collection Date: 02/10/2026
    Pathology Report / Test Result:
    - Urine Protein: Negative | Reference Range: Negative
    - Microscopic RBC: 0-2 / HPF | Normal Range: 0-3
    - Urine Culture: No growth at 48 hours
    Pathologist: Dr. Helena Shaw, MD
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.LAB_REPORT.value
    assert res.confidence_score >= 0.85


def test_unseen_lab_2_blood_pathology():
    """Unseen Pathology panel: Analyte, Reference range, Flag, Specimen."""
    doc = create_test_doc("pathology_summary.pdf")
    text = """
    CLINICAL PATHOLOGY REPORT
    Specimen: Whole Blood EDTA
    Collected: 01/22/2026
    Test Result:
    - Serum Creatinine: 1.8 mg/dL | Normal Range: 0.7 - 1.3 | FLAG: High
    - Blood Urea Nitrogen: 28 mg/dL | Reference Range: 8 - 20 | FLAG: Abnormal
    Biological Reference: Adult Male
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.LAB_REPORT.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 4. UNSEEN PRESCRIPTIONS (Hospital E-Rx, Compounded Rx)
# =========================================================================

def test_unseen_prescription_1_electronic_discharge_rx():
    """Unseen E-Prescription: Rx #, Prescriber, DEA #, Dispense, Sig, Refill."""
    doc = create_test_doc("discharge_rx.pdf")
    text = """
    PRESCRIPTION ORDER
    Rx #: 9920194
    Prescriber: Dr. Meredith Grey, MD
    DEA #: AG4481023
    Pharmacy: Seattle Community Pharmacy
    Medication: Atorvastatin 40mg
    Sig: Take 1 tablet by mouth daily at bedtime
    Dispense: 90 Tablets
    Refills: 3
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.PRESCRIPTION.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 5. UNSEEN INSURANCE DOCUMENTS (Auto Fleet Policy, Claim Schedule)
# =========================================================================

def test_unseen_insurance_1_commercial_policy_binder():
    """Unseen Insurance Policy: Policy number, Insured, Coverage, Deductible, Premium."""
    doc = create_test_doc("commercial_auto_policy.pdf")
    text = """
    COMMERCIAL INSURANCE POLICY SCHEDULE
    Policy Number: PAC-8839201
    Named Insured: Apex Global Logistics LLC
    Coverage: Commercial Auto Comprehensive & Collision
    Deductible: $1,000.00
    Annual Premium: $14,500.00
    Effective Date: 01/03/2026
    Expiration Date: 01/03/2027
    Plan Type: Commercial Fleet
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.INSURANCE.value
    assert res.confidence_score >= 0.85


def test_unseen_insurance_2_medical_benefits_claim():
    """Unseen Health Claim: Member ID, Group #, Claim #, Deductible, Copay, Coinsurance."""
    doc = create_test_doc("claim_adjudication.pdf")
    text = """
    EXPLANATION OF BENEFITS / INSURANCE CLAIM
    Member ID: UHC-9920138
    Group #: GRP-44291
    Subscriber ID: SUB-10293
    Claim Number: CLM-2026-88192
    Insured: Sarah Connor
    Coverage: Major Medical Preferred Care
    Deductible: $500.00
    Copay: $35.00
    Coinsurance: 10%
    Benefits Paid: $3,200.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.INSURANCE.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 6. UNSEEN INVOICES (Freight Export, SaaS Billing)
# =========================================================================

def test_unseen_invoice_1_export_freight():
    """Unseen Commercial Export Invoice: Commercial Invoice, GSTIN, Bill To, Amount Due."""
    doc = create_test_doc("freight_export.pdf")
    text = """
    COMMERCIAL INVOICE
    Invoice Number: EXP-2026-904
    GSTIN: 27AAACN8829K1ZV
    Bill To: Tokyo Imports Co.
    Ship To: Yokohama Harbor Terminal
    Payment Terms: Net 45 Days
    Due Date: 20/03/2026
    Description: Precision Microturbines
    Qty: 50 | Unit Price: $900.00 | Line Total: $45,000.00
    Subtotal: $45,000.00
    Tax Amount: $8,100.00
    Amount Due: $53,100.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.INVOICE.value
    assert res.confidence_score >= 0.85


def test_unseen_invoice_2_saas_subscription():
    """Unseen SaaS Cloud Invoice: Tax Invoice, Billed To, Subtotal, Amount Due."""
    doc = create_test_doc("saas_bill.pdf")
    text = """
    TAX INVOICE
    Invoice #: SAAS-2026-118
    Billed To: CyberDyne Systems
    Payment Terms: Due Upon Receipt
    Subtotal: $4,500.00
    Tax Amount: $810.00
    Balance Due: $5,310.00
    Amount Due: $5,310.00
    Line Items: Cloud GPU Cluster Compute, Quantity: 10, Rate: $450.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.INVOICE.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 7. UNSEEN RECEIPTS (Gas Station POS, Dining Bill)
# =========================================================================

def test_unseen_receipt_1_gas_station_pos():
    """Unseen Fuel Receipt: Cash receipt, Store #, Terminal #, Cash Tendered, Change Due."""
    doc = create_test_doc("gas_receipt.pdf")
    text = """
    CASH RECEIPT
    Speedway Gas & Convenience
    Store #5512
    Terminal #: T-02
    Register #: 04
    Cashier: Dave B.
    Items: Unleaded Fuel (12.4 Gal): $42.50
    Cash Tendered: $50.00
    Change Due: $7.50
    Payment Method: Cash Tender
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.RECEIPT.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 8. UNSEEN CONTRACTS (Master Lease, Executive Employment)
# =========================================================================

def test_unseen_contract_1_property_lease():
    """Unseen Commercial Lease: Lease agreement, Parties, Whereas, Terms and Conditions."""
    doc = create_test_doc("property_lease.pdf")
    text = """
    COMMERCIAL PROPERTY LEASE AGREEMENT
    This Agreement entered into on Effective Date: March 1, 2026
    Between the Parties:
    Lessor: Horizon Real Estate Trust
    Lessee: Quantum Innovations Inc
    Whereas, Lessor owns commercial property.
    Terms and Conditions of Lease:
    Governing Law: State of Washington.
    In Witness Whereof, the parties have executed this Agreement.
    Authorized Signatory: Richard Hendricks
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.CONTRACT.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 9. UNSEEN IDENTITY DOCUMENTS (UK Driving Licence, India Aadhaar)
# =========================================================================

def test_unseen_identity_1_uk_driving_licence():
    """Unseen UK Driving Licence: Driving licence, DOB, Date of Birth, Expiry date, Issuing Authority."""
    doc = create_test_doc("uk_licence.pdf")
    text = """
    GREAT BRITAIN DRIVING LICENCE
    Driving Licence Number: CONNO881029S99
    Date of Birth: 29.10.1988
    Nationality: British
    Date of Issue: 12.04.2019
    Expiry Date: 11.04.2029
    Issuing Authority: DVLA Swansea
    Gender: F
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.IDENTITY_DOCUMENT.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 10. UNSEEN TAX FORMS (US Form 1040, India ITR-V)
# =========================================================================

def test_unseen_tax_1_us_1040_individual_return():
    """Unseen IRS Form 1040: Form 1040, Income tax return, Tax year, Filing status, Taxpayer."""
    doc = create_test_doc("form_1040.pdf")
    text = """
    DEPARTMENT OF THE TREASURY - INTERNAL REVENUE SERVICE
    FORM 1040 Individual Income Tax Return
    Tax Year: 2025
    Filing Status: Single
    Taxpayer: Tony Stark
    Wages, Salaries, Tips: $250,000.00
    Federal Income Tax Withheld: $48,000.00
    State Income Tax: $12,500.00
    Schedule C Business Profit: $85,000.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.TAX_FORM.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 11. ADVERSARIAL CROSS-TYPE TESTS
# =========================================================================

def test_adversarial_invoice_with_hospital_words():
    """Adversarial Invoice: Contains 'Hospital' & 'Patient' words in line items, but is an INVOICE."""
    doc = create_test_doc("hospital_vendor_bill.pdf")
    text = """
    COMMERCIAL INVOICE
    Invoice #: MED-INV-2026-88
    Bill To: St. Jude Children's Hospital
    Ship To: St. Jude Central Supply
    Amount Due: $18,400.00
    Subtotal: $16,000.00
    Due Date: 28/02/2026
    Line Items:
    - Patient Monitoring ECG Leads, Qty: 200, Unit Price: $80.00, Line Total: $16,000.00
    Tax Amount: $2,400.00
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.INVOICE.value
    assert res.confidence_score >= 0.80


def test_adversarial_medical_record_with_insurance_header():
    """Adversarial Medical Record: Mentions policy number in passing, but primary structure is clinical."""
    doc = create_test_doc("clinical_with_insurance.pdf")
    text = """
    DISCHARGE SUMMARY
    Patient Name: Bruce Wayne
    MRN: MR-007192
    Attending Physician: Dr. Lucius Fox, MD
    Hospital: Gotham General Hospital
    Chief Complaint: Traumatic rib contusion
    Diagnosis: Multiple costal fractures, closed
    History of Present Illness: Blunt trauma during night shift.
    Allergies: None
    Insurance Policy Reference: POL-991823 (for billing records only)
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.MEDICAL_RECORD.value
    assert res.confidence_score >= 0.85


# =========================================================================
# 12. WEAK SIGNAL / GENERIC PROSE ISOLATION
# =========================================================================

def test_weak_generic_prose_returns_unknown():
    """Generic corporate memo containing isolated words 'policy', 'agreement', 'account' returns UNKNOWN."""
    doc = create_test_doc("corporate_memo.txt")
    text = """
    Internal Memo:
    We had a fruitful discussion regarding our company policy on remote work.
    We reached a general agreement on the timeline.
    Please ensure your team takes into account the quarterly budget constraints.
    """
    res = document_classification_service.classify(doc, text)
    assert res.document_type == DocumentType.UNKNOWN.value
    assert res.confidence_score <= 0.20


# =========================================================================
# 13. HEAVILY CORRUPTED OCR GENERALIZATION
# =========================================================================

def test_ocr_generalization_bank_and_medical():
    """Heavily corrupted OCR text correctly classifies."""
    doc_bank = create_test_doc("ocr_bank.pdf")
    text_bank = "Acc0unt Staternent ... IFSC C0de: CIUB0001 ... A/C No: 50010101 ... Cl0sing Balance: 15,000"
    res_bank = document_classification_service.classify(doc_bank, text_bank)
    assert res_bank.document_type == DocumentType.BANK_STATEMENT.value

    doc_med = create_test_doc("ocr_med.pdf")
    text_med = "Med1cal Rec0rd ... Pat1ent: Bruce ... D1agnos1s: Asthrna ... Phys1c1an: Dr. Clark ... H0sp1tal: City Hospital"
    res_med = document_classification_service.classify(doc_med, text_med)
    assert res_med.document_type == DocumentType.MEDICAL_RECORD.value


# =========================================================================
# 14. PERFORMANCE & LATENCY MEASUREMENT
# =========================================================================

def test_classification_latency():
    """Measures classification execution speed across multiple unseen documents."""
    doc = create_test_doc("speed_test.pdf")
    text = "TAX INVOICE\nInvoice Number: INV-001\nBill To: Client Inc\nAmount Due: $500.00\nSubtotal: $450.00\nDue Date: 01/01/2026\nQuantity: 5\nUnit Price: $90.00"
    
    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        _ = document_classification_service.classify(doc, text)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    avg_ms = sum(latencies) / len(latencies)
    p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]
    assert avg_ms < 5.0, f"Average latency too high: {avg_ms:.3f}ms"
    assert p95_ms < 10.0, f"P95 latency too high: {p95_ms:.3f}ms"

