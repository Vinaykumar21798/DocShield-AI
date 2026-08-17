import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath("."))
from modules.detection.service import DetectionService

logging.basicConfig(level=logging.INFO)

# Generate a realistic, complex clinical document containing:
# - MUST_HAVE entities (Patient name, MRN, SSN, DOB, Diagnoses, Medications, Account numbers)
# - NICE_TO_HAVE entities (Doctor, Hospital, Procedures, Vital signs, Insurance ID, Address)
# - DROP entities (Equipment serial number, boilerplate disclaimer, device model)
TEST_DOCUMENT = """
ST. JUDE REGIONAL MEDICAL CENTER
DEPARTMENT OF CARDIOLOGY - DISCHARGE SUMMARY

PATIENT INFORMATION:
Patient Name: Eleanor Vance
Date of Birth: 1974-08-14
MRN: MRN-9842109
SSN: 482-19-8732
Address: 742 Evergreen Terrace, Springfield, OR 97477
Contact: (541) 555-0199 | eleanor.vance@emailprovider.com
Emergency Contact: Thomas Vance (Spouse) - 541-555-0188

ADMISSION & DISCHARGE:
Admission Date: October 12, 2024
Discharge Date: October 16, 2024
Attending Physician: Dr. Marcus Brody, MD (NPI: 1982736450)
Primary Nurse: Sarah Jenkins, RN

CLINICAL COURSE & DIAGNOSIS:
Primary Diagnosis: Acute Non-ST Elevation Myocardial Infarction (NSTEMI)
Secondary Diagnoses: Essential Hypertension, Hyperlipidemia, Type 2 Diabetes Mellitus
Presenting Symptoms: Severe substernal chest pressure radiating to left arm, diaphoresis, dyspnea.

PROCEDURES PERFORMED:
1. Emergent Percutaneous Coronary Intervention (PCI) with drug-eluting stent placement in proximal LAD on 2024-10-12.
2. Transthoracic Echocardiogram showing left ventricular ejection fraction (LVEF) of 45%.

DISCHARGE MEDICATIONS:
- Aspirin 81 mg oral tablet daily
- Ticagrelor (Brilinta) 90 mg oral tablet twice daily
- Atorvastatin 80 mg oral tablet at bedtime
- Metoprolol Succinate 50 mg oral tablet once daily
- Metformin 500 mg oral tablet twice daily with meals

LABORATORY & VITAL SIGNS AT DISCHARGE:
Blood Pressure: 118/76 mmHg | Heart Rate: 68 bpm | SpO2: 98% on room air
Peak Troponin I: 4.82 ng/mL | Fasting Blood Glucose: 134 mg/dL | Serum Creatinine: 0.9 mg/dL

INSURANCE & BILLING:
Insurance Provider: Blue Cross Blue Shield of Oregon
Policy Number: BCBS-OR-8839201
Member ID: MEM-55928174
Group Number: GRP-99120
Billing Account: ACC-7729104
Direct Deposit Bank Account: 9876543210 (Routing: 123456789)

EQUIPMENT & TECHNICAL METADATA (DROP CANDIDATES):
Diagnostic ECG Machine Serial Number: SN-ECG-998822-X
Stent Delivery Catheter Lot Code: LOT-882910-B
Telemetry Monitor Asset Tag: ASSET-44910-MON

DISCLAIMER & NOTICE:
This document contains confidential health information intended only for the use of the individual or entity named above. If you are not the intended recipient, you are hereby notified that any disclosure, copying, distribution, or action taken in reliance on the contents is strictly prohibited.
"""

def main():
    service = DetectionService()
    print("\n" + "="*80)
    print("RUNNING DETECTION PIPELINE ON TEST CLINICAL DOCUMENT")
    print("="*80 + "\n")

    results = service.detect(
        TEST_DOCUMENT,
        page_number=1,
        document_type="Medical Record / Clinical Note",
    )

    print(f"\nTotal Detected Entities: {len(results)}\n")
    
    must_have_count = 0
    nice_to_have_count = 0
    drop_count = 0

    print(f"{'TYPE':<25} | {'VALUE':<32} | {'CONF':<6} | {'PRIORITY':<12} | {'DETECTOR':<10} | {'MASK'}")
    print("-" * 105)
    for r in results:
        priority = r.metadata.get("policy_priority", "UNKNOWN")
        should_mask = r.metadata.get("should_mask", True)
        if priority == "MUST_HAVE":
            must_have_count += 1
        elif priority == "NICE_TO_HAVE":
            nice_to_have_count += 1
        elif priority == "DROP":
            drop_count += 1

        val_display = (r.entity_value[:30] + "..") if len(r.entity_value) > 30 else r.entity_value
        print(f"{r.entity_type:<25} | {val_display:<32} | {r.confidence_score:<6.2f} | {priority:<12} | {r.detector:<10} | {str(should_mask)}")

    print("-" * 105)
    print(f"Summary: MUST_HAVE = {must_have_count}, NICE_TO_HAVE = {nice_to_have_count}, DROP (Passed through) = {drop_count}")
    print("="*80)

if __name__ == "__main__":
    main()
