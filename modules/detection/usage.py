"""Exact LLM usage extraction and configurable cost accounting.

Token counts are accepted only from provider response metadata.  Cost rates
come from deployment configuration; this module deliberately has no pricing
defaults because model, region, deployment type, discounts, and local compute
costs vary.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import os
from typing import Any, Callable, Optional


NANOSECONDS_PER_SECOND = Decimal("1000000000")
SECONDS_PER_HOUR = Decimal("3600")
TOKENS_PER_MILLION = Decimal("1000000")


def _member(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _nonnegative_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _positive_decimal(value: Any) -> Optional[Decimal]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed > 0 else None


def optional_nonnegative_decimal_env(name: str) -> Optional[Decimal]:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return None
    try:
        value = Decimal(raw_value.strip())
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a non-negative decimal value") from exc
    if value < 0:
        raise ValueError(f"{name} must be a non-negative decimal value")
    return value


@dataclass(frozen=True)
class ProviderUsage:
    prompt_tokens: int
    completion_tokens: int
    cached_prompt_tokens: Optional[int] = None
    duration_seconds: Optional[Decimal] = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def extract_azure_usage(response: Any) -> Optional[ProviderUsage]:
    """Read exact Chat Completions usage, including cached prompt tokens."""
    usage = _member(response, "usage")
    if usage is None:
        return None

    prompt_tokens = _nonnegative_int(_member(usage, "prompt_tokens"))
    completion_tokens = _nonnegative_int(
        _member(usage, "completion_tokens")
    )
    if prompt_tokens is None and completion_tokens is None:
        return None

    prompt_details = _member(usage, "prompt_tokens_details")
    cached_prompt_tokens = None
    if prompt_details is not None:
        cached_prompt_tokens = _nonnegative_int(
            _member(prompt_details, "cached_tokens")
        )
        if cached_prompt_tokens is not None:
            cached_prompt_tokens = min(
                cached_prompt_tokens,
                prompt_tokens or 0,
            )
    return ProviderUsage(
        prompt_tokens=prompt_tokens or 0,
        completion_tokens=completion_tokens or 0,
        cached_prompt_tokens=cached_prompt_tokens,
    )


def extract_ollama_usage(
    response: Any,
    *,
    elapsed_seconds: Optional[float] = None,
) -> Optional[ProviderUsage]:
    """Read exact Ollama counts and measured/provider-reported duration."""
    prompt_tokens = _nonnegative_int(
        _member(response, "prompt_eval_count")
    )
    completion_tokens = _nonnegative_int(_member(response, "eval_count"))
    if prompt_tokens is None and completion_tokens is None:
        return None

    duration_ns = _positive_decimal(_member(response, "total_duration"))
    if duration_ns is not None:
        duration_seconds = duration_ns / NANOSECONDS_PER_SECOND
    else:
        duration_seconds = _positive_decimal(elapsed_seconds)

    return ProviderUsage(
        prompt_tokens=prompt_tokens or 0,
        completion_tokens=completion_tokens or 0,
        cached_prompt_tokens=0,
        duration_seconds=duration_seconds,
    )


@dataclass(frozen=True)
class AzureTokenRates:
    input_per_million: Decimal
    output_per_million: Decimal
    cached_input_per_million: Optional[Decimal]

    @classmethod
    def from_env(cls) -> Optional["AzureTokenRates"]:
        input_rate = optional_nonnegative_decimal_env(
            "AZURE_OPENAI_INPUT_COST_PER_1M"
        )
        output_rate = optional_nonnegative_decimal_env(
            "AZURE_OPENAI_OUTPUT_COST_PER_1M"
        )
        cached_rate = optional_nonnegative_decimal_env(
            "AZURE_OPENAI_CACHED_INPUT_COST_PER_1M"
        )
        if input_rate is None and output_rate is None and cached_rate is None:
            return None
        if input_rate is None or output_rate is None:
            raise ValueError(
                "Both AZURE_OPENAI_INPUT_COST_PER_1M and "
                "AZURE_OPENAI_OUTPUT_COST_PER_1M are required when Azure "
                "pricing is configured"
            )
        return cls(input_rate, output_rate, cached_rate)

    def calculate(self, usage: ProviderUsage) -> Optional[Decimal]:
        cached_tokens = usage.cached_prompt_tokens
        if cached_tokens is None:
            if self.cached_input_per_million == self.input_per_million:
                cached_tokens = 0
            else:
                return None
        if cached_tokens and self.cached_input_per_million is None:
            return None
        uncached_tokens = usage.prompt_tokens - cached_tokens
        cost = (
            Decimal(uncached_tokens) * self.input_per_million
            + Decimal(usage.completion_tokens) * self.output_per_million
        ) / TOKENS_PER_MILLION
        if cached_tokens:
            cost += (
                Decimal(cached_tokens) * self.cached_input_per_million
            ) / TOKENS_PER_MILLION
        return cost


@dataclass(frozen=True)
class LocalComputeRate:
    usd_per_hour: Decimal

    @classmethod
    def from_env(cls) -> Optional["LocalComputeRate"]:
        rate = optional_nonnegative_decimal_env(
            "GEMMA_COMPUTE_COST_PER_HOUR_USD"
        )
        return cls(rate) if rate is not None else None

    def calculate(self, usage: ProviderUsage) -> Optional[Decimal]:
        if usage.duration_seconds is None:
            return None
        return usage.duration_seconds * self.usd_per_hour / SECONDS_PER_HOUR


class UsageLedger:
    """Aggregate provider-reported usage and auditable configured cost."""

    def __init__(
        self,
        cost_calculator: Optional[
            Callable[[ProviderUsage], Optional[Decimal]]
        ],
        *,
        cost_basis: Optional[str],
    ) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cached_prompt_tokens: Optional[int] = 0
        self.duration_seconds = Decimal("0")
        self.usage_records = 0
        self.is_complete = True
        self._cost_calculator = cost_calculator
        self._total_cost_usd = (
            Decimal("0") if cost_calculator is not None else None
        )
        self.cost_basis = cost_basis if cost_calculator is not None else None

    @property
    def total_cost_usd(self) -> Optional[float]:
        if self._total_cost_usd is None:
            return None
        return float(self._total_cost_usd)

    def record(self, usage: ProviderUsage) -> None:
        self.prompt_tokens += usage.prompt_tokens
        self.completion_tokens += usage.completion_tokens
        if self.cached_prompt_tokens is not None:
            if usage.cached_prompt_tokens is None:
                self.cached_prompt_tokens = None
            else:
                self.cached_prompt_tokens += usage.cached_prompt_tokens
        if usage.duration_seconds is not None:
            self.duration_seconds += usage.duration_seconds
        self.usage_records += 1

        if self._cost_calculator is None or self._total_cost_usd is None:
            return
        call_cost = self._cost_calculator(usage)
        if call_cost is None:
            self._total_cost_usd = None
            self.cost_basis = None
            return
        self._total_cost_usd += call_cost

    def mark_incomplete(self) -> None:
        self.is_complete = False
        self._total_cost_usd = None
        self.cost_basis = None
