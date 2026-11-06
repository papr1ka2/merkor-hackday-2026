import json

import pytest

from verdict import report, runner
from verdict.agent import AgentError
from verdict.loader import load

from .conftest import REPO_DATASET


@pytest.fixture(scope="module")
def ds():
    return load(REPO_DATASET)


class Agent:
    """Answers each prompt with fn(question), where the question comes from questions.yaml."""

    def __init__(self, ds, fn):
        self.by_prompt, self.fn = {q.prompt: q for q in ds.questions}, fn

    def answer(self, prompt, files, answer_type):
        assert all(path.exists() and not name.startswith("r0") for path, name in files)
        return self.fn(self.by_prompt[prompt])


def oracle(q):
    cites = [{"file": ev.file.filename, "quote": ev.quote} for ev in q.evidence]
    return {"answer": q.expected, "citations": cites, "explanation": "oracle"}


def test_expected_answers_and_evidence_are_accepted_everywhere(ds):
    results = runner.run(ds, Agent(ds, oracle), workers=1)
    assert len(results) == sum(not q.deferred for q in ds.questions)
    assert [(r.question_id, r.reason) for r in results if r.verdict != "ACCEPT"] == []
    assert runner.run(ds, Agent(ds, oracle), source="synthetic") == []


def test_fabricated_quote_escalates_and_empty_submission_rejects(ds):
    q = next(q for q in ds.questions if not q.deferred and q.evidence)
    fake = {"file": q.files[0].filename, "quote": "the parties agree to exchange one ceremonial goat"}
    sub = lambda x: {"answer": x.expected, "citations": [fake]} if x is q else {}
    results = runner.run(ds, Agent(ds, sub), workers=1)
    [r] = [r for r in results if r.question_id == q.id]
    assert r.verdict == "ESCALATE" and r.answer_correct
    assert "NOT FOUND" in report.render(ds, [r])
    assert {r.verdict for r in results if r.question_id != q.id} == {"REJECT"}


def test_run_folder_records_results_errors_and_trajectories(ds, tmp_path):
    ok = next(q for q in ds.questions if not q.deferred)

    def sub(q):
        if q is ok:
            return {**oracle(q), "trajectory": [{"type": "note", "text": "hello"}]}
        raise AgentError("boom", [{"type": "note", "text": "so far"}])

    results = runner.run(ds, Agent(ds, sub), workers=1)
    failed = [r for r in results if r.question_id != ok.id]
    assert failed and all(r.verdict == "REJECT" and "boom" in r.error for r in failed)

    run_dir = tmp_path / "run"
    report.write_run(run_dir, ds, results, {"model": "fake"})
    assert json.loads((run_dir / "run.json").read_text()) == {"model": "fake"}
    rows = [json.loads(line) for line in (run_dir / "results.jsonl").read_text().splitlines()]
    assert len(rows) == len(results) and all("trajectory" not in row for row in rows)
    trajs = {
        t["question_id"]: t["trajectory"]
        for t in map(json.loads, (run_dir / "trajectories.jsonl").read_text().splitlines())
    }
    assert trajs[ok.id] == [{"type": "note", "text": "hello"}]
    assert trajs[failed[0].question_id] == [{"type": "note", "text": "so far"}]  # kept on failure
    md = (run_dir / "report.md").read_text()
    assert md.startswith("# Results") and "WARNING" in md
