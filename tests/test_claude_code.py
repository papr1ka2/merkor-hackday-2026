import json
import os
import stat
import sys

import pytest

from cqa.agent import AgentError
from cqa.claude_code import ClaudeCodeAgent
from cqa.schema import AnswerType

FAKE = '''#!{python}
import json, os, sys
argv = sys.argv[1:]
mode = os.environ["FAKE_MODE"]
assert "ANTHROPIC_API_KEY" not in os.environ, "API key must not reach claude -p"
schema = json.loads(argv[argv.index("--json-schema") + 1])
files = sorted(os.listdir("."))
print(json.dumps({{"type": "system", "subtype": "init", "cwd_files": files, "schema_keys": sorted(schema["properties"])}}))
print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "text", "text": "reading"}}]}}}}))
if mode == "ok":
    out = {{"answer": True, "citations": [{{"file": files[0], "quote": "q"}}], "explanation": "e"}}
    print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "structured_output": out}}))
elif mode == "text_json":
    out = {{"answer": 3, "citations": [], "explanation": "e"}}
    print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "result": json.dumps(out)}}))
elif mode == "error_result":
    print(json.dumps({{"type": "result", "subtype": "error_max_turns", "is_error": True}}))
elif mode == "no_output":
    print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "result": "not json"}}))
elif mode == "crash":
    print("boom", file=sys.stderr)
    sys.exit(2)
'''


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    path = tmp_path / "claude"
    path.write_text(FAKE.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-be-stripped")
    doc = tmp_path / "r03__stored.docx"
    doc.write_bytes(b"raw")
    return str(path), [(doc, "Contract (v3).docx")]


def run(fake_claude, mode, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", mode)
    bin_path, files = fake_claude
    return ClaudeCodeAgent(claude_bin=bin_path).answer("Is it capped?", files, AnswerType("bool"))


def test_success(fake_claude, monkeypatch):
    out = run(fake_claude, "ok", monkeypatch)
    assert out["answer"] is True and out["citations"][0]["file"] == "Contract (v3).docx"
    traj = out["trajectory"]
    assert traj[0]["type"] == "command" and traj[0]["files"] == ["Contract (v3).docx"]
    init = traj[1]["event"]
    assert init["cwd_files"] == ["Contract (v3).docx"]  # only the cited file, original name
    assert init["schema_keys"] == ["answer", "citations", "explanation"]
    assert [e["event"]["type"] for e in traj[1:]] == ["system", "assistant", "result"]


@pytest.mark.parametrize(
    "mode,msg",
    [("error_result", "error_max_turns"), ("crash", "boom"), ("no_output", "no structured output"),
     ("text_json", "no structured output")],  # JSON in the result text is not schema-validated
)
def test_failures_keep_trajectory(fake_claude, monkeypatch, mode, msg):
    with pytest.raises(AgentError, match=msg) as err:
        run(fake_claude, mode, monkeypatch)
    assert err.value.trajectory[0]["type"] == "command"
    assert err.value.trajectory[-1]["type"] == "error"


def test_missing_binary_is_an_agent_error(tmp_path):
    doc = tmp_path / "a.docx"
    doc.write_bytes(b"x")
    with pytest.raises(AgentError):
        ClaudeCodeAgent(claude_bin=str(tmp_path / "nope")).answer("q", [(doc, "a.docx")], AnswerType("bool"))
