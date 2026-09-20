# app/agents/channel_specs.py
"""How long each channel's copy should be, and how to size a rewrite.

The Content agent used to get no length guidance at all, so LinkedIn posts
came out blog-sized, and a "make it shorter" regenerate had nothing to aim at
- it either barely changed or collapsed the post. Lengths are decided here in
plain code and handed to the model as a number range, then checked afterwards,
rather than hoping the model's sense of "concise" matches ours.

Word counts are for the body only, with HTML tags stripped (email bodies are
HTML, and markup would otherwise inflate the count).
"""
from __future__ import annotations

import re

# (target_min, target_max) words for the body.
CHANNEL_WORDS: dict[str, tuple[int, int]] = {
    "linkedin": (60, 150),
    "email": (80, 200),
    "blog": (600, 1200),
}

_CAPPED_ON_HOLD = {"linkedin", "email"}

# A draft is only flagged once it's this far past the target - the model
# won't hit a range exactly, and a retry costs a full extra call.
_OVER_TOLERANCE = 1.25
_UNDER_TOLERANCE = 0.85  # used for rewrites aimed at a specific length

_TAGS = re.compile(r"<[^>]+>")

_SHORTEN = re.compile(
    r"\b(short(er|en)?|concise|brief(er)?|trim|cut|tighten|too long|lengthy|reduce|condense|compact)\b", re.I
)
_LENGTHEN = re.compile(r"\b(longer|expand|elaborate|more detail|more depth|add more|flesh out)\b", re.I)
_EXPLICIT = re.compile(r"(\d[\d,]*)\s*(words?|characters?|chars?)\b", re.I)


def word_count(text: str) -> int:
    return len(_TAGS.sub(" ", text or "").split())


def channel_range(channel: str) -> tuple[int, int] | None:
    return CHANNEL_WORDS.get((channel or "").strip().lower())


def default_length_block(channels: list[str]) -> dict[str, str]:
    """Prompt-ready {channel: 'lo-hi words'} for the channels being written."""
    out: dict[str, str] = {}
    for ch in channels:
        rng = channel_range(ch)
        if rng:
            out[ch] = f"{rng[0]}-{rng[1]} words"
    return out


def over_length(assets: list[dict]) -> str | None:
    """Message describing assets far past their channel's target, or None."""
    problems = []
    for a in assets:
        rng = channel_range(a.get("channel", ""))
        if not rng:
            continue
        n = word_count(a.get("body", ""))
        if n > rng[1] * _OVER_TOLERANCE:
            problems.append(f"{a.get('channel')}: body is {n} words, must be {rng[0]}-{rng[1]}")
    return "; ".join(problems) or None


def _window(low: int, high: int) -> tuple[int, int]:
    """Never hand the model a needle-thin range ("60-61 words"): at least ~15% wide."""
    low = max(low, 1)
    return low, max(high, int(low * 1.15) + 1)


def rewrite_target(channel: str, previous_words: int, feedback: str) -> tuple[int, int]:
    """Word range a regenerated asset should land in.

    Default is to hold length steady (+/-10%) so feedback about tone or a
    missing detail doesn't quietly rewrite the size - but never above the
    channel's own ceiling, so regenerating an oversized LinkedIn post also
    brings it back to a sane length. Only feedback that is actually about
    length moves it: an explicit number is honoured, "shorter" means a
    meaningful but not total cut (about a quarter to a third off), and
    "longer" grows it by about a third.
    """
    rng = channel_range(channel)
    prev = max(previous_words, 1)
    fb = feedback or ""

    explicit = _EXPLICIT.search(fb)
    if explicit:
        n = int(explicit.group(1).replace(",", ""))
        words = n if explicit.group(2).lower().startswith("word") else max(n // 6, 1)
        return _window(int(words * 0.9), int(words * 1.1))

    if _SHORTEN.search(fb) and not _LENGTHEN.search(fb):
        low, high = int(prev * 0.62), int(prev * 0.78)
        if rng:
            low = max(low, min(rng[0], prev))  # don't cut below the channel's floor
        return _window(low, high)

    if _LENGTHEN.search(fb):
        low, high = int(prev * 1.2), int(prev * 1.45)
        if rng:
            high = min(high, max(int(rng[1] * 1.25), prev + 1))  # some headroom, but not unbounded
            low = min(low, int(high * 0.9))
        return _window(low, high)

    low, high = int(prev * 0.9), int(prev * 1.1)
    # Short-form channels get pulled back under their ceiling; a long-form blog
    # keeps its length (its range is a default for new drafts, not a cap).
    if rng and channel.strip().lower() in _CAPPED_ON_HOLD and high > rng[1]:
        high = rng[1]
        low = min(low, int(high * 0.9))
    return _window(low, high)


def outside_target(text: str, target: tuple[int, int]) -> str | None:
    n = word_count(text)
    low, high = target
    if n < low * _UNDER_TOLERANCE or n > high * _OVER_TOLERANCE:
        return f"body was {n} words; it must be {low}-{high} words"
    return None
