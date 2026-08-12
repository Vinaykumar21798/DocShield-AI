import pytest

from modules.detection.metrics import evaluate_predictions, normalize_annotations
from modules.detection.models.detection_result import DetectionResult


def _prediction(
    entity_type,
    value,
    start,
    end,
    confidence=0.90,
    detector="Regex",
    canonical_type=None,
):
    return DetectionResult(
        entity_type=entity_type,
        entity_value=value,
        confidence_score=confidence,
        start_char=start,
        end_char=end,
        page_number=1,
        detector=detector,
        canonical_type=canonical_type or entity_type,
    )


def test_prediction_metrics_calculates_precision_recall_f1_and_accuracy():
    predictions = [
        _prediction("EMAIL", "jane@example.com", 7, 23, detector="Regex"),
        _prediction("PHONE_NUMBER", "555-1111", 31, 39, detector="Presidio"),
    ]
    ground_truth = [
        {"type": "EMAIL", "value": "jane@example.com", "start": 7, "end": 23},
        {"type": "PATIENT", "value": "Jane Patient", "start": 48, "end": 60},
    ]

    metrics = evaluate_predictions(predictions, ground_truth).to_dict()

    assert metrics["global"]["true_positives"] == 1
    assert metrics["global"]["false_positives"] == 1
    assert metrics["global"]["false_negatives"] == 1
    assert metrics["global"]["precision"] == pytest.approx(0.5)
    assert metrics["global"]["recall"] == pytest.approx(0.5)
    assert metrics["global"]["f1_score"] == pytest.approx(0.5)
    assert metrics["global"]["accuracy"] == pytest.approx(1 / 3)
    assert metrics["detectors"]["Regex"]["true_positives"] == 1
    assert metrics["detectors"]["Presidio"]["false_positives"] == 1


def test_prediction_metrics_resolves_ground_truth_values_from_source_text():
    text = "Patient: Alex Kim\nEmergency Contact: Alex Kim"
    first_start = text.index("Alex Kim")
    second_start = text.index("Alex Kim", first_start + 1)
    predictions = [
        _prediction("PATIENT", "Alex Kim", first_start, first_start + 8),
        _prediction("PERSON", "Alex Kim", second_start, second_start + 8),
    ]
    ground_truth = [
        {"type": "PATIENT", "value": "Alex Kim"},
        {"type": "PERSON", "value": "Alex Kim"},
    ]

    annotations = normalize_annotations(ground_truth, source_text=text)
    metrics = evaluate_predictions(predictions, ground_truth, source_text=text)

    assert [(item.start_char, item.end_char) for item in annotations] == [
        (first_start, first_start + 8),
        (second_start, second_start + 8),
    ]
    assert metrics.global_metrics.true_positives == 2
    assert metrics.global_metrics.false_positives == 0
    assert metrics.global_metrics.false_negatives == 0
    assert metrics.global_metrics.f1_score == pytest.approx(1.0)


def test_prediction_metrics_applies_confidence_threshold():
    predictions = [
        _prediction("EMAIL", "jane@example.com", 7, 23, confidence=0.79),
    ]
    ground_truth = [
        {"type": "EMAIL", "value": "jane@example.com", "start": 7, "end": 23},
    ]

    metrics = evaluate_predictions(
        predictions,
        ground_truth,
        confidence_threshold=0.80,
    )

    assert metrics.global_metrics.true_positives == 0
    assert metrics.global_metrics.false_positives == 0
    assert metrics.global_metrics.false_negatives == 1


def test_prediction_metrics_matches_canonical_type():
    prediction = _prediction(
        "DATE_TIME",
        "2026-08-10",
        5,
        15,
        canonical_type="DATE_OF_BIRTH",
    )
    ground_truth = [
        {"type": "DATE_OF_BIRTH", "value": "2026-08-10", "start": 5, "end": 15},
    ]

    metrics = evaluate_predictions([prediction], ground_truth)

    assert metrics.global_metrics.true_positives == 1
    assert metrics.global_metrics.precision == pytest.approx(1.0)
