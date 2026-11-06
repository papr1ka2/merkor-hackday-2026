"""The one place that talks to the Claude API."""

from __future__ import annotations

import os
from functools import cache
from typing import Any

import anthropic

MODEL = os.environ.get("VERDICT_MODEL", "claude-opus-5-5")


class RefusalError(RuntimeError):
    pass


@cache
def client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def create(**kwargs: Any):
    """messages.create with the project defaults. Raises on refusal."""
    resp = client().beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        # If a safety classifier declines, the API re-runs on a recommended fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        **kwargs,
    )
    if resp.stop_reason == "refusal":
        raise RefusalError(f"model declined: {resp.stop_details}")
    return resp
