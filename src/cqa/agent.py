"""Agents under test. Anything with `answer(contract, questions) -> {question_id: answer}` works."""

from __future__ import annotations

from typing import Any, Protocol

from .schema import Question

FORMAT_HINTS = {
    "bool": "Answer 'yes' or 'no'.",
    "choice": "Answer with exactly one of: {choices}.",
    "number": "Answer with a single number only (no units).",
    "date": "Answer with a date in YYYY-MM-DD format.",
    "text": "Answer in one or two sentences.",
}


class Agent(Protocol):
    def answer(self, contract: str, questions: list[Question]) -> dict[str, Any]: ...


def format_questions(questions: list[Question]) -> str:
    lines = []
    for q in questions:
        hint = FORMAT_HINTS[q.type].format(choices=", ".join(q.choices))
        lines.append(f"- [{q.id}] {q.text} {hint}")
    return "\n".join(lines)


class ClaudeAgent:
    SYSTEM = (
        "You are a careful contract analyst. Answer each question using only the contract "
        "provided. Follow each question's answer format exactly."
    )

    def __init__(self, effort: str = "medium"):
        self.effort = effort

    def answer(self, contract: str, questions: list[Question]) -> dict[str, Any]:
        from . import llm

        schema = {
            "type": "object",
            "properties": {
                "answers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "enum": [q.id for q in questions]},
                            "answer": {"type": "string"},
                        },
                        "required": ["id", "answer"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["answers"],
            "additionalProperties": False,
        }
        prompt = (
            f"<contract>\n{contract}\n</contract>\n\n"
            f"Questions:\n{format_questions(questions)}"
        )
        out = llm.complete_json(system=self.SYSTEM, prompt=prompt, schema=schema, effort=self.effort)
        return {a["id"]: a["answer"] for a in out["answers"]}


class StaticAgent:
    """Returns fixed answers per contract text. For tests and pipeline smoke runs."""

    def __init__(self, answers_by_contract: dict[str, dict[str, Any]]):
        self.answers_by_contract = answers_by_contract

    def answer(self, contract: str, questions: list[Question]) -> dict[str, Any]:
        return dict(self.answers_by_contract.get(contract, {}))
