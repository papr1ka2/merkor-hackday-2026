import pytest

from cqa.graders import grade
from cqa.schema import AnswerType, Question


def q(kind, expected, choices=()):
    return Question("X", "synthetic", True, "t", "p", (), AnswerType(kind, choices), expected)


@pytest.mark.parametrize("got,ok", [(True, True), ("yes", True), (False, False), (1, False), ("maybe", False), (None, False)])
def test_bool(got, ok):
    assert grade(q("bool", True), got) is ok


@pytest.mark.parametrize("got,ok", [(1234567, True), (1234567.0, True), ("$1,234,567", True), (1234568, False), ("1 or 2", False), (True, False)])
def test_number(got, ok):
    assert grade(q("number", 1234567), got) is ok


@pytest.mark.parametrize("got,ok", [("2026-03-06", True), (" 2026-03-06 ", True), ("March 6, 2026", False), ("2026-03-07", False)])
def test_date(got, ok):
    assert grade(q("date", "2026-03-06"), got) is ok


@pytest.mark.parametrize("got,ok", [("DE", True), ("de", True), ("NY", False)])
def test_choice(got, ok):
    assert grade(q("choice", "DE", ("NY", "DE")), got) is ok
