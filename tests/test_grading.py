import zipfile
from pathlib import Path

import pytest

from verdict import evidence
from verdict.graders import grade, verdict
from verdict.schema import AnswerType, Citation, Evidence, Question, Revision


def q(kind, expected, choices=(), ev=()):
    rev = Revision(Path("documents/d/r01__a.docx"))
    return Question("X", "synthetic", True, "t", "p", (rev,), AnswerType(kind, choices), expected,
                    tuple(Evidence(rev, e) for e in ev))


@pytest.mark.parametrize(
    "kind,expected,got,ok",
    [
        ("bool", True, True, True), ("bool", True, "yes", True), ("bool", True, 1, False),
        ("bool", True, "maybe", False), ("bool", True, None, False),
        ("number", 1234567, 1234567.0, True), ("number", 1234567, "$1,234,567", True),
        ("number", 1234567, 1234568, False), ("number", 1234567, "1 or 2", False), ("number", 1, True, False),
        ("date", "2030-07-15", " 2030-07-15 ", True), ("date", "2030-07-15", "July 15, 2030", True),
        ("date", "2030-07-15", "15 July 2030", True), ("date", "2030-07-15", "Monday, 15 July 2030.", True),
        ("date", "2030-07-15", "2030-07-16", False), ("date", "2030-07-15", "mid July", False),
        ("choice", "DE", "de", True), ("choice", "DE", "NY", False),
    ],
)
def test_grade(kind, expected, got, ok):
    assert grade(q(kind, expected, ("NY", "DE")), got) is ok


CLAUSE = "survive termination for a period of two (2) years; provided, recipient's obligations"
GOOD = Citation("a.docx", CLAUSE, "¶1", True)
OTHER = Citation("a.docx", "some other text", "¶1", False)
FAKE = Citation("a.docx", "some other text", None, False)


@pytest.mark.parametrize(
    "correct,citations,evidence,want,reason",
    [
        (False, (GOOD,), (CLAUSE,), "REJECT", "did cite a controlling clause"),
        (True, (GOOD,), (CLAUSE,), "ACCEPT", "cites 1/1"),
        (True, (GOOD, FAKE), (CLAUSE,), "ESCALATE", "not found"),
        (True, (OTHER,), (CLAUSE,), "ESCALATE", "none of the controlling"),
        (True, (), (CLAUSE,), "ESCALATE", "none of the controlling"),
        (True, (), (), "ACCEPT", "no expert evidence"),
    ],
)
def test_verdict(correct, citations, evidence, want, reason):
    v, why = verdict(q("bool", True, ev=evidence), correct, citations)
    assert v == want and reason in why


DOCX = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:r><w:t>1. Term.</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Obligations survive for a period of </w:t></w:r>
<w:del><w:r><w:delText>five (5)</w:delText></w:r></w:del>
<w:ins><w:r><w:t>two (2)</w:t></w:r></w:ins>
<w:r><w:t xml:space="preserve"> years after the Recipient’s receipt of notice.</w:t></w:r></w:p>
</w:body></w:document>"""
COMMENTS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:comment w:id="0"><w:p><w:r><w:t>Uncapped is too risky; propose a cap.</w:t></w:r></w:p></w:comment>
</w:comments>"""


@pytest.mark.parametrize(
    "quote,found",
    [
        ("survive for a period of two (2) years", "¶2"),  # tracked changes accepted
        ("survive for a period of five (5) years", "¶2"),  # ... and rejected
        ("survive for a period of ten (10) years", None),
        ("OBLIGATIONS SURVIVE … the Recipient's receipt of notice.", "¶2"),  # case, quotes, ellipsis
        ("receipt of notice … Obligations survive", None),  # order matters
        ("1. Term. Obligations survive", "¶1"),  # spans paragraphs
        ("Uncapped is too risky", "¶1"),  # counsel comment
        ("the ?Recipient’s? receipt", "¶2"),  # PDF-style "?" for quote marks
    ],
)
def test_locate_in_docx(tmp_path, quote, found):
    path = tmp_path / "nda.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", DOCX)
        z.writestr("word/comments.xml", COMMENTS)
    assert evidence.locate(path, quote) == found


def test_overlaps():
    assert evidence.overlaps("for a period of two (2) years; provided, recipient", CLAUSE)
    assert not evidence.overlaps("governed by the laws of Delaware", CLAUSE)
