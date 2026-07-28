import re
import string
from dataclasses import dataclass
from typing import Optional, Tuple


CONFIDENCE_EVALUATION_METHOD = (
    "WEIGHTED_ENGINE_TEXT_QUALITY_COVERAGE_V1"
)
PLACEHOLDER_TEXT_VALUES = {
    "todo - ocr not implemented",
}


@dataclass(frozen=True)
class OCRConfidenceEvaluation:
    """
    Detailed confidence evaluation for extracted document text.
    """

    confidence_score: float
    raw_engine_confidence: float
    text_quality_score: float
    coverage_score: float
    evaluation_method: str
    signals: Tuple[str, ...]


class OCRConfidenceEvaluator:
    """
    Evaluates OCR confidence using engine confidence, text quality,
    and extracted-text coverage.
    """

    ENGINE_WEIGHT = 0.70
    TEXT_QUALITY_WEIGHT = 0.20
    COVERAGE_WEIGHT = 0.10

    HIGH_COVERAGE_CHARS_PER_PAGE = 500
    MEDIUM_COVERAGE_CHARS_PER_PAGE = 200
    LOW_COVERAGE_CHARS_PER_PAGE = 75
    MIN_COVERAGE_CHARS_PER_PAGE = 25

    def evaluate(
        self,
        extracted_text: Optional[str],
        raw_confidence_score: Optional[float],
        page_count: int,
        extraction_method: str,
    ) -> OCRConfidenceEvaluation:
        text = (extracted_text or "").strip()
        raw_engine_confidence = self._normalize_confidence(
            raw_confidence_score,
        )

        if self._is_invalid_text(text):
            return OCRConfidenceEvaluation(
                confidence_score=0.0,
                raw_engine_confidence=raw_engine_confidence,
                text_quality_score=0.0,
                coverage_score=0.0,
                evaluation_method=CONFIDENCE_EVALUATION_METHOD,
                signals=("empty_or_placeholder_text",),
            )

        text_quality_score = self._calculate_text_quality_score(text)
        coverage_score = self._calculate_coverage_score(text, page_count)
        confidence_score = self._calculate_final_score(
            raw_engine_confidence=raw_engine_confidence,
            text_quality_score=text_quality_score,
            coverage_score=coverage_score,
        )

        return OCRConfidenceEvaluation(
            confidence_score=confidence_score,
            raw_engine_confidence=raw_engine_confidence,
            text_quality_score=text_quality_score,
            coverage_score=coverage_score,
            evaluation_method=CONFIDENCE_EVALUATION_METHOD,
            signals=self._build_signals(
                extraction_method=extraction_method,
                text_quality_score=text_quality_score,
                coverage_score=coverage_score,
            ),
        )

    def _calculate_final_score(
        self,
        raw_engine_confidence: float,
        text_quality_score: float,
        coverage_score: float,
    ) -> float:
        score = (
            raw_engine_confidence * self.ENGINE_WEIGHT
            + text_quality_score * self.TEXT_QUALITY_WEIGHT
            + coverage_score * self.COVERAGE_WEIGHT
        )
        score = self._apply_quality_caps(
            score,
            text_quality_score,
            coverage_score,
        )
        return round(self._clamp(score), 4)

    @staticmethod
    def _apply_quality_caps(
        score: float,
        text_quality_score: float,
        coverage_score: float,
    ) -> float:
        if text_quality_score < 0.30:
            return min(score, 0.45)

        if text_quality_score < 0.50:
            return min(score, 0.65)

        if coverage_score <= 0.20 and text_quality_score < 0.80:
            return min(score, 0.75)

        return score

    def _calculate_text_quality_score(self, text: str) -> float:
        characters = [character for character in text if character.strip()]
        if not characters:
            return 0.0

        valid_characters = sum(
            1
            for character in characters
            if self._is_valid_text_character(character)
        )
        valid_character_ratio = valid_characters / len(characters)
        meaningful_word_ratio = self._calculate_meaningful_word_ratio(text)
        noise_penalty = self._calculate_noise_penalty(text)

        score = (
            valid_character_ratio * 0.60
            + meaningful_word_ratio * 0.40
            - noise_penalty
        )
        return round(self._clamp(score), 4)

    def _calculate_coverage_score(
        self,
        text: str,
        page_count: int,
    ) -> float:
        normalized_page_count = max(page_count, 1)
        chars_per_page = len(text) / normalized_page_count

        if chars_per_page >= self.HIGH_COVERAGE_CHARS_PER_PAGE:
            return 1.0

        if chars_per_page >= self.MEDIUM_COVERAGE_CHARS_PER_PAGE:
            return 0.85

        if chars_per_page >= self.LOW_COVERAGE_CHARS_PER_PAGE:
            return 0.70

        if chars_per_page >= self.MIN_COVERAGE_CHARS_PER_PAGE:
            return 0.45

        return 0.20

    @staticmethod
    def _calculate_meaningful_word_ratio(text: str) -> float:
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", text)
        if not words:
            return 0.0

        meaningful_words = [
            word
            for word in words
            if 2 <= len(word) <= 35
        ]
        return len(meaningful_words) / len(words)

    @staticmethod
    def _calculate_noise_penalty(text: str) -> float:
        replacement_char_count = text.count("?") + text.count("\ufffd")
        if not text:
            return 0.0

        replacement_ratio = replacement_char_count / len(text)
        repeated_symbol_matches = re.findall(r"[^A-Za-z0-9\s]{4,}", text)
        repeated_symbol_penalty = min(
            len(repeated_symbol_matches) * 0.05,
            0.25,
        )

        return min(replacement_ratio + repeated_symbol_penalty, 0.40)

    @staticmethod
    def _is_valid_text_character(character: str) -> bool:
        if character.isalnum() or character.isspace():
            return True

        return character in string.punctuation

    @staticmethod
    def _normalize_confidence(score: Optional[float]) -> float:
        try:
            return OCRConfidenceEvaluator._clamp(float(score or 0.0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _is_invalid_text(text: str) -> bool:
        if not text:
            return True

        return text.lower().strip() in PLACEHOLDER_TEXT_VALUES

    @staticmethod
    def _build_signals(
        extraction_method: str,
        text_quality_score: float,
        coverage_score: float,
    ) -> Tuple[str, ...]:
        signals = [
            f"method={extraction_method}",
            f"text_quality={text_quality_score}",
            f"coverage={coverage_score}",
        ]
        return tuple(signals)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(value, 1.0))


ocr_confidence_evaluator = OCRConfidenceEvaluator()


