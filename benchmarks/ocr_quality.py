import numpy as np
from typing import List, Tuple, Dict

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def calculate_cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate"""
    if not reference:
        return 1.0 if hypothesis else 0.0
    dist = levenshtein_distance(reference, hypothesis)
    return dist / len(reference)

def calculate_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate"""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 1.0 if hyp_words else 0.0
    dist = levenshtein_distance(" ".join(ref_words), " ".join(hyp_words))
    # Simplified WER: distance between joined strings / length of ref words
    # A better WER would be distance between word lists
    return dist / len(ref_words)

def calculate_metrics(ground_truth: List[str], extracted: List[str]) -> Dict[str, float]:
    """
    Calculates PII/PHI metrics.
    Expects ground_truth and extracted to be lists of detected entity values.
    """
    gt_set = set(ground_truth)
    ex_set = set(extracted)
    
    tp = len(gt_set.intersection(ex_set))
    fp = len(ex_set - gt_set)
    fn = len(gt_set - ex_set)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }
