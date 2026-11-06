"""Deterministic grading: compare each typed answer field to the expected value."""

from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any, Callable

from .schema import Field, Question

_TRUE = {"true", "yes", "y"}
_FALSE = {"false", "no", "n"}
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def grade_bool(field: Field, expected: Any, got: Any) -> bool:
    if isinstance(got, str):
        s = got.strip().casefold().rstrip(".")
        got = True if s in _TRUE else False if s in _FALSE else None
    return got is expected


def grade_number(field: Field, expected: Any, got: Any) -> bool:
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


def grade_date(field: Field, expected: Any, got: Any) -> bool:
    try:
        return dt.date.fromisoformat(str(got).strip()).isoformat() == expected
    except ValueError:
        return False


def grade_choice(field: Field, expected: Any, got: Any) -> bool:
    return str(got).strip().casefold() == str(expected).casefold()


GRADERS: dict[str, Callable[[Field, Any, Any], bool]] = {
    "bool": grade_bool,
    "number": grade_number,
    "date": grade_date,
    "choice": grade_choice,
}


def grade(question: Question, got: dict[str, Any]) -> dict[str, bool]:
    """Per-field correctness. A missing field is wrong."""
    return {
        f.key: f.key in got and got[f.key] is not None
        and GRADERS[f.type](f, question.expected[f.key], got[f.key])
        for f in question.fields
    }
