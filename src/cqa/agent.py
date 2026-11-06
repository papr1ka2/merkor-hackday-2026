"""Agents under test.

An agent gets the question prompt, the cited files (absolute paths plus the name to show),
and the answer fields it must fill in. It never sees expected values or expert evidence.

It returns a submission:
    {"answer": {field_key: value, ...},
     "citations": [{"file": <filename as shown>, "quote": <verbatim text>}, ...],
     "explanation": "<reasoning>"}
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Protocol

from .schema import Field

FIELD_SCHEMA = {
    "bool": lambda f: {"type": "boolean"},
    "number": lambda f: {"type": "number"},
    "date": lambda f: {"type": "string", "description": "YYYY-MM-DD"},
    "choice": lambda f: {"type": "string", "enum": list(f.choices)},
}


class Agent(Protocol):
    def answer(
        self, prompt: str, files: list[tuple[Path, str]], fields: tuple[Field, ...]
    ) -> dict[str, Any]: ...


def submission_schema(fields: tuple[Field, ...], filenames: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "answer": {
                "type": "object",
                "properties": {f.key: FIELD_SCHEMA[f.type](f) for f in fields},
                "required": [f.key for f in fields],
                "additionalProperties": False,
            },
            "citations": {
                "type": "array",
                "description": "Verbatim quotes from the files that support the answer.",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string", "enum": filenames},
                        "quote": {"type": "string", "description": "Exact contract text; use … to skip words."},
                    },
                    "required": ["file", "quote"],
                    "additionalProperties": False,
                },
            },
            "explanation": {
                "type": "string",
                "description": "The rule applied, any exceptions, and any calculation, briefly.",
            },
        },
        "required": ["answer", "citations", "explanation"],
        "additionalProperties": False,
    }


class ClaudeAgent:
    """Claude with a code-execution sandbox holding the cited files.

    It reads the files however it likes (e.g. python-docx, raw XML for tracked changes)
    and finishes by calling `submit_answer`, whose schema is built from the fields.
    """

    SYSTEM = (
        "You are a careful contract lawyer. The contract files for this question are in your "
        "code-execution sandbox; read them directly, including any tracked changes (insertions "
        "and deletions) and comments. Answer only from the files and the facts in the question. "
"Support your answer with verbatim quotes of the controlling language. When you are "
        "done, call submit_answer exactly once."
    )
    MAX_TURNS = 8

    def __init__(self, effort: str = "high"):
        self.effort = effort

    def answer(
        self, prompt: str, files: list[tuple[Path, str]], fields: tuple[Field, ...]
    ) -> dict[str, Any]:
        from . import llm

        uploaded = [
            llm.client().files.upload(
                file=(name, path.read_bytes(), mimetypes.guess_type(name)[0] or "application/octet-stream")
            )
            for path, name in files
        ]
        try:
            return self._run(prompt, uploaded, fields)
        finally:
            for f in uploaded:
                try:
                    llm.client().files.delete(f.id)
                except Exception:
                    pass

    def _run(self, prompt: str, uploaded: list, fields: tuple[Field, ...]) -> dict[str, Any]:
        from . import llm

        names = "\n".join(f"- {f.filename}" for f in uploaded)
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Files:\n{names}\n\nQuestion:\n{prompt}"},
                    *({"type": "container_upload", "file_id": f.id} for f in uploaded),
                ],
            }
        ]
        tools = [
            {"type": "code_execution_20260521", "name": "code_execution"},
            {
                "name": "submit_answer",
                "description": "Submit your final answer with supporting quotes. Call once, at the end.",
                "strict": True,
                "input_schema": submission_schema(fields, [f.filename for f in uploaded]),
            },
        ]
        container = None
        for _ in range(self.MAX_TURNS):
            resp = llm.create(
                system=self.SYSTEM,
                messages=messages,
                tools=tools,
                output_config={"effort": self.effort},
                **({"container": container} if container else {}),
            )
            container = resp.container.id if resp.container else container
            for block in resp.content:
                if block.type == "tool_use" and block.name == "submit_answer":
                    return dict(block.input)

            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "pause_turn":
                continue  # server-side tool loop hit its limit; resend to resume
            if resp.stop_reason == "end_turn":
                messages.append(
                    {"role": "user", "content": "Call submit_answer with your final answer."}
                )
                continue
            raise RuntimeError(f"unexpected stop_reason: {resp.stop_reason}")
        raise RuntimeError(f"no submit_answer after {self.MAX_TURNS} turns")


class StaticAgent:
    """Returns fixed submissions keyed by prompt. For tests and pipeline smoke runs."""

    def __init__(self, answers_by_prompt: dict[str, dict[str, Any]]):
        self.answers_by_prompt = answers_by_prompt

    def answer(
        self, prompt: str, files: list[tuple[Path, str]], fields: tuple[Field, ...]
    ) -> dict[str, Any]:
        return dict(self.answers_by_prompt.get(prompt, {}))
