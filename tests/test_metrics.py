from modules.detection.service import DetectionService
import re

# Benchmark dataset with annotated ground truth
BENCHMARK_DATA = [
    {
        "domain": "healthcare",
        "text": """Lakeside Diagnostic Laboratory
Laboratory Report - CONFIDENTIAL (Sample / Synthetic Data)
Patient Name:\tFatima Al-Sayed
Date of Birth:\t2001-09-08
Social Security No.:\t601-92-5546
Phone:\t(469) 555-0184
Address:\t230 Cedar Lane, Dallas, TX 75201
Insurance Provider:\tLonestar Health Partners
Insurance ID:\tLHP-30284719
Medical Record No.:\tMRN-556511
Ordering Physician:\tDr. Michael Chen
Collection Date:\t2026-04-09
Test Results
Clinical Impression: Findings consistent with mild persistent asthma.""",
        "annotations": [
            {"value": "Fatima Al-Sayed", "type": "PERSON"},
            {"value": "2001-09-08", "type": "DATE_OF_BIRTH"},
            {"value": "601-92-5546", "type": "SSN"},
            {"value": "(469) 555-0184", "type": "US_PHONE_NUMBER"},
            {"value": "230 Cedar Lane, Dallas, TX 75201", "type": "ADDRESS"},
            {"value": "Lonestar Health Partners", "type": "ORGANIZATION"},
            {"value": "LHP-30284719", "type": "INSURANCE_ID"},
            {"value": "MRN-556511", "type": "MRN"},
            {"value": "Dr. Michael Chen", "type": "DOCTOR"},
            {"value": "2026-04-09", "type": "DATE_TIME"},
            {"value": "asthma", "type": "DISEASE"}
        ]
    },
    {
        "domain": "healthcare/financial",
        "text": """Explanation of Benefits (EOB)

Patient Name: Lonnie Taylor
DOB: 2001-08-10
SSN: 347-08-2950
Insurance ID: naV-77733127
Visit Date: 2024-08-28
Provider: Harrison-Edwards
Procedure Code: CPT99213
Diagnosis: Back Pain""",
        "annotations": [
            {"value": "Lonnie Taylor", "type": "PERSON"},
            {"value": "2001-08-10", "type": "DATE_OF_BIRTH"},
            {"value": "347-08-2950", "type": "SSN"},
            {"value": "naV-77733127", "type": "INSURANCE_ID"},
            {"value": "2024-08-28", "type": "DATE_TIME"},
            {"value": "Harrison-Edwards", "type": "ORGANIZATION"},
            {"value": "CPT99213", "type": "CPT_CODE"}
        ]
    },
    {
        "domain": "corporate",
        "text": """Employment Verification

This letter is to verify that Rebecca Norris DVM is currently employed with Odonnell Inc in the role of Journalist, broadcasting.

Details:
- Employee ID: EMP3896
- SSN: 400-04-2603
- DOB: 1992-03-19
- Start Date: 2020-10-24
- Salary: $133392
- Address: USCGC Miller, FPO AE 99567""",
        "annotations": [
            {"value": "Rebecca Norris", "type": "PERSON"},
            {"value": "Odonnell Inc", "type": "ORGANIZATION"},
            {"value": "400-04-2603", "type": "SSN"},
            {"value": "1992-03-19", "type": "DATE_OF_BIRTH"},
            {"value": "2020-10-24", "type": "DATE_TIME"},
            {"value": "USCGC Miller", "type": "LOCATION"},
            {"value": "99567", "type": "ZIP_CODE"}
        ]
    },
    {
        "domain": "financial",
        "text": """Invoice no: 12847181
Date of issue:	03/03/2012

Seller:\tClient:
Fitzpatrick and Sons\tDuncan PLC
00480 Cook Cove\tUnit 8799 Box 0703
Spencerport, UT 12036\tDPO AP 81970
Tax Id: 998-99-5253\tTax Id: 911-82-7132
IBAN: GB92PBPQ73499358975916""",
        "annotations": [
            {"value": "12036", "type": "ZIP_CODE"},
            {"value": "81970", "type": "ZIP_CODE"},
            {"value": "998-99-5253", "type": "SSN"},
            {"value": "911-82-7132", "type": "SSN"},
            {"value": "GB92PBPQ73499358975916", "type": "BANK_ACCOUNT_NUMBER"}
        ]
    }
]

def locate_spans(text, annotations):
    """Find character offsets of annotations in the raw text."""
    resolved = []
    for ann in annotations:
        val = ann["value"]
        matches = list(re.finditer(re.escape(val), text))
        if matches:
            # Match the first occurrence in the text block
            match = matches[0]
            resolved.append({
                "value": val,
                "type": ann["type"],
                "start": match.start(),
                "end": match.end()
            })
    return resolved

def evaluate_pipeline(threshold=0.0):
    service = DetectionService()
    
    tp_global = 0
    fp_global = 0
    fn_global = 0
    
    detector_metrics = {}
    
    for case in BENCHMARK_DATA:
        text = case["text"]
        gt_entities = locate_spans(text, case["annotations"])
        detected_raw = service.detect(text)
        
        # Filter detections by the confidence threshold
        detected = [d for d in detected_raw if d.confidence_score >= threshold]
        
        matched_gt = set()
        matched_dt = set()
        
        # 1. Match True Positives (TPs)
        for i, dt in enumerate(detected):
            for j, gt in enumerate(gt_entities):
                if j in matched_gt:
                    continue
                    
                # Evaluate boundary overlap and type compatibility
                overlap = max(0, min(dt.end_char, gt["end"]) - max(dt.start_char, gt["start"]))
                type_match = (dt.entity_type == gt["type"] or dt.canonical_type == gt["type"])
                
                if overlap > 0 and type_match:
                    matched_gt.add(j)
                    matched_dt.add(i)
                    tp_global += 1
                    
                    # Update detector-specific TP metric
                    det_name = dt.detector
                    if det_name not in detector_metrics:
                        detector_metrics[det_name] = {"tp": 0, "fp": 0, "fn": 0}
                    detector_metrics[det_name]["tp"] += 1
                    break
        
        # 2. Count False Positives (FPs)
        for i, dt in enumerate(detected):
            if i not in matched_dt:
                fp_global += 1
                det_name = dt.detector
                if det_name not in detector_metrics:
                    detector_metrics[det_name] = {"tp": 0, "fp": 0, "fn": 0}
                detector_metrics[det_name]["fp"] += 1
                
        # 3. Count False Negatives (FNs)
        for j, gt in enumerate(gt_entities):
            if j not in matched_gt:
                fn_global += 1
                # If a GT was missed, charge it to the pipeline globally
                
    # Calculate global stats
    precision = tp_global / (tp_global + fp_global) if (tp_global + fp_global) > 0 else 0.0
    recall = tp_global / (tp_global + fn_global) if (tp_global + fn_global) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = tp_global / (tp_global + fp_global + fn_global) if (tp_global + fp_global + fn_global) > 0 else 0.0
    
    return {
        "global": {"precision": precision, "recall": recall, "f1": f1, "accuracy": accuracy, "tp": tp_global, "fp": fp_global, "fn": fn_global},
        "detectors": detector_metrics
    }

if __name__ == "__main__":
    print("=" * 60)
    print("      PROGRESSIVE PIPELINE METRICS EVALUATOR")
    print("=" * 60)
    
    print("\nRunning Threshold Testing (from 0.0 to 0.9)...")
    print("-" * 75)
    print(f"{'Threshold':<10} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Accuracy':<10} | {'TP/FP/FN'}")
    print("-" * 75)
    
    best_f1 = 0.0
    best_threshold = 0.0
    
    for th in [0.0, 0.5, 0.6, 0.7, 0.8, 0.9]:
        res = evaluate_pipeline(th)
        g = res["global"]
        print(f"{th:<10.1f} | {g['precision']:<10.2%} | {g['recall']:<10.2%} | {g['f1']:<10.2%} | {g['accuracy']:<10.2%} | {g['tp']}/{g['fp']}/{g['fn']}")
        
        if g["f1"] > best_f1:
            best_f1 = g["f1"]
            best_threshold = th
            
    print("-" * 75)
    print(f"Optimal Confidence Threshold: {best_threshold:.1f} (Best F1: {best_f1:.2%})")
    
    print("\n\n" + "=" * 60)
    print(f"      DETECTOR PROFILE (At Threshold {best_threshold:.1f})")
    print("=" * 60)
    
    metrics = evaluate_pipeline(best_threshold)
    print(f"{'Detector':<15} | {'True Positives':<15} | {'False Positives':<15} | {'Precision':<10}")
    print("-" * 60)
    for det, met in metrics["detectors"].items():
        det_prec = met["tp"] / (met["tp"] + met["fp"]) if (met["tp"] + met["fp"]) > 0 else 0.0
        print(f"{det:<15} | {met['tp']:<15} | {met['fp']:<15} | {det_prec:<10.2%}")
    print("-" * 60)
