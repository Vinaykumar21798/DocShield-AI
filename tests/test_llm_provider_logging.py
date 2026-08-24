from types import SimpleNamespace

from modules.detection.pipeline_state import PipelineState
from modules.detection.service import DetectionService, DynamicDetectionConfig


def test_llm_log_context_uses_active_detector_identity():
    azure = SimpleNamespace(
        name="azure",
        deployment="demo-azure-deployment",
        MODEL_NAME="unused-model",
    )
    gemma = SimpleNamespace(
        name="gemma",
        MODEL_NAME="demo-gemma-model",
    )

    assert DetectionService._llm_log_context(azure) == (
        "Azure",
        "demo-azure-deployment",
    )
    assert DetectionService._llm_log_context(gemma) == (
        "Gemma",
        "demo-gemma-model",
    )


def test_residual_skip_log_uses_active_provider(caplog):
    service = DetectionService()
    detector = SimpleNamespace(name="azure", MODEL_NAME="demo-azure-model")
    state = PipelineState(original_text="")

    with caplog.at_level("INFO", logger="modules.detection.service"):
        results = service._run_qwen_detector(
            detector=detector,
            state=state,
            page_number=1,
            remaining_candidates={"candidates": []},
            config=DynamicDetectionConfig(),
        )

    assert results == []
    message = caplog.text
    assert "provider=Azure" in message
    assert "model=demo-azure-model" in message
    assert "Gemma residual discovery" not in message


def test_usage_summary_is_provider_neutral(caplog):
    service = DetectionService()
    state = PipelineState(original_text="")

    with caplog.at_level("INFO", logger="modules.detection.service"):
        service._log_pipeline_summary(state, [], document_type=None)

    assert "LLM USAGE SUMMARY" in caplog.text
    assert "GEMMA USAGE SUMMARY" not in caplog.text
