# app/services/llm/usage.py
"""Per-run token and cost accounting.

Providers report into an ambient meter so cost can be attributed to a run
without threading a cost object through every agent call. Prices are per
1M tokens, in USD.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator

PRICES: dict[str, tuple[float, float]] = {
    # model            (input $/1M, output $/1M)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}
_FALLBACK_PRICE = (1.00, 3.00)


@dataclass
class UsageMeter:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    calls: int = 0
    by_agent: dict[str, int] = field(default_factory=dict)

    def record(self, model: str, prompt: int, completion: int, agent: str = "") -> None:
        p_in, p_out = PRICES.get(model, _FALLBACK_PRICE)
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.cost_usd = round(
            self.cost_usd + (prompt / 1_000_000) * p_in + (completion / 1_000_000) * p_out, 6
        )
        self.calls += 1
        if agent:
            self.by_agent[agent] = self.by_agent.get(agent, 0) + prompt + completion

    def snapshot(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "llm_calls": self.calls,
            "tokens_by_agent": dict(self.by_agent),
        }


_meter: ContextVar[UsageMeter | None] = ContextVar("usage_meter", default=None)
_agent: ContextVar[str] = ContextVar("usage_agent", default="")


def record(model: str, prompt: int, completion: int) -> None:
    meter = _meter.get()
    if meter is not None:
        meter.record(model, prompt, completion, _agent.get())


@contextmanager
def metered() -> Iterator[UsageMeter]:
    meter = UsageMeter()
    token = _meter.set(meter)
    try:
        yield meter
    finally:
        _meter.reset(token)


@contextmanager
def attributed_to(agent: str) -> Iterator[None]:
    token = _agent.set(agent)
    try:
        yield
    finally:
        _agent.reset(token)
