from pathlib import Path

import pytest

from cqa.loader import DataError, load

from .conftest import REPO_DATASET

QUESTIONS = """
- id: X
  title: t
  prompt: p
  files: [documents/msa/r02__MSA (v2).docx]
  expected:
    cap_usd: {type: number, value: 100}
    renews: {type: bool, value: true}
    ends: {type: date, value: 2026-01-31}
    law: {type: choice, choices: [NY, DE], value: DE}
- id: Y
  title: deferred one
  prompt: p
  files: [documents/msa/r01__MSA.docx]
"""


def test_repo_dataset_loads():
    ds = load(REPO_DATASET)
    assert ds.questions and ds.documents
    for q in ds.questions:
        assert q.files
        assert set(q.expected) == {f.key for f in q.fields}


def test_revisions_and_questions(make_dataset):
    ds = load(make_dataset({"msa": ["r01__MSA.docx", "r02__MSA (v2).docx"]}, QUESTIONS))
    msa = ds.documents["msa"]
    r1, r2 = msa.revisions
    assert (r1.number, r1.filename, r1.document_id) == (1, "MSA.docx", "msa")
    assert msa.latest == r2 and msa.previous(r2) == r1 and msa.previous(r1) is None

    x, y = ds.questions
    assert x.files == (r2,)
    assert [f.type for f in x.fields] == ["number", "bool", "date", "choice"]
    assert x.expected["ends"] == "2026-01-31"  # YAML date normalized to ISO string
    assert y.deferred and not x.deferred


def test_revisions_sort_numerically(make_dataset):
    names = [f"r{i:02d}__v.docx" for i in (3, 1, 2)]
    ds = load(make_dataset({"d": names}, "[]"))
    assert [r.number for r in ds.documents["d"].revisions] == [1, 2, 3]


@pytest.mark.parametrize(
    "docs,msg",
    [
        ({"d": ["r01__a.docx", "r03__b.docx"]}, "no gaps"),
        ({"d": ["contract.docx"]}, "rNN__"),
    ],
)
def test_bad_document_layout(make_dataset, docs, msg):
    with pytest.raises(DataError, match=msg):
        load(make_dataset(docs, "[]"))


@pytest.mark.parametrize(
    "expected,msg",
    [
        ("a: {type: bool, value: maybe}", "bool value"),
        ("a: {type: number, value: lots}", "number value"),
        ("a: {type: date, value: soon}", "date value"),
        ("a: {type: choice, choices: [X], value: Y}", "not in choices"),
        ("a: {type: text, value: hi}", "type must be"),
        ("a: true", "type: ..., value"),
    ],
)
def test_bad_expected(make_dataset, expected, msg):
    q = f"- id: X\n  title: t\n  prompt: p\n  files: [documents/d/r01__a.docx]\n  expected:\n    {expected}\n"
    with pytest.raises(DataError, match=msg):
        load(make_dataset({"d": ["r01__a.docx"]}, q))


def test_unknown_file_reference(make_dataset):
    q = "- id: X\n  title: t\n  prompt: p\n  files: [documents/d/r09__nope.docx]\n"
    with pytest.raises(DataError, match="file not found"):
        load(make_dataset({"d": ["r01__a.docx"]}, q))


def test_evidence_must_cite_a_question_file(make_dataset):
    q = (
        "- id: X\n  title: t\n  prompt: p\n  files: [documents/d/r01__a.docx]\n"
        "  evidence:\n    - {file: documents/d/r02__b.docx, quote: hello}\n"
    )
    with pytest.raises(DataError, match="evidence file"):
        load(make_dataset({"d": ["r01__a.docx", "r02__b.docx"]}, q))


def test_repo_evidence_quotes_exist_in_files():
    from cqa.report import unfound_evidence

    assert unfound_evidence(load(REPO_DATASET)) == []
