"""Plain data types. Every other module depends on this one and nothing else in cqa."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

QuestionType = Literal["bool", "choice", "number", "date", "text"]
QUESTION_TYPES: tuple[str, ...] = ("bool", "choice", "number", "date", "text")

BASE_VERSION = "v0"


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    type: QuestionType
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class Version:
    """One self-contained version of a contract and its expert answer key."""

    family: str
    id: str
    text: str
    answers: dict[str, Any]

    @property
    def key(self) -> str:
        return f"{self.family}/{self.id}"

    @property
    def is_base(self) -> bool:
        return self.id == BASE_VERSION


@dataclass(frozen=True)
class Family:
    """A contract and all its versions. They share one question set."""

    id: str
    questions: list[Question]
    versions: list[Version] = field(default_factory=list)

    @property
    def base(self) -> Version:
        return next(v for v in self.versions if v.is_base)

    def changed_questions(self, version: Version) -> set[str]:
        """Question ids whose expert answer differs from the base version."""
        if version.is_base:
            return set()
        base = self.base.answers
        return {qid for qid, ans in version.answers.items() if ans != base[qid]}


@dataclass(frozen=True)
class Result:
    family: str
    version: str
    question_id: str
    question_type: QuestionType
    expected: Any
    got: Any
    correct: bool
    # None on the base version; on other versions, whether the expert answer
    # differs from the base (i.e. the redline should have flipped it).
    changed: bool | None
    # Set when the agent or judge call failed; such rows count as incorrect.
    error: str | None = None
