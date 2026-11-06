import pytest

from cqa.graders import grade
from cqa.schema import Field, Question

FIELDS = (
    Field("renews", "bool"),
    Field("cap", "number"),
    Field("ends", "date"),
    Field("law", "choice", ("NY", "DE")),
)
Q = Question("X", "synthetic", True, "t", "p", (), FIELDS, {"renews": True, "cap": 1234567, "ends": "2026-03-06", "law": "DE"})


def test_all_correct():
    got = {"renews": True, "cap": 1234567.0, "ends": "2026-03-06", "law": "de"}
    assert grade(Q, got) == {"renews": True, "cap": True, "ends": True, "law": True}


def test_missing_fields_are_wrong():
    assert grade(Q, {}) == {"renews": False, "cap": False, "ends": False, "law": False}


@pytest.mark.parametrize("got,ok", [(True, True), ("yes", True), (False, False), (1, False), ("maybe", False)])
def test_bool(got, ok):
    assert grade(Q, {"renews": got})["renews"] is ok


@pytest.mark.parametrize("got,ok", [("$1,234,567", True), ("1234567.00", True), (1234568, False), ("1 or 2", False), (True, False)])
def test_number(got, ok):
    assert grade(Q, {"cap": got})["cap"] is ok


@pytest.mark.parametrize("got,ok", [("2026-03-06", True), (" 2026-03-06 ", True), ("March 6, 2026", False), ("2026-03-07", False)])
def test_date(got, ok):
    assert grade(Q, {"ends": got})["ends"] is ok
