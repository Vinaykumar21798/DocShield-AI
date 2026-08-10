import os
from unittest.mock import MagicMock
import pytest
from modules.detection.detectors.qwen_detector import Qwen3BDetector


def test_qwen_detector_should_run_bypass_llm(monkeypatch):
    detector = Qwen3BDetector()
    detector.client = MagicMock()

    # Case 1: BYPASS_LLM is set to "True" (capitalized)
    monkeypatch.setenv("BYPASS_LLM", "True")
    assert detector.should_run("Sample text", None) is False

    # Case 2: BYPASS_LLM is set to "true" (lowercase)
    monkeypatch.setenv("BYPASS_LLM", "true")
    assert detector.should_run("Sample text", None) is False

    # Case 3: BYPASS_LLM is set to "1"
    monkeypatch.setenv("BYPASS_LLM", "1")
    assert detector.should_run("Sample text", None) is False

    # Case 4: BYPASS_LLM is set to "false"
    monkeypatch.setenv("BYPASS_LLM", "false")
    assert detector.should_run("Sample text", None) is True

    # Case 5: BYPASS_LLM is unset / empty
    monkeypatch.delenv("BYPASS_LLM", raising=False)
    assert detector.should_run("Sample text", None) is True


def test_qwen_detector_empty_response_handling():
    detector = Qwen3BDetector()
    detector.client = MagicMock()

    # Mock an empty response content
    mock_message = MagicMock()
    mock_message.content = ""
    mock_response = MagicMock()
    mock_response.message = mock_message
    detector.client.chat.return_value = mock_response

    # Verify detect() returns empty list rather than raising
    results = detector.detect("Sample text")
    assert results == []


def test_qwen_detector_invalid_json_handling():
    detector = Qwen3BDetector()
    detector.client = MagicMock()

    # Mock invalid/truncated JSON response
    mock_message = MagicMock()
    mock_message.content = "{invalid json"
    mock_response = MagicMock()
    mock_response.message = mock_message
    detector.client.chat.return_value = mock_response

    # Verify detect() handles parsing failure gracefully and returns []
    results = detector.detect("Sample text")
    assert results == []

def test_qwen_detector_skips_blank_entity_values():
    detector = Qwen3BDetector()
    detector.client = MagicMock()

    mock_message = MagicMock()
    mock_message.content = (
        '{"results":[{"entity_type":"PERSON","entity_value":"",'
        '"confidence_score":0.9,"start_char":0,"end_char":0}]}'
    )
    mock_response = MagicMock()
    mock_response.message = mock_message
    detector.client.chat.return_value = mock_response

    results = detector.detect("Name:")
    assert results == []

