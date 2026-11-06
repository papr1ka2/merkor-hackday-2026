import json
from types import SimpleNamespace

import pytest

from verdict import llm, report, runner
from verdict.agent import AgentError, ClaudeAgent
from verdict.loader import load
from verdict.schema import AnswerType

from .conftest import REPO_DATASET


class FakeResponse(SimpleNamespace):
    def model_dump(self, mode="json"):
        return {"stop_reason": self.stop_reason, "content": [vars(b) for b in self.content]}


def response(stop_reason, *blocks):
    return FakeResponse(stop_reason=stop_reason, content=list(blocks), container=SimpleNamespace(id="c1"))


def block(type, **kw):
    return SimpleNamespace(type=type, **kw)


@pytest.fixture
def fake_api(monkeypatch, tmp_path):
    """Replace the Claude API with a scripted sequence of responses."""
    script, deleted, requests = [], [], []
    files = SimpleNamespace(
        upload=lambda file: SimpleNamespace(id=f"file_{file[0]}", filename=file[0]),
        delete=lambda fid: deleted.append(fid),
    )
    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(files=files))

    def create(**kwargs):
        requests.append(kwargs)
        item = script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(llm, "create", create)
    doc = tmp_path / "contract.docx"
    doc.write_bytes(b"raw")
    return SimpleNamespace(script=script, deleted=deleted, requests=requests, files=[(doc, "Contract.docx")])


NUMBER = AnswerType("number")
SUBMISSION = {"answer": 5, "citations": [], "explanation": "because"}


def test_records_every_turn_and_resumes_after_pause(fake_api):
    fake_api.script += [
        response("pause_turn", block("server_tool_use", name="code_execution")),
        response("end_turn", block("text", text="I think it's 5.")),
        response("tool_use", block("tool_use", name="submit_answer", input=SUBMISSION)),
    ]
    out = ClaudeAgent().answer("What is the cap?", fake_api.files, NUMBER)

    assert {k: out[k] for k in SUBMISSION} == SUBMISSION
    types = [e["type"] for e in out["trajectory"]]
    assert types == ["files", "request", "response", "response", "user", "response"]
    assert out["trajectory"][0]["files"] == [{"filename": "Contract.docx", "file_id": "file_Contract.docx"}]
    assert fake_api.requests[1]["container"] == "c1"  # resumed in the same sandbox
    assert fake_api.deleted == ["file_Contract.docx"]  # uploads cleaned up


def test_failure_keeps_partial_trajectory(fake_api):
    fake_api.script += [response("pause_turn"), RuntimeError("api down")]
    with pytest.raises(AgentError) as err:
        ClaudeAgent().answer("q", fake_api.files, NUMBER)
    assert [e["type"] for e in err.value.trajectory] == ["files", "request", "response", "error"]
    assert "api down" in err.value.trajectory[-1]["error"]
    assert fake_api.deleted == ["file_Contract.docx"]


def test_run_folder_contents(tmp_path):
    ds = load(REPO_DATASET)
    q = next(q for q in ds.questions if not q.deferred)

    class Agent:
        def answer(self, prompt, files, answer_type):
            if prompt == q.prompt:
                return {"answer": q.expected, "citations": [], "explanation": "x",
                        "trajectory": [{"type": "note", "text": "hello"}]}
            raise AgentError("boom", [{"type": "note", "text": "partial"}])

    results = runner.run(ds, Agent(), workers=1)
    run_dir = tmp_path / "run"
    report.write_run(run_dir, ds, results, {"model": "fake"})

    assert json.loads((run_dir / "run.json").read_text()) == {"model": "fake"}
    rows = [json.loads(l) for l in (run_dir / "results.jsonl").read_text().splitlines()]
    trajs = {json.loads(l)["question_id"]: json.loads(l) for l in (run_dir / "trajectories.jsonl").read_text().splitlines()}
    assert len(rows) == len(trajs) == len(results)
    assert all("trajectory" not in row for row in rows)
    assert trajs[q.id]["trajectory"] == [{"type": "note", "text": "hello"}]
    other = next(r.question_id for r in results if r.question_id != q.id)
    assert trajs[other]["trajectory"] == [{"type": "note", "text": "partial"}]  # kept on failure
    assert (run_dir / "report.md").read_text().startswith("# Results")
