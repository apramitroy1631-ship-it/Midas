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
import math
import random
import re
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
#
# "per day" / "(tpd)" cover Groq's wording ("...on tokens per day (TPD)"),
# which the Gemini-shaped markers above missed - so a spent Groq daily cap was
# being retried with backoff before failing instead of failing immediately.
_DAILY_QUOTA_MARKERS = ("perday", "per_day", "per day", "daily", "(tpd)", "(rpd)")

_MAX_ATTEMPTS = 4
_BASE_DELAY_S = 2.0


class LLMQuotaError(RuntimeError):
    """The provider's daily allowance is spent. Message is written for the
    person watching the run, not for a developer reading a raw API error."""


def _is_daily_quota(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _DAILY_QUOTA_MARKERS)


def _humanize_wait(raw: str) -> str | None:
    """'7m10.704s' -> 'about 8 minutes'. Rounds up so we never promise sooner
    than it really frees up."""
    match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", raw)
    if not match or not any(match.groups()):
        return None
    hours, minutes, seconds = (float(g) if g else 0.0 for g in match.groups())
    total = hours * 3600 + minutes * 60 + seconds
    if total < 60:
        return "less than a minute"
    mins = math.ceil(total / 60)
    if mins < 60:
        return f"about {mins} minute{'s' if mins != 1 else ''}"
    h, m = divmod(mins, 60)
    parts = [f"{h} hour{'s' if h != 1 else ''}"]
    if m:
        parts.append(f"{m} minute{'s' if m != 1 else ''}")
    return "about " + " ".join(parts)


def _quota_message(exc: Exception) -> str:
    # Groq says "Please try again in 7m10.704s." - turn that into something readable.
    match = re.search(r"try again in ([0-9hms.]+)", str(exc))
    wait = _humanize_wait(match.group(1).rstrip(".")) if match else None
    if wait:
        return f"The AI provider's daily usage limit has been reached. Please try again in {wait}."
    return "The AI provider's daily usage limit has been reached. Try again later, or raise the limit with the provider."


def _is_retryable(exc: Exception) -> bool:
    if _is_daily_quota(exc):
        return False
    text = str(exc).lower()
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
            if _is_daily_quota(exc):
                raise LLMQuotaError(_quota_message(exc)) from exc
            if attempt == _MAX_ATTEMPTS or not _is_retryable(exc):
                raise
            delay = _BASE_DELAY_S * (2 ** (attempt - 1)) + random.uniform(0, 1)
            logger.warning(
                "LLM call retrying | %s | attempt %d/%d | waiting %.1fs | %s",
                label, attempt, _MAX_ATTEMPTS, delay, exc,
            )
            time.sleep(delay)
    raise last_exc  # pragma: no cover - loop always returns or raises above
