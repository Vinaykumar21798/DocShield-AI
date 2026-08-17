"""Detector specifications, factory and availability probe.

Each detector is instantiated fresh and invoked directly via
BaseDetector.detect(text, page_number) - no DetectionService, no masking,
no known-entities, no shared state between detectors.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from eval_common import CONTENT_PATH

TRUE_VALUES = {"1", "true", "yes", "on"}

MODEL_CACHE_PATH = os.path.join(
    os.path.expanduser("~"),
    ".cache",
    "huggingface",
    "hub",
)


def _spacy_model_available() -> str | None:
    try:
        import spacy.util

        for candidate in ("en_core_web_sm", "en_core_web_lg"):
            if spacy.util.is_package(candidate):
                return candidate
    except Exception:
        return None
    return None


def _huggingface_model_cached(model_id: str) -> bool:
    folder = "models--" + model_id.replace("/", "--")
    return os.path.isdir(os.path.join(MODEL_CACHE_PATH, folder))


class DetectorProfile:
    def __init__(
        self,
        key: str,
        label: str,
        factory: Callable[[], Any],
        availability: Callable[[], dict[str, Any]],
    ) -> None:
        self.key = key
        self.label = label
        self.factory = factory
        self._availability = availability

    def availability(self) -> dict[str, Any]:
        return self._availability()


def _regex_availability() -> dict[str, Any]:
    return {
        "available": True,
        "mode": "pure_python",
        "model": "none",
        "error": None,
    }


def _presidio_availability() -> dict[str, Any]:
    try:
        import presidio_analyzer  # noqa: F401
    except Exception as exc:  # pragma: no cover
        return {
            "available": False,
            "mode": "unavailable",
            "model": "none",
            "error": f"presidio_analyzer import failed: {exc}",
        }
    model = _spacy_model_available()
    if model is None:
        return {
            "available": False,
            "mode": "unavailable",
            "model": "none",
            "error": "no local spaCy English model (en_core_web_sm/lg) installed",
        }
    return {
        "available": True,
        "mode": "presidio+spacy",
        "model": model,
        "error": None,
    }


def _medspacy_availability() -> dict[str, Any]:
    try:
        import medspacy  # noqa: F401
    except Exception as exc:
        return {
            "available": True,
            "mode": "deterministic_fallback_rules",
            "model": "none",
            "error": f"medspacy import failed, using fallback rules: {exc}",
        }
    return {
        "available": True,
        "mode": "medspacy_target_matcher",
        "model": "medspacy",
        "error": None,
    }


def _gliner_availability() -> dict[str, Any]:
    enabled = os.getenv("GLINER_ENABLED", "true").strip().lower() in TRUE_VALUES
    if not enabled:
        return {
            "available": True,
            "mode": "deterministic_fallback_rules",
            "model": "none",
            "error": "GLINER_ENABLED is false, using fallback rules",
        }
    try:
        import gliner  # noqa: F401
    except Exception as exc:
        return {
            "available": True,
            "mode": "deterministic_fallback_rules",
            "model": "none",
            "error": f"gliner import failed, using fallback rules: {exc}",
        }
    if not _huggingface_model_cached("urchade/gliner_medium-v2.1"):
        allow_download = (
            os.getenv("GLINER_ALLOW_MODEL_DOWNLOAD", "false").strip().lower()
            in TRUE_VALUES
        )
        if not allow_download:
            return {
                "available": True,
                "mode": "deterministic_fallback_rules",
                "model": "none",
                "error": (
                    "gliner_medium-v2.1 not in HF cache and "
                    "GLINER_ALLOW_MODEL_DOWNLOAD is false; using fallback rules"
                ),
            }
    return {
        "available": True,
        "mode": "model",
        "model": "urchade/gliner_medium-v2.1",
        "error": None,
    }


def _qwen_availability() -> dict[str, Any]:
    bypass = os.getenv("BYPASS_LLM", "false").strip().lower()
    if bypass in TRUE_VALUES:
        return {
            "available": False,
            "mode": "skipped",
            "model": "qwen3:4b",
            "error": "BYPASS_LLM is enabled",
        }
    try:
        from ollama import Client
    except Exception as exc:
        return {
            "available": False,
            "mode": "skipped",
            "model": "qwen3:4b",
            "error": f"ollama package import failed: {exc}",
        }
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        client = Client(host=host)
        models = client.list()
        names = [
            m.get("model") or m.get("name") or ""
            for m in models.get("models", [])
        ]
        if not any("qwen3:4b" in name for name in names):
            return {
                "available": False,
                "mode": "skipped",
                "model": "qwen3:4b",
                "error": f"qwen3:4b not served by Ollama at {host}; got: {names}",
            }
    except Exception as exc:
        return {
            "available": False,
            "mode": "skipped",
            "model": "qwen3:4b",
            "error": f"Ollama unreachable at {host}: {exc}",
        }
    return {
        "available": True,
        "mode": "ollama_qwen3_4b",
        "model": "qwen3:4b",
        "error": None,
    }


DETECTOR_PROFILES: dict[str, DetectorProfile] = {
    "regex": DetectorProfile(
        key="regex",
        label="Regex",
        factory=lambda: _instantiate(
            "modules.detection.detectors.regex_detector", "RegexDetector"
        ),
        availability=_regex_availability,
    ),
    "presidio": DetectorProfile(
        key="presidio",
        label="Presidio",
        factory=lambda: _instantiate(
            "modules.detection.detectors.presidio_detector", "PresidioDetector"
        ),
        availability=_presidio_availability,
    ),
    "medspacy": DetectorProfile(
        key="medspacy",
        label="MedSpaCy",
        factory=lambda: _instantiate(
            "modules.detection.detectors.medspacy_detector", "MedSpaCyDetector"
        ),
        availability=_medspacy_availability,
    ),
    "gliner": DetectorProfile(
        key="gliner",
        label="GLiNER",
        factory=lambda: _instantiate(
            "modules.detection.detectors.gliner_detector", "GLiNERDetector"
        ),
        availability=_gliner_availability,
    ),
    "qwen": DetectorProfile(
        key="qwen",
        label="Qwen3:4b",
        factory=lambda: _instantiate(
            "modules.detection.detectors.qwen_detector", "Qwen3BDetector"
        ),
        availability=_qwen_availability,
    ),
}


def _instantiate(module_path: str, class_name: str):
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls()


def availability_report() -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    for key, profile in DETECTOR_PROFILES.items():
        info = profile.availability()
        info["label"] = profile.label
        info["input_file"] = CONTENT_PATH
        report[key] = info
    return report
