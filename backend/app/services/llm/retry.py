# app/services/llm/retry.py
"""Retry wrapper for transient LLM API failures.

Real LLM APIs fail transiently, and often — a 429 rate limit, a 503 "model
currently experiencing high demand", a dropped connection. None of these
mean the request itself was wrong, and failing an entire campaign run over
one blip (confirmed happening in practice: a single transient 503 killed a
run outright, with zero retry) is needless. This wraps one call with
exponential backoff, retrying only error shapes actually worth retrying —
anything else (a bad API key, a malformed prompt) still fails immediately,
since retrying those would just waste time before failing anyway.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")

logger = logging.getLogger("llm.retry")

# Substrings, not exact codes, because every provider's SDK formats errors
# differently — OpenAI, Anthropic, and Gemini all raise different exception
# types with the status buried in the message text, not a clean attribute.
_RETRYABLE_MARKERS = (
    "429", "503", "500", "502", "504",
    "resource_exhausted", "unavailable", "rate limit", "rate_limit",
    "overloaded", "timeout", "timed out", "connection",
)

# A 429 with one of these markers is a hard daily/monthly cap, not a burst
# rate limit — confirmed in practice: Gemini's free tier returns 429 with
# "GenerateRequestsPerDayPerProjectPerModel-FreeTier" for a 20/day cap, and
# no amount of backoff inside one process fixes that before the quota
# actually resets. Retrying it just burns ~15s to fail anyway; better to
# say so immediately.
_DAILY_QUOTA_MARKERS = ("perday", "per_day", "daily")

_MAX_ATTEMPTS = 4
_BASE_DELAY_S = 2.0


def _is_retryable(exc: Exception) -> bool:
    text = str(exc).lower()
    if any(marker in text for marker in _DAILY_QUOTA_MARKERS):
        return False
    return any(marker in text for marker in _RETRYABLE_MARKERS)


def with_retry(fn: Callable[[], T], *, label: str = "llm-call") -> T:
    """Call `fn()`, retrying with exponential backoff + jitter on a
    retryable failure. Raises immediately on anything else, and re-raises
    the last error once attempts are exhausted."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - any provider's SDK can raise here
            last_exc = exc
            if attempt == _MAX_ATTEMPTS or not _is_retryable(exc):
                raise
            delay = _BASE_DELAY_S * (2 ** (attempt - 1)) + random.uniform(0, 1)
            logger.warning(
                "LLM call retrying | %s | attempt %d/%d | waiting %.1fs | %s",
                label, attempt, _MAX_ATTEMPTS, delay, exc,
            )
            time.sleep(delay)
    raise last_exc  # pragma: no cover - loop always returns or raises above
