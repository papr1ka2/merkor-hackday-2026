"""The one place that talks to the Claude API. Used by the Claude agent and the text judge."""

from __future__ import annotations

import json
import os
from functools import cache
from typing import Any

import anthropic

MODEL = os.environ.get("CQA_MODEL", "claude-opus-5-5")


class RefusalError(RuntimeError):
    pass


@cache
def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def complete_json(
    *, system: str, prompt: str, schema: dict[str, Any], effort: str = "medium"
) -> dict[str, Any]:
    """One request whose response is constrained to `schema`. Returns the parsed JSON."""
    resp = _client().beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "effort": effort,
            "format": {"type": "json_schema", "schema": schema},
        },
        # If a safety classifier declines, the API re-runs on a recommended fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise RefusalError(f"model declined: {resp.stop_details}")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)
