"""Plain data types. Every other module depends on this one and nothing else in verdict.

Dataset layout (the directory is the source of truth; nothing is read from inside the files):

    dataset/
      questions.yaml
      documents/<document_id>/r01__<original filename>
                              r02__<original filename>     # later revision of the same document

A document is any folder of rNN__ files; its id is its path under documents/, so documents can
be grouped in plain folders (e.g. documents/cuad/<category>/<contract>/r01__....pdf).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

AnswerKind = Literal["bool", "number", "date", "choice"]
Verdict = Literal["ACCEPT", "REJECT", "ESCALATE"]
Source = Literal["expert", "synthetic"]
SOURCES: tuple[str, ...] = ("expert", "synthetic")
ANSWER_KINDS: tuple[str, ...] = ("bool", "number", "date", "choice")

REVISION_NAME = re.compile(r"^r(\d{2})__(.+)$")


@dataclass(frozen=True)
class Revision:
    """One file in a document's revision chain."""

    path: Path  # relative to the dataset root, e.g. documents/clientco_msa/r06__....docx

    @property
    def document_id(self) -> str:
        return self.path.parent.relative_to("documents").as_posix()

    @property
    def number(self) -> int:
        return int(_revision_match(self.path.name).group(1))

    @property
    def filename(self) -> str:
        """The original filename, without the rNN__ prefix. This is what the agent sees."""
        return _revision_match(self.path.name).group(2)


@dataclass(frozen=True)
class Document:
    """All revisions of one contract, oldest first."""

    id: str
    revisions: tuple[Revision, ...]

    @property
    def latest(self) -> Revision:
        return self.revisions[-1]

    def previous(self, rev: Revision) -> Revision | None:
        i = self.revisions.index(rev)
        return self.revisions[i - 1] if i else None


@dataclass(frozen=True)
class AnswerType:
    """The type of a question's answer. This is all the agent learns about the expected answer."""

    kind: AnswerKind
    choices: tuple[str, ...] = ()  # for kind == "choice"


@dataclass(frozen=True)
class Evidence:
    """Expert-annotated controlling language: a verbatim quote from one of the question's files."""

    file: Revision
    quote: str


@dataclass(frozen=True)
class Question:
    id: str
    source: Source  # expert: from the team's Q&A; synthetic: written by Claude
    reviewed: bool  # have `expected`/`evidence` been checked by an expert?
    title: str
    prompt: str
    files: tuple[Revision, ...]
    answer_type: AnswerType | None  # None -> not graded yet (free-text answer, or no answer yet)
    expected: Any  # the expected answer value
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
    """One quote the agent cited, after checking it against the file."""

    file: str  # filename as the agent saw it
    quote: str
    location: str | None  # e.g. "¶39" if the quote was found in the file, else None
    controlling: bool  # overlaps one of the question's expert evidence quotes


@dataclass(frozen=True)
class Result:
    question_id: str
    verdict: Verdict
    reason: str
    answer: Any  # the agent's typed answer, as submitted
    answer_correct: bool
    citations: tuple[Citation, ...] = ()
    explanation: str = ""  # the agent's reasoning; shown in the report, not graded
    error: str | None = None  # agent failure; verdict is REJECT
    audit: tuple[str, ...] = ()  # agent actions that may have reached for the answer key
    # What the agent did (API requests/responses etc.); written to trajectories.jsonl.
    trajectory: list[dict[str, Any]] = field(default_factory=list, repr=False, compare=False)


def _revision_match(name: str) -> re.Match:
    m = REVISION_NAME.match(name)
    if not m:
        raise ValueError(f"not a revision filename (expected rNN__<name>): {name}")
    return m
