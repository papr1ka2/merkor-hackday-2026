import pytest

from verdict.loader import DataError, load
from verdict.report import unfound_evidence

from .conftest import REPO_DATASET


def question(files="[documents/d/r01__a.docx]", extra="", provenance="  source: synthetic\n  reviewed: true\n"):
    return f"- id: X\n{provenance}  title: t\n  prompt: p\n  files: {files}\n{extra}"


def test_repo_dataset_loads_and_evidence_quotes_exist():
    ds = load(REPO_DATASET)
    assert ds.questions and ds.documents
    assert unfound_evidence(ds) == []
    assert {q.source for q in ds.questions} == {"expert"}  # no question was written by Claude


def test_valid_dataset(make_dataset):
    docs = {"msa": ["r02__MSA (v2).docx", "r01__MSA.docx"], "cuad/Supply/Acme": ["r01__Acme.pdf"]}
    qs = question("[documents/msa/r02__MSA (v2).docx]", "  expected: {type: date, value: 2026-01-31}\n")
    qs += question("[documents/msa/r01__MSA.docx]").replace("id: X", "id: Y")
    ds = load(make_dataset(docs, qs))

    assert set(ds.documents) == {"msa", "cuad/Supply/Acme"}
    r1, r2 = ds.documents["msa"].revisions
    assert (r1.number, r1.filename, r2.number) == (1, "MSA.docx", 2)
    x, y = ds.questions
    assert x.files == (r2,) and x.answer_type.kind == "date"
    assert x.expected == "2026-01-31"  # YAML date normalized to an ISO string
    assert y.deferred and not x.deferred


@pytest.mark.parametrize(
    "docs,questions,msg",
    [
        ({"d": ["r01__a.docx", "r03__b.docx"]}, "[]", "no gaps"),
        ({"d": ["contract.docx"]}, "[]", "rNN__"),
        ({"d": ["r01__a.docx"], "d/sub": ["r01__b.docx"]}, "[]", "no subfolders"),
        (None, question("[documents/d/r09__nope.docx]"), "file not found"),
        (None, question(extra="  evidence:\n    - {file: documents/d/r02__b.docx, quote: hi}\n"), "evidence file"),
        (None, question(provenance="  reviewed: false\n"), "source must be"),
        (None, question(provenance="  source: claude\n  reviewed: false\n"), "source must be"),
        (None, question(provenance="  source: expert\n"), "reviewed must be"),
        (None, question(extra="  expected: {type: bool, value: maybe}\n"), "bool value"),
        (None, question(extra="  expected: {type: number, value: lots}\n"), "number value"),
        (None, question(extra="  expected: {type: date, value: soon}\n"), "date value"),
        (None, question(extra="  expected: {type: choice, choices: [X], value: Y}\n"), "not in choices"),
        (None, question(extra="  expected: {type: text, value: hi}\n"), "type must be"),
        (None, question(extra="  expected: true\n"), "one answer"),
    ],
)
def test_invalid_dataset(make_dataset, docs, questions, msg):
    with pytest.raises(DataError, match=msg):
        load(make_dataset(docs or {"d": ["r01__a.docx", "r02__b.docx"]}, questions))
