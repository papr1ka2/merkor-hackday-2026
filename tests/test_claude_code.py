import json
import stat
import sys
from pathlib import Path

import pytest

from verdict.agent import AgentError
from verdict.claude_code import ClaudeCodeAgent, audit
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
elif mode == "crash":
    print("boom", file=sys.stderr)
    sys.exit(2)
'''


@pytest.fixture
def run(tmp_path, monkeypatch):
    path = tmp_path / "claude"
    path.write_text(FAKE.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-be-stripped")
    doc = tmp_path / "r03__stored.docx"
    doc.write_bytes(b"raw")

    def run(mode, **kw):
        monkeypatch.setenv("FAKE_MODE", mode)
        agent = ClaudeCodeAgent(claude_bin=kw.pop("claude_bin", str(path)), **kw)
        return agent.answer("Is it capped?", [(doc, "Contract (v3).docx")], AnswerType("bool"))

    return run


def test_success(run):
    out = run("ok")
    assert out["answer"] is True and out["citations"][0]["file"] == "Contract (v3).docx"
    traj = out["trajectory"]
    assert traj[0]["type"] == "command"
    init = traj[1]["event"]
    assert init["cwd_files"] == ["Contract (v3).docx"]  # only the cited file, original name
    assert init["schema_keys"] == ["answer", "citations", "explanation"]
    assert [e["event"]["type"] for e in traj[1:]] == ["system", "assistant", "result"]


@pytest.mark.parametrize(
    "mode,msg",
    [("error_result", "error_max_turns"), ("crash", "boom"),
     ("text_json", "no structured output")],  # JSON in the result text is not schema-validated
)
def test_failures_keep_trajectory(run, mode, msg):
    with pytest.raises(AgentError, match=msg) as err:
        run(mode)
    assert [err.value.trajectory[0]["type"], err.value.trajectory[-1]["type"]] == ["command", "error"]


def test_missing_binary_is_an_agent_error(run, tmp_path):
    with pytest.raises(AgentError):
        run("ok", claude_bin=str(tmp_path / "nope"))


def test_isolation_settings(run, tmp_path):
    repo = tmp_path / "repo"
    argv = run("ok", deny_read=[repo])["trajectory"][0]["argv"]
    s = json.loads(argv[argv.index("--settings") + 1])
    assert s["sandbox"] == {
        "enabled": True,
        "failIfUnavailable": True,
        "allowUnsandboxedCommands": False,
        "filesystem": {"denyRead": [str(repo.resolve())]},
        "network": {"allowedDomains": []},
    }
    assert s["permissions"]["deny"] == [f"Read(/{repo.resolve().as_posix()}/**)", "WebFetch", "WebSearch"]
    assert "--settings" not in run("ok", isolate=False)["trajectory"][0]["argv"]


def test_audit_flags_reaching_for_denied_paths():
    def call(name, **inp):
        return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}

    work, repo = Path("/Users/me/run/work"), Path("/Users/me/repo")
    events = [
        call("Read", file_path=f"{work}/contract.docx"),
        call("Bash", command="python3 -c \"W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'\""),
        call("Bash", command=f"python3 -c \"open('{repo}/dataset/questions.yaml')\""),
        call("Bash", command="python3 -c \"import urllib.request\""),
        {"type": "result", "permission_denials": [{"tool_name": "Grep", "tool_input": {"path": str(repo)}}]},
    ]
    flags = audit(events, work, [repo])
    assert not any("contract.docx" in f or "openxmlformats" in f for f in flags)  # own files, XML namespace
    assert any("answer key" in f for f in flags)
    assert any("network" in f and "urllib" in f for f in flags)
    assert any(f.startswith("denied Grep") for f in flags)
