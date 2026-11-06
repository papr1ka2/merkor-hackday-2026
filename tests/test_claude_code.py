import json
import os
import stat
import sys

import pytest

from verdict.agent import AgentError
from verdict.claude_code import ClaudeCodeAgent
from verdict.schema import AnswerType

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


def test_isolation_settings_block_repo_for_tools_shell_and_network(tmp_path):
    from verdict.claude_code import isolation_settings

    repo = tmp_path / "repo"
    s = isolation_settings([repo])
    assert s["sandbox"]["enabled"] and s["sandbox"]["failIfUnavailable"]
    assert s["sandbox"]["allowUnsandboxedCommands"] is False
    assert s["sandbox"]["filesystem"]["denyRead"] == [str(repo)]
    assert s["sandbox"]["network"]["allowedDomains"] == []
    assert f"Read(/{repo.as_posix()}/**)" in s["permissions"]["deny"]


def test_isolation_flag_controls_settings(fake_claude, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_MODE", "ok")
    bin_path, files = fake_claude
    on = ClaudeCodeAgent(claude_bin=bin_path, deny_read=[tmp_path]).answer("q", files, AnswerType("bool"))
    off = ClaudeCodeAgent(claude_bin=bin_path, isolate=False).answer("q", files, AnswerType("bool"))
    assert "--settings" in on["trajectory"][0]["argv"]
    assert "--settings" not in off["trajectory"][0]["argv"]


def test_audit_flags_reaching_for_denied_paths():
    from pathlib import Path

    from verdict.claude_code import audit

    def call(name, **inp):
        return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}

    events = [
        call("Read", file_path="/work/contract.docx"),
        call("Bash", command="python3 -c \"open('/repo/dataset/questions.yaml')\""),
        call("Bash", command="python3 -c \"import urllib.request\""),
        {"type": "result", "permission_denials": [{"tool_name": "Grep", "tool_input": {"path": "/repo"}}]},
    ]
    flags = audit(events, "/work", [Path("/repo")])
    assert not any("contract.docx" in f for f in flags)
    assert any("answer key" in f for f in flags)
    assert any("network" in f for f in flags)
    assert any(f.startswith("denied Grep") for f in flags)
