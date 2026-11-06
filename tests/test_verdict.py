from pathlib import Path

from cqa.graders import verdict
from cqa.schema import Citation, Evidence, Field, Question, Revision

REV = Revision(Path("documents/d/r01__a.docx"))
CLAUSE = "survive termination for a period of two (2) years; provided, recipient's obligations"
Q = Question("X", "synthetic", True, "t", "p", (REV,), (Field("x", "bool"),), {"x": True}, (Evidence(REV, CLAUSE),))


def cite(found=True, controlling=True):
    return Citation("a.docx", CLAUSE if controlling else "some other text", "¶1" if found else None, controlling)


def test_wrong_answer_rejects_even_with_good_citations():
    v, reason = verdict(Q, {"x": False}, (cite(),))
    assert v == "REJECT" and "controlling" in reason


def test_right_answer_with_controlling_citation_accepts():
    assert verdict(Q, {"x": True}, (cite(),))[0] == "ACCEPT"


def test_right_answer_with_fabricated_quote_escalates():
    v, reason = verdict(Q, {"x": True}, (cite(), cite(found=False, controlling=False)))
    assert v == "ESCALATE" and "not found" in reason


def test_right_answer_without_controlling_clause_escalates():
    assert verdict(Q, {"x": True}, (cite(controlling=False),))[0] == "ESCALATE"
    assert verdict(Q, {"x": True}, ())[0] == "ESCALATE"


def test_no_expert_evidence_accepts_on_answer():
    q = Question("X", "synthetic", True, "t", "p", (REV,), (Field("x", "bool"),), {"x": True})
    assert verdict(q, {"x": True}, ())[0] == "ACCEPT"
