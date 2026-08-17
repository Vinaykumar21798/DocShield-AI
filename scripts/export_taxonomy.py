"""
Exports the Excel taxonomy into modules/detection/taxonomy_data.py
with clean formatting, detector aliases, and pre-computed priority indices.
"""
import os
import pprint
import openpyxl

excel_path = "PII_PHI_Entity_Policy_Taxonomy_Corrected.xlsx"
out_path = os.path.join("modules", "detection", "taxonomy_data.py")

wb = openpyxl.load_workbook(excel_path)

# Detector-specific aliases to include directly
DETECTOR_ALIASES = {
    "PATIENT": "FULL NAME / PERSON NAME",
    "PERSON": "FULL NAME / PERSON NAME",
    "PATIENT_NAME": "FULL NAME / PERSON NAME",
    "DOCTOR": "TREATING PROVIDER NAME / NPI NUMBER",
    "PHYSICIAN": "TREATING PROVIDER NAME / NPI NUMBER",
    "NURSE": "TREATING PROVIDER NAME / NPI NUMBER",
    "HEALTHCARE_STAFF": "TREATING PROVIDER NAME / NPI NUMBER",
    "PROVIDER": "TREATING PROVIDER NAME / NPI NUMBER",
    "DISEASE": "DIAGNOSIS / MEDICAL CONDITION",
    "DIAGNOSIS": "DIAGNOSIS / MEDICAL CONDITION",
    "SYMPTOM": "DIAGNOSIS / MEDICAL CONDITION",
    "PROBLEM": "DIAGNOSIS / MEDICAL CONDITION",
    "PROCEDURE": "PROCEDURE CODE / DESCRIPTION",
    "MEDICATION": "MEDICATION / PRESCRIPTION DETAIL",
    "DOSAGE": "MEDICATION / PRESCRIPTION DETAIL",
    "ALLERGY": "ALLERGY INFORMATION",
    "VITAL_SIGN": "LAB TEST RESULT / VALUE",
    "CLINICAL_MEASUREMENT": "LAB TEST RESULT / VALUE",
    "LAB_RESULT": "LAB TEST RESULT / VALUE",
    "LAB": "LAB TEST RESULT / VALUE",
    "HOSPITAL": "COMPANY / EMPLOYER NAME",
    "CLINIC": "COMPANY / EMPLOYER NAME",
    "ORGANIZATION": "COMPANY / EMPLOYER NAME",
    "LOCATION": "STREET / MAILING ADDRESS",
    "ADDRESS": "STREET / MAILING ADDRESS",
    "ZIP_CODE": "GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)",
    "PIN_CODE": "GEOGRAPHIC SUBDIVISION SMALLER THAN STATE (ZIP)",
    "DATE_OF_BIRTH": "DATE OF BIRTH",
    "VISIT_DATE": "ADMISSION / DISCHARGE / SERVICE DATE",
    "START_DATE": "ADMISSION / DISCHARGE / SERVICE DATE",
    "DATE_TIME": "ADMISSION / DISCHARGE / SERVICE DATE",
    "DATE": "ADMISSION / DISCHARGE / SERVICE DATE",
    "SSN": "SOCIAL SECURITY NUMBER (SSN)",
    "MRN": "MEDICAL RECORD NUMBER (MRN)",
    "MEDICAL_RECORD_NUMBER": "MEDICAL RECORD NUMBER (MRN)",
    "MEMBER_ID": "HEALTH PLAN BENEFICIARY/MEMBER NUMBER",
    "GROUP_NUMBER": "GROUP / POLICY NUMBER",
    "POLICY_NUMBER": "HEALTH INSURANCE POLICY NUMBER",
    "CLAIM_NUMBER": "MEDICAL CLAIM NUMBER",
    "NPI_NUMBER": "TREATING PROVIDER NAME / NPI NUMBER",
    "NPI": "TREATING PROVIDER NAME / NPI NUMBER",
    "US_PHONE_NUMBER": "PHONE NUMBER",
    "PHONE_NUMBER": "PHONE NUMBER",
    "EMAIL": "EMAIL ADDRESS",
    "CREDIT_CARD": "PAYMENT CARD NUMBER (PAN)",
    "BANK_ACCOUNT": "BANK ACCOUNT NUMBER",
    "TAX_ID": "US TAX ID (EIN / ITIN)",
    "AADHAAR_NUMBER": "AADHAAR NUMBER (INDIA)",
    "PAN_NUMBER": "PERMANENT ACCOUNT NUMBER — INCOME TAX (INDIA)",
    "PASSPORT_NUMBER": "PASSPORT NUMBER",
    "DRIVING_LICENSE": "DRIVER'S LICENSE NUMBER",
}

# 1. Entity Canonicalization
c_ws = wb["Entity_Canonicalization"]
canonical_map = dict(DETECTOR_ALIASES)

for r in list(c_ws.iter_rows(values_only=True))[1:]:
    raw, canonical, category, aliases = r[0], r[1], r[2], r[3]
    if raw and canonical:
        canonical_map[str(raw).strip().upper()] = str(canonical).strip().upper()
    if canonical:
        canonical_map[str(canonical).strip().upper()] = str(canonical).strip().upper()
    if aliases and canonical:
        for alias in str(aliases).split(";"):
            alias = alias.strip()
            if alias:
                canonical_map[alias.upper()] = str(canonical).strip().upper()

# 2. Master Entity Policy
m_ws = wb["Master_Entity_Policy"]
doc_policies = {}
global_policy = {}
drop_entities = set()
must_have_by_doc = {}
nice_to_have_by_doc = {}
drop_by_doc = {}

for r in list(m_ws.iter_rows(values_only=True))[1:]:
    doc_type = str(r[0]).strip() if r[0] else "General"
    entity = str(r[2]).strip() if r[2] else ""
    canonical = str(r[3]).strip().upper() if r[3] else entity.upper()
    category = str(r[4]).strip() if r[4] else ""
    data_type = str(r[5]).strip() if r[5] else ""
    priority = str(r[6]).strip() if r[6] else "NICE_TO_HAVE"
    risk = str(r[7]).strip() if r[7] else "MEDIUM"
    threat = str(r[8]).strip() if r[8] else ""
    regulation = str(r[9]).strip() if r[9] else ""

    if not canonical:
        continue

    if doc_type not in doc_policies:
        doc_policies[doc_type] = {}
        must_have_by_doc[doc_type] = []
        nice_to_have_by_doc[doc_type] = []
        drop_by_doc[doc_type] = []

    doc_policies[doc_type][canonical] = {
        "priority": priority,
        "risk_level": risk,
        "category": category,
        "data_type": data_type,
        "threat": threat,
        "regulation": regulation,
    }

    if priority == "MUST_HAVE":
        must_have_by_doc[doc_type].append(canonical)
    elif priority == "NICE_TO_HAVE":
        nice_to_have_by_doc[doc_type].append(canonical)
    elif priority == "DROP":
        drop_by_doc[doc_type].append(canonical)
        drop_entities.add(canonical)

    if canonical not in global_policy or priority == "MUST_HAVE":
        global_policy[canonical] = {
            "priority": priority,
            "risk_level": risk,
            "category": category,
            "data_type": data_type,
        }

# 3. Drop_Entities sheet
d_ws = wb["Drop_Entities"]
for r in list(d_ws.iter_rows(values_only=True))[1:]:
    doc_type = str(r[0]).strip() if r[0] else ""
    canonical = str(r[2]).strip().upper() if r[2] else (str(r[1]).strip().upper() if r[1] else "")
    if canonical:
        drop_entities.add(canonical)
        if doc_type and doc_type in drop_by_doc:
            if canonical not in drop_by_doc[doc_type]:
                drop_by_doc[doc_type].append(canonical)

# Format outputs
code = f'''"""
Auto-generated from PII_PHI_Entity_Policy_Taxonomy_Corrected.xlsx
Defines document-type specific entity policies (MUST_HAVE, NICE_TO_HAVE, DROP),
canonical entity mapping, risk levels, and drop rules.
"""

CANONICAL_ENTITY_MAPPING = {pprint.pformat(canonical_map, width=120, compact=True)}

DOCUMENT_POLICIES = {pprint.pformat(doc_policies, width=120, compact=False)}

GLOBAL_POLICY = {pprint.pformat(global_policy, width=120, compact=False)}

DROP_ENTITIES = {pprint.pformat(sorted(list(drop_entities)), width=120, compact=True)}

DOCUMENT_TYPES = {pprint.pformat(sorted(list(doc_policies.keys())), width=120, compact=True)}
'''

with open(out_path, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Exported taxonomy data successfully to {out_path}")
