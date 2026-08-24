from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from modules.detection.detectors.azure_detector import AzureOpenAIDetector
from modules.detection.detectors.gemma_detector import Gemma4E4BDetector
from modules.detection.models.detection_result import DetectionResult


PRICING_ENV_VARS = (
    "AZURE_OPENAI_INPUT_COST_PER_1M",
    "AZURE_OPENAI_CACHED_INPUT_COST_PER_1M",
    "AZURE_OPENAI_OUTPUT_COST_PER_1M",
    "GEMMA_COMPUTE_COST_PER_HOUR_USD",
)


@pytest.fixture(autouse=True)
def clear_pricing_environment(monkeypatch):
    for name in PRICING_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)


def _azure_response(prompt_tokens, completion_tokens, cached_tokens=0):
    prompt_details = SimpleNamespace(cached_tokens=cached_tokens)
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens_details=prompt_details,
    )
    return SimpleNamespace(usage=usage)


def test_azure_uses_provider_tokens_and_configured_cached_rates(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_INPUT_COST_PER_1M", "2.00")
    monkeypatch.setenv("AZURE_OPENAI_CACHED_INPUT_COST_PER_1M", "0.50")
    monkeypatch.setenv("AZURE_OPENAI_OUTPUT_COST_PER_1M", "8.00")
    detector = AzureOpenAIDetector()

    detector._record_usage(
        _azure_response(
            prompt_tokens=1000,
            completion_tokens=200,
            cached_tokens=400,
        )
    )

    assert detector.prompt_tokens == 1000
    assert detector.cached_prompt_tokens == 400
    assert detector.completion_tokens == 200
    assert detector.total_cost_usd == pytest.approx(0.003)
    assert detector.cost_basis == "azure_configured_token_rates"
    assert detector.usage_complete is True


def test_azure_reports_unknown_cost_when_pricing_is_not_configured():
    detector = AzureOpenAIDetector()

    detector._record_usage(_azure_response(125, 25))

    assert detector.prompt_tokens == 125
    assert detector.completion_tokens == 25
    assert detector.total_cost_usd is None
    assert detector.cost_basis is None


def test_azure_does_not_invent_usage_when_response_has_no_usage():
    detector = AzureOpenAIDetector()

    detector._record_usage(SimpleNamespace())

    assert detector.prompt_tokens == 0
    assert detector.completion_tokens == 0
    assert detector.total_cost_usd is None
    assert detector.usage_complete is False


def test_azure_requires_cached_rate_when_cached_tokens_are_used(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_INPUT_COST_PER_1M", "2.00")
    monkeypatch.setenv("AZURE_OPENAI_OUTPUT_COST_PER_1M", "8.00")
    detector = AzureOpenAIDetector()

    detector._record_usage(_azure_response(1000, 200, cached_tokens=400))

    assert detector.prompt_tokens == 1000
    assert detector.cached_prompt_tokens == 400
    assert detector.total_cost_usd is None


def test_azure_does_not_assume_zero_cached_tokens(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_INPUT_COST_PER_1M", "2.00")
    monkeypatch.setenv("AZURE_OPENAI_CACHED_INPUT_COST_PER_1M", "0.50")
    monkeypatch.setenv("AZURE_OPENAI_OUTPUT_COST_PER_1M", "8.00")
    detector = AzureOpenAIDetector()
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1000,
            completion_tokens=200,
            prompt_tokens_details=None,
        )
    )

    detector._record_usage(response)

    assert detector.prompt_tokens == 1000
    assert detector.cached_prompt_tokens is None
    assert detector.completion_tokens == 200
    assert detector.total_cost_usd is None


def test_gemma_uses_ollama_tokens_and_measured_compute_duration(monkeypatch):
    monkeypatch.setenv("GEMMA_COMPUTE_COST_PER_HOUR_USD", "2.00")
    detector = Gemma4E4BDetector()

    detector._record_usage(
        {
            "prompt_eval_count": 120,
            "eval_count": 30,
            "total_duration": 3_600_000_000,
        },
        elapsed_seconds=99.0,
    )

    assert detector.prompt_tokens == 120
    assert detector.completion_tokens == 30
    assert detector.llm_duration_seconds == pytest.approx(3.6)
    assert detector.total_cost_usd == pytest.approx(0.002)
    assert detector.cost_basis == "gemma_measured_compute_runtime"
    assert detector.usage_complete is True


def test_gemma_reports_tokens_but_unknown_cost_without_compute_rate():
    detector = Gemma4E4BDetector()

    detector._record_usage(
        {"prompt_eval_count": 10, "eval_count": 4},
        elapsed_seconds=1.5,
    )

    assert detector.prompt_tokens == 10
    assert detector.completion_tokens == 4
    assert detector.llm_duration_seconds == pytest.approx(1.5)
    assert detector.total_cost_usd is None


def test_gemma_validation_usage_is_included(monkeypatch):
    monkeypatch.setenv("BYPASS_LLM", "false")
    monkeypatch.setenv("GEMMA_COMPUTE_COST_PER_HOUR_USD", "1.00")
    detector = Gemma4E4BDetector()
    detector.client = MagicMock()
    detector.client.chat.return_value = {
        "message": {
            "content": (
                '{"decision":"CONFIRM","corrected_type":null,'
                '"confidence_score":0.91,"reason":"Synthetic test."}'
            )
        },
        "prompt_eval_count": 75,
        "eval_count": 15,
        "total_duration": 1_800_000_000,
    }
    candidate = DetectionResult(
        entity_type="PERSON",
        entity_value="Synthetic Candidate",
        confidence_score=0.7,
        start_char=0,
        end_char=19,
        detector="test",
    )

    validated = detector.validate_candidates(
        [candidate],
        [SimpleNamespace(text="Synthetic Candidate")],
    )

    assert len(validated) == 1
    assert detector.prompt_tokens == 75
    assert detector.completion_tokens == 15
    assert detector.llm_duration_seconds == pytest.approx(1.8)
    assert detector.total_cost_usd == pytest.approx(0.0005)


def test_gemma_does_not_fallback_to_character_estimates():
    detector = Gemma4E4BDetector()

    detector._record_usage(
        {"message": {"content": "response without usage"}},
        elapsed_seconds=1.0,
    )

    assert detector.prompt_tokens == 0
    assert detector.completion_tokens == 0
    assert detector.total_cost_usd is None
    assert detector.usage_complete is False
