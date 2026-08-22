import os
import json
from unittest.mock import MagicMock
import pytest
from modules.detection.detectors.gemma_detector import Gemma4E4BDetector, GemmaDetector
from modules.detection.models.detection_result import DetectionResult


def test_gemma_detector_should_run_bypass_llm(monkeypatch):
    detector = Gemma4E4BDetector()
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


def test_gemma_detector_empty_response_handling():
    detector = Gemma4E4BDetector()
    detector.client = MagicMock()

    mock_message = MagicMock()
    mock_message.content = ""
    mock_response = MagicMock()
    mock_response.message = mock_message
    detector.client.chat.return_value = mock_response

    results = detector.detect("Sample text")
    assert results == []


def test_gemma_detector_invalid_json_handling():
    detector = Gemma4E4BDetector()
    detector.client = MagicMock()

    mock_message = MagicMock()
    mock_message.content = "{invalid json"
    mock_response = MagicMock()
    mock_response.message = mock_message
    detector.client.chat.return_value = mock_response

    results = detector.detect("Sample text")
    assert results == []


def test_gemma_detector_skips_blank_entity_values():
    detector = Gemma4E4BDetector()
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


def test_format_known_entities_supports_dicts_and_detection_results():
    detector = Gemma4E4BDetector()

    # 1. Dict-style entities
    dict_entities = [
        {"entity_type": "SSN", "start_char": 0, "end_char": 11, "field_path": None},
    ]
    formatted_dict = detector._format_known_entities(dict_entities)
    assert "- SSN at chars 0-11 (already detected; do not return)" in formatted_dict

    # 2. DetectionResult-style entities
    result_entities = [
        DetectionResult(
            entity_type="PHONE_NUMBER",
            entity_value="123-456-7890",
            confidence_score=0.9,
            start_char=20,
            end_char=32,
            detector="regex",
        )
    ]
    formatted_result = detector._format_known_entities(result_entities)
    assert "- PHONE_NUMBER at chars 20-32 (already detected; do not return)" in formatted_result

    # 3. DetectionResult with metadata field_path
    result_with_field = [
        DetectionResult(
            entity_type="EMAIL",
            entity_value="test@example.com",
            confidence_score=0.95,
            start_char=40,
            end_char=56,
            detector="regex",
            metadata={"field_path": "user.email"},
        )
    ]
    formatted_field = detector._format_known_entities(result_with_field)
    assert "- EMAIL at field 'user.email' (already detected; do not return)" in formatted_field
