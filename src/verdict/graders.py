"""Deterministic grading.

Two independent checks, combined into one verdict:
  answer    the typed answer vs the expected value
  evidence  each cited quote exists in the cited file, and at least one overlaps
            an expert-annotated controlling clause

    answer wrong                                   -> REJECT
    answer right, a quote not found in the file    -> ESCALATE
    answer right, no controlling clause cited      -> ESCALATE
    answer right, quotes found, controlling cited  -> ACCEPT
"""

from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any, Callable

from . import evidence
from .schema import AnswerType, Citation, Dataset, Question, Verdict

_TRUE = {"true", "yes", "y"}
_FALSE = {"false", "no", "n"}
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


# --- answer ---------------------------------------------------------------------


def grade_bool(t: AnswerType, expected: Any, got: Any) -> bool:
    if isinstance(got, str):
        s = got.strip().casefold().rstrip(".")
        got = True if s in _TRUE else False if s in _FALSE else None
    return got is expected


def grade_number(t: AnswerType, expected: Any, got: Any) -> bool:
    if isinstance(got, bool):
        return False
    if isinstance(got, str):
        nums = _NUMBER.findall(got.replace(",", ""))
        if len(nums) != 1:  # missing or ambiguous
            return False
        got = nums[0]
    try:
        return math.isclose(float(got), float(expected), rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return False


def grade_date(t: AnswerType, expected: Any, got: Any) -> bool:
    try:
        return dt.date.fromisoformat(str(got).strip()).isoformat() == expected
    except ValueError:
        return False


def grade_choice(t: AnswerType, expected: Any, got: Any) -> bool:
    return str(got).strip().casefold() == str(expected).casefold()


GRADERS: dict[str, Callable[[AnswerType, Any, Any], bool]] = {
    "bool": grade_bool,
    "number": grade_number,
    "date": grade_date,
    "choice": grade_choice,
}


def grade(question: Question, got: Any) -> bool:
    """Is the submitted answer the expected one? A missing answer is wrong."""
    t = question.answer_type
    return got is not None and GRADERS[t.kind](t, question.expected, got)


# --- evidence ----------------------------------------------------------------------


def check_citations(
    dataset: Dataset, question: Question, citations: list[dict[str, Any]]
) -> tuple[Citation, ...]:
    by_name = {rev.filename: rev for rev in question.files}
    checked = []
    for c in citations:
        name, quote = str(c.get("file", "")), str(c.get("quote", ""))
        rev = by_name.get(name)
        location = evidence.locate(dataset.abspath(rev), quote) if rev else None
        controlling = location is not None and any(
            ev.file == rev and evidence.overlaps(quote, ev.quote) for ev in question.evidence
        )
        checked.append(Citation(file=name, quote=quote, location=location, controlling=controlling))
    return tuple(checked)


# --- verdict -----------------------------------------------------------------------


def verdict(
    question: Question, answer_correct: bool, citations: tuple[Citation, ...]
) -> tuple[Verdict, str]:
    if not answer_correct:
        note = " (did cite a controlling clause)" if any(c.controlling for c in citations) else ""
        return "REJECT", f"wrong answer{note}"

    unfound = [c for c in citations if c.location is None]
    if unfound:
        return "ESCALATE", f"answer correct, but {len(unfound)} cited quote(s) not found in the file"
    if not question.evidence:
        return "ACCEPT", "answer correct (no expert evidence annotated)"

    cited = sum(
        any(c.controlling and evidence.overlaps(c.quote, ev.quote) for c in citations)
        for ev in question.evidence
    )
    if not cited:
        return "ESCALATE", "answer correct, but cites none of the controlling clauses"
    return "ACCEPT", f"answer correct; cites {cited}/{len(question.evidence)} controlling clauses"
