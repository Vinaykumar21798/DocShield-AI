from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class EntityAnnotation:
    entity_type: str
    entity_value: str
    start_char: int | None = None
    end_char: int | None = None
    page_number: int = 1


@dataclass
class MetricCounts:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def f1_score(self) -> float:
        denominator = self.precision + self.recall
        return 2 * self.precision * self.recall / denominator if denominator else 0.0

    @property
    def accuracy(self) -> float:
        denominator = (
            self.true_positives
            + self.false_positives
            + self.false_negatives
        )
        return self.true_positives / denominator if denominator else 0.0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 6),
            "recall": round(self.recall, 6),
            "f1_score": round(self.f1_score, 6),
            "accuracy": round(self.accuracy, 6),
        }


@dataclass
class PredictionMetrics:
    global_metrics: MetricCounts = field(default_factory=MetricCounts)
    detector_metrics: dict[str, MetricCounts] = field(default_factory=dict)
    matched_predictions: list[dict[str, Any]] = field(default_factory=list)
    false_positive_predictions: list[dict[str, Any]] = field(default_factory=list)
    false_negative_annotations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "global": self.global_metrics.to_dict(),
            "detectors": {
                detector: counts.to_dict()
                for detector, counts in sorted(self.detector_metrics.items())
            },
            "matched_predictions": self.matched_predictions,
            "false_positive_predictions": self.false_positive_predictions,
            "false_negative_annotations": self.false_negative_annotations,
        }


def evaluate_predictions(
    predictions: Iterable[Any],
    ground_truth: Iterable[Any],
    source_text: str | None = None,
    confidence_threshold: float = 0.0,
    min_overlap_ratio: float = 0.5,
) -> PredictionMetrics:
    """
    Calculates entity-extraction metrics after prediction.

    Precision, recall, F1, and extraction accuracy require ground-truth
    annotations. When annotations do not include start/end offsets, source_text
    is used to resolve entity_value occurrences before matching.
    """
    gt_entities = normalize_annotations(ground_truth, source_text)
    predicted_entities = [
        _normalize_prediction(prediction)
        for prediction in predictions
        if _get(prediction, "confidence_score", 0.0) >= confidence_threshold
    ]

    metrics = PredictionMetrics()
    matched_gt_indexes: set[int] = set()
    matched_prediction_indexes: set[int] = set()

    for prediction_index, prediction in enumerate(predicted_entities):
        best_gt_index = _best_ground_truth_match(
            prediction,
            gt_entities,
            matched_gt_indexes,
            min_overlap_ratio,
        )
        if best_gt_index is None:
            continue

        matched_prediction_indexes.add(prediction_index)
        matched_gt_indexes.add(best_gt_index)
        metrics.global_metrics.true_positives += 1

        detector = prediction.get("detector") or "Unknown"
        detector_counts = metrics.detector_metrics.setdefault(
            detector,
            MetricCounts(),
        )
        detector_counts.true_positives += 1
        metrics.matched_predictions.append(
            {
                "prediction": prediction,
                "ground_truth": asdict(gt_entities[best_gt_index]),
            }
        )

    for prediction_index, prediction in enumerate(predicted_entities):
        if prediction_index in matched_prediction_indexes:
            continue

        metrics.global_metrics.false_positives += 1
        detector = prediction.get("detector") or "Unknown"
        detector_counts = metrics.detector_metrics.setdefault(
            detector,
            MetricCounts(),
        )
        detector_counts.false_positives += 1
        metrics.false_positive_predictions.append(prediction)

    for gt_index, annotation in enumerate(gt_entities):
        if gt_index in matched_gt_indexes:
            continue

        metrics.global_metrics.false_negatives += 1
        metrics.false_negative_annotations.append(asdict(annotation))

    return metrics


def normalize_annotations(
    annotations: Iterable[Any],
    source_text: str | None = None,
) -> list[EntityAnnotation]:
    resolved: list[EntityAnnotation] = []
    used_spans: set[tuple[int, int]] = set()

    for annotation in annotations:
        entity_type = _annotation_type(annotation)
        entity_value = _annotation_value(annotation)
        start_char = _optional_int(_get(annotation, "start_char", None))
        end_char = _optional_int(_get(annotation, "end_char", None))
        page_number = int(_get(annotation, "page_number", 1) or 1)

        if start_char is None:
            start_char = _optional_int(_get(annotation, "start", None))
        if end_char is None:
            end_char = _optional_int(_get(annotation, "end", None))

        if (
            source_text is not None
            and entity_value
            and (start_char is None or end_char is None)
        ):
            located = _locate_next_span(source_text, entity_value, used_spans)
            if located is not None:
                start_char, end_char = located

        if start_char is not None and end_char is not None:
            used_spans.add((start_char, end_char))

        resolved.append(
            EntityAnnotation(
                entity_type=entity_type,
                entity_value=entity_value,
                start_char=start_char,
                end_char=end_char,
                page_number=page_number,
            )
        )

    return resolved


def _best_ground_truth_match(
    prediction: dict[str, Any],
    ground_truth: list[EntityAnnotation],
    matched_gt_indexes: set[int],
    min_overlap_ratio: float,
) -> int | None:
    best_index = None
    best_score = 0.0

    for gt_index, annotation in enumerate(ground_truth):
        if gt_index in matched_gt_indexes:
            continue
        if prediction["page_number"] != annotation.page_number:
            continue
        if not _types_match(prediction, annotation):
            continue

        score = _match_score(prediction, annotation)
        if score < min_overlap_ratio:
            continue
        if score > best_score:
            best_index = gt_index
            best_score = score

    return best_index


def _match_score(prediction: dict[str, Any], annotation: EntityAnnotation) -> float:
    if prediction["start_char"] is None or prediction["end_char"] is None:
        return 1.0 if _same_value(prediction["entity_value"], annotation.entity_value) else 0.0
    if annotation.start_char is None or annotation.end_char is None:
        return 1.0 if _same_value(prediction["entity_value"], annotation.entity_value) else 0.0

    overlap = max(
        0,
        min(prediction["end_char"], annotation.end_char)
        - max(prediction["start_char"], annotation.start_char),
    )
    gt_length = max(1, annotation.end_char - annotation.start_char)
    prediction_length = max(1, prediction["end_char"] - prediction["start_char"])
    return overlap / max(gt_length, prediction_length)


def _normalize_prediction(prediction: Any) -> dict[str, Any]:
    return {
        "entity_type": str(_get(prediction, "entity_type", "")),
        "canonical_type": str(
            _get(
                prediction,
                "canonical_type",
                _get(prediction, "entity_type", ""),
            )
        ),
        "entity_value": str(_get(prediction, "entity_value", "")),
        "start_char": _optional_int(_get(prediction, "start_char", None)),
        "end_char": _optional_int(_get(prediction, "end_char", None)),
        "page_number": int(_get(prediction, "page_number", 1) or 1),
        "confidence_score": float(_get(prediction, "confidence_score", 0.0) or 0.0),
        "detector": str(_get(prediction, "detector", "Unknown") or "Unknown"),
    }


def _types_match(prediction: dict[str, Any], annotation: EntityAnnotation) -> bool:
    expected = _normalize_type(annotation.entity_type)
    predicted = _normalize_type(prediction["entity_type"])
    canonical = _normalize_type(prediction.get("canonical_type") or "")
    return expected in {predicted, canonical}


def _same_value(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()


def _normalize_type(value: str) -> str:
    return value.strip().upper().replace(" ", "_")


def _annotation_type(annotation: Any) -> str:
    return str(_get(annotation, "entity_type", _get(annotation, "type", "")))


def _annotation_value(annotation: Any) -> str:
    return str(_get(annotation, "entity_value", _get(annotation, "value", "")))


def _locate_next_span(
    text: str,
    value: str,
    used_spans: set[tuple[int, int]],
) -> tuple[int, int] | None:
    pattern = re.escape(value).replace(r"\ ", r"\s+")
    for match in re.finditer(pattern, text):
        span = (match.start(), match.end())
        if span not in used_spans:
            return span
    return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
