"""Plain data types. A document is any folder of rNN__ files under documents/; its id is that path."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, get_args

AnswerKind = Literal["bool", "number", "date", "choice"]
Verdict = Literal["ACCEPT", "REJECT", "ESCALATE"]
Source = Literal["expert", "synthetic"]
SOURCES = get_args(Source)
ANSWER_KINDS = get_args(AnswerKind)

REVISION_NAME = re.compile(r"^r(\d{2})__(.+)$")


@dataclass(frozen=True)
class Revision:
    path: Path  # relative to the dataset root

    @property
    def number(self) -> int:
        return int(_revision_match(self.path.name).group(1))

    @property
    def filename(self) -> str:
        """The original filename, without the rNN__ prefix: what the agent sees."""
        return _revision_match(self.path.name).group(2)


@dataclass(frozen=True)
class Document:
    id: str
    revisions: tuple[Revision, ...]  # oldest first

    @property
    def latest(self) -> Revision:
        return self.revisions[-1]


@dataclass(frozen=True)
class AnswerType:
    """All the agent learns about the expected answer."""

    kind: AnswerKind
    choices: tuple[str, ...] = ()  # for kind == "choice"


@dataclass(frozen=True)
class Evidence:
    file: Revision
    quote: str


@dataclass(frozen=True)
class Question:
    id: str
    source: Source
    reviewed: bool  # have `expected`/`evidence` been checked by an expert?
    title: str
    prompt: str
    files: tuple[Revision, ...]
    answer_type: AnswerType | None  # None -> not graded yet (free-text answer, or no answer yet)
    expected: Any
    evidence: tuple[Evidence, ...] = ()

    @property
    def deferred(self) -> bool:
        return self.answer_type is None


@dataclass(frozen=True)
class Dataset:
    root: Path
    documents: dict[str, Document]
    questions: list[Question]

    def abspath(self, rev: Revision) -> Path:
        return self.root / rev.path


@dataclass(frozen=True)
class Citation:
    file: str  # filename as the agent saw it
    quote: str
    location: str | None  # e.g. "¶39" if the quote was found in the file, else None
    controlling: bool  # overlaps an expert evidence quote


@dataclass(frozen=True)
class Result:
    question_id: str
    verdict: Verdict
    reason: str
    answer: Any
    answer_correct: bool
    citations: tuple[Citation, ...] = ()
    explanation: str = ""  # shown in the report, not graded
    error: str | None = None
    audit: tuple[str, ...] = ()
    # Written to trajectories.jsonl, not results.jsonl.
    trajectory: list[dict[str, Any]] = field(default_factory=list, repr=False, compare=False)


def _revision_match(name: str) -> re.Match:
    m = REVISION_NAME.match(name)
    if not m:
        raise ValueError(f"not a revision filename (expected rNN__<name>): {name}")
    return m
