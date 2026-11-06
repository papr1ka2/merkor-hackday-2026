"""Agents under test.

An agent gets the question prompt, the cited files (absolute paths plus the name to show),
and the type of answer it must give. It never sees the expected answer or expert evidence.

It returns a submission:
    {"answer": <one value of the question's answer type>,
     "citations": [{"file": <filename as shown>, "quote": <verbatim text>}, ...],
     "explanation": "<reasoning>",
     "trajectory": [<event>, ...]}          # optional: what the agent did, stored per run

If it fails, it may raise AgentError carrying the trajectory so far.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Protocol

from .schema import AnswerType

ANSWER_SCHEMA = {
    "bool": lambda f: {"type": "boolean"},
    "number": lambda f: {"type": "number"},
    "date": lambda f: {"type": "string", "description": "YYYY-MM-DD"},
    "choice": lambda f: {"type": "string", "enum": list(f.choices)},
}


class AgentError(RuntimeError):
    def __init__(self, message: str, trajectory: list[dict[str, Any]]):
        super().__init__(message)
        self.trajectory = trajectory


class Agent(Protocol):
    def answer(
        self, prompt: str, files: list[tuple[Path, str]], answer_type: AnswerType
    ) -> dict[str, Any]: ...


def submission_schema(answer_type: AnswerType, filenames: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "answer": ANSWER_SCHEMA[answer_type.kind](answer_type),
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
    and finishes by calling `submit_answer`, whose schema is built from the answer type.
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
        self, prompt: str, files: list[tuple[Path, str]], answer_type: AnswerType
    ) -> dict[str, Any]:
        from . import llm

        trajectory: list[dict[str, Any]] = []
        uploaded = []
        try:
            for path, name in files:
                mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
                uploaded.append(llm.client().files.upload(file=(name, path.read_bytes(), mime)))
            trajectory.append(
                {"type": "files", "files": [{"filename": f.filename, "file_id": f.id} for f in uploaded]}
            )
            submission = self._run(prompt, uploaded, answer_type, trajectory)
            return {**submission, "trajectory": trajectory}
        except Exception as e:
            trajectory.append({"type": "error", "error": repr(e)})
            raise AgentError(repr(e), trajectory) from e
        finally:
            for f in uploaded:
                try:
                    llm.client().files.delete(f.id)
                except Exception:
                    pass

    def _run(
        self, prompt: str, uploaded: list, answer_type: AnswerType, trajectory: list[dict[str, Any]]
    ) -> dict[str, Any]:
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
                "input_schema": submission_schema(answer_type, [f.filename for f in uploaded]),
            },
        ]
        trajectory.append(
            {"type": "request", "system": self.SYSTEM, "tools": tools, "message": messages[0]}
        )
        container = None
        for turn in range(self.MAX_TURNS):
            resp = llm.create(
                system=self.SYSTEM,
                messages=messages,
                tools=tools,
                output_config={"effort": self.effort},
                **({"container": container} if container else {}),
            )
            trajectory.append({"type": "response", "turn": turn, "response": resp.model_dump(mode="json")})
            container = resp.container.id if resp.container else container
            for block in resp.content:
                if block.type == "tool_use" and block.name == "submit_answer":
                    return dict(block.input)

            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "pause_turn":
                continue  # server-side tool loop hit its limit; resend to resume
            if resp.stop_reason == "end_turn":
                nudge = {"role": "user", "content": "Call submit_answer with your final answer."}
                messages.append(nudge)
                trajectory.append({"type": "user", "message": nudge})
                continue
            raise RuntimeError(f"unexpected stop_reason: {resp.stop_reason}")
        raise RuntimeError(f"no submit_answer after {self.MAX_TURNS} turns")


class StaticAgent:
    """Returns fixed submissions keyed by prompt. For tests and pipeline smoke runs."""

    def __init__(self, answers_by_prompt: dict[str, dict[str, Any]]):
        self.answers_by_prompt = answers_by_prompt

    def answer(
        self, prompt: str, files: list[tuple[Path, str]], answer_type: AnswerType
    ) -> dict[str, Any]:
        return dict(self.answers_by_prompt.get(prompt, {}))
