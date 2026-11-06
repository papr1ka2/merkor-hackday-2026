from types import SimpleNamespace

import pytest

from verdict import llm
from verdict.agent import AgentError, ClaudeAgent
from verdict.schema import AnswerType


class FakeResponse(SimpleNamespace):
    def model_dump(self, mode="json"):
        return {"stop_reason": self.stop_reason}


def response(stop_reason, *blocks):
    return FakeResponse(stop_reason=stop_reason, content=list(blocks), container=SimpleNamespace(id="c1"))


SUBMISSION = {"answer": 5, "citations": [], "explanation": "because"}


@pytest.fixture
def fake_api(monkeypatch, tmp_path):
    """Replace the Claude API with a scripted sequence of responses."""
    api = SimpleNamespace(script=[], removed=[], requests=[])
    files = SimpleNamespace(
        upload=lambda file: SimpleNamespace(id=f"file_{file[0]}", filename=file[0]),
        delete=api.removed.append,
    )
    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(files=files))

    def create(**kwargs):
        api.requests.append(kwargs)
        item = api.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(llm, "create", create)
    doc = tmp_path / "contract.docx"
    doc.write_bytes(b"raw")
    api.answer = lambda: ClaudeAgent().answer("What is the cap?", [(doc, "Contract.docx")], AnswerType("number"))
    return api


def test_resumes_after_pause_and_nudges_after_end_turn(fake_api):
    fake_api.script += [
        response("pause_turn", SimpleNamespace(type="server_tool_use", name="code_execution")),
        response("end_turn", SimpleNamespace(type="text", text="I think it's 5.")),
        response("tool_use", SimpleNamespace(type="tool_use", name="submit_answer", input=SUBMISSION)),
    ]
    out = fake_api.answer()
    assert {k: out[k] for k in SUBMISSION} == SUBMISSION
    assert [e["type"] for e in out["trajectory"]] == ["files", "request", "response", "response", "user", "response"]
    assert fake_api.requests[1]["container"] == "c1"  # resumed in the same sandbox
    assert fake_api.removed == ["file_Contract.docx"]  # uploads cleaned up


def test_failure_keeps_partial_trajectory(fake_api):
    fake_api.script += [response("pause_turn"), RuntimeError("api down")]
    with pytest.raises(AgentError) as err:
        fake_api.answer()
    assert [e["type"] for e in err.value.trajectory] == ["files", "request", "response", "error"]
    assert "api down" in err.value.trajectory[-1]["error"]
    assert fake_api.removed == ["file_Contract.docx"]
