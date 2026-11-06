"""Compare one agent answer to one expert answer. One grader per question type.

Structured types (bool/choice/number/date) are graded deterministically.
Only `text` questions call a judge, which is injectable so tests stay offline.
"""

from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any, Callable

from .schema import Question

Judge = Callable[[Question, Any, Any], bool]

_TRUE = {"true", "yes", "y", "1"}
_FALSE = {"false", "no", "n", "0"}
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def grade_bool(q: Question, expected: Any, got: Any) -> bool:
    return _to_bool(got) == expected


def grade_choice(q: Question, expected: Any, got: Any) -> bool:
    return str(got).strip().casefold() == str(expected).casefold()


def grade_number(q: Question, expected: Any, got: Any) -> bool:
    if isinstance(got, (int, float)) and not isinstance(got, bool):
        value = float(got)
    else:
        nums = _NUMBER.findall(str(got).replace(",", ""))
        if len(nums) != 1:  # ambiguous or missing
            return False
        value = float(nums[0])
    return math.isclose(value, float(expected), rel_tol=1e-9, abs_tol=1e-9)


def grade_date(q: Question, expected: Any, got: Any) -> bool:
    try:
        return dt.date.fromisoformat(str(got).strip()).isoformat() == expected
    except ValueError:
        return False


GRADERS: dict[str, Callable[[Question, Any, Any], bool]] = {
    "bool": grade_bool,
    "choice": grade_choice,
    "number": grade_number,
    "date": grade_date,
}


def grade(q: Question, expected: Any, got: Any, judge: Judge | None = None) -> bool:
    if got is None or str(got).strip() == "":
        return False
    if q.type == "text":
        return (judge or llm_judge)(q, expected, got)
    return GRADERS[q.type](q, expected, got)


def llm_judge(q: Question, expected: Any, got: Any) -> bool:
    from . import llm

    out = llm.complete_json(
        system=(
            "You grade answers to contract questions against an expert's reference answer. "
            "An answer is correct if it agrees with the reference on every material point; "
            "wording may differ. Extra detail is fine unless it contradicts the reference."
        ),
        prompt=(
            f"Question: {q.text}\n\nReference answer: {expected}\n\nCandidate answer: {got}\n\n"
            "Is the candidate answer correct?"
        ),
        schema={
            "type": "object",
            "properties": {"reasoning": {"type": "string"}, "correct": {"type": "boolean"}},
            "required": ["reasoning", "correct"],
            "additionalProperties": False,
        },
        effort="low",
    )
    return bool(out["correct"])


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    s = str(value).strip().casefold().rstrip(".")
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    return None
