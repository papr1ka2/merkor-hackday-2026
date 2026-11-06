import pytest

from cqa.graders import grade
from cqa.schema import Question

BOOL = Question("q", "?", "bool")
CHOICE = Question("q", "?", "choice", ("New York", "Delaware"))
NUMBER = Question("q", "?", "number")
DATE = Question("q", "?", "date")
TEXT = Question("q", "?", "text")


@pytest.mark.parametrize("got,ok", [("yes", True), ("Yes.", True), ("true", True), (True, True), ("no", False), ("maybe", False)])
def test_bool(got, ok):
    assert grade(BOOL, True, got) is ok


@pytest.mark.parametrize("got,ok", [("Delaware", True), (" delaware ", True), ("New York", False)])
def test_choice(got, ok):
    assert grade(CHOICE, "Delaware", got) is ok


@pytest.mark.parametrize("got,ok", [("24", True), ("24 months", True), (24, True), ("24.0", True), ("12", False), ("12 or 24", False), ("", False)])
def test_number(got, ok):
    assert grade(NUMBER, 24, got) is ok


@pytest.mark.parametrize("got,ok", [("2025-03-01", True), ("2025-03-02", False), ("March 1, 2025", False)])
def test_date(got, ok):
    assert grade(DATE, "2025-03-01", got) is ok


def test_missing_answer_is_wrong():
    assert grade(NUMBER, 24, None) is False


def test_text_uses_injected_judge():
    calls = []

    def judge(q, expected, got):
        calls.append((expected, got))
        return got == "same"

    assert grade(TEXT, "ref", "same", judge) is True
    assert grade(TEXT, "ref", "different", judge) is False
    assert calls == [("ref", "same"), ("ref", "different")]
