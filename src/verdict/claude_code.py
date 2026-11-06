"""Claude Code as the agent under test, run headless (`claude -p`) on the user's login.

Each question runs in a fresh temp dir holding copies of only the cited files. With isolation on,
Claude Code's sandbox is mandatory and `deny_read` (the repo and runs dir) is unreadable to both
tools and shell; the tool calls are also audited afterwards as a second check.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .agent import AgentError, submission_schema
from .schema import AnswerType

SYSTEM = (
    "You are a careful contract lawyer answering one question about the contract files in the "
    "current directory. Read the files directly, including tracked changes (insertions and "
    "deletions) in .docx files. Use python3 to read them: pypdf is installed for .pdf, and a "
    ".docx is a zip whose word/document.xml holds the text (w:ins / w:del mark tracked changes). "
    "Answer only from the files and "
    "the facts in the question, and support your answer with verbatim quotes of the controlling "
    "language. Do not modify or create files."
)
TOOLS = "Read,Grep,Glob,Bash"
# Read-only shell commands are allowed by default; python3 and unzip are not.
ALLOWED = ["Read", "Grep", "Glob", "Bash(python3 *)", "Bash(unzip *)"]
# Removed so claude -p never silently bills an API key instead of the subscription.
API_KEY_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


class ClaudeCodeAgent:
    def __init__(
        self,
        model: str = "opus",
        effort: str | None = None,
        max_turns: int = 50,
        timeout: int = 1800,
        claude_bin: str = "claude",
        deny_read: list[Path] | None = None,
        isolate: bool = True,
    ):
        self.isolate = isolate
        self.deny_read = [Path(p).resolve() for p in deny_read or []]
        self.model = model
        self.effort = effort
        self.max_turns = max_turns
        self.timeout = timeout
        self.claude_bin = claude_bin

    def answer(
        self, prompt: str, files: list[tuple[Path, str]], answer_type: AnswerType
    ) -> dict[str, Any]:
        names = [name for _, name in files]
        text = "Files:\n" + "\n".join(f"- {n}" for n in names) + f"\n\nQuestion:\n{prompt}"
        cmd = [
            self.claude_bin, "-p", text,
            "--output-format", "stream-json", "--verbose",
            "--json-schema", json.dumps(submission_schema(answer_type, names)),
            "--model", self.model,
            "--max-turns", str(self.max_turns),
            "--append-system-prompt", SYSTEM,
            "--tools", TOOLS,
            "--allowedTools", *ALLOWED,
            "--permission-mode", "dontAsk",
            "--setting-sources", "",
            "--strict-mcp-config",
            "--no-session-persistence",
        ]  # fmt: skip
        if self.isolate:
            cmd += ["--settings", json.dumps(isolation_settings(self.deny_read))]
        if self.effort:
            cmd += ["--effort", self.effort]
        trajectory: list[dict[str, Any]] = [
            {"type": "command", "argv": cmd[:2] + ["<prompt>"] + cmd[3:], "prompt": text, "files": names}
        ]
        with tempfile.TemporaryDirectory(prefix="verdict-") as tmp:
            work, lib = Path(os.path.realpath(tmp)) / "work", Path(os.path.realpath(tmp)) / "lib"
            work.mkdir()
            for path, name in files:
                shutil.copyfile(path, work / name)
            env = agent_env(lib)
            try:
                proc = subprocess.run(
                    cmd, cwd=work, env=env, capture_output=True, text=True, timeout=self.timeout
                )
            except (OSError, subprocess.TimeoutExpired) as e:
                trajectory.append({"type": "error", "error": repr(e)})
                raise AgentError(repr(e), trajectory) from e

        events = _parse_events(proc.stdout)
        trajectory += [{"type": "claude_code", "event": e} for e in events]
        flags = audit(events, str(work), self.deny_read)
        if flags:
            trajectory.append({"type": "audit", "flags": flags})
        if proc.stderr.strip():
            trajectory.append({"type": "stderr", "text": proc.stderr[-4000:]})

        result = next((e for e in reversed(events) if e.get("type") == "result"), None)
        if proc.returncode != 0 or result is None or result.get("is_error"):
            detail = (result or {}).get("subtype") or proc.stderr.strip()[-500:] or f"exit {proc.returncode}"
            trajectory.append({"type": "error", "error": detail})
            raise AgentError(f"claude -p failed: {detail}", trajectory)

        # Only the schema-validated output counts; JSON in the result text does not.
        submission = result.get("structured_output")
        if not isinstance(submission, dict):
            trajectory.append({"type": "error", "error": "no structured output in result"})
            raise AgentError("claude -p returned no structured output", trajectory)
        return {**submission, "trajectory": trajectory, "audit": flags}


def _parse_events(stdout: str) -> list[dict[str, Any]]:
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            obj = {"type": "unparsed", "text": line}
        events.append(obj if isinstance(obj, dict) else {"type": "unparsed", "value": obj})
    return events


def isolation_settings(deny_read: list[Path]) -> dict[str, Any]:
    """Mandatory sandbox (claude exits rather than run unsandboxed), no shell network, and
    deny_read blocked for shell commands (sandbox) and Read/Grep/Glob (permission rules)."""
    return {
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            "allowUnsandboxedCommands": False,
            "filesystem": {"denyRead": [str(p) for p in deny_read]},
            "network": {"allowedDomains": []},
        },
        "permissions": {
            "deny": [f"Read(/{p.as_posix()}/**)" for p in deny_read] + ["WebFetch", "WebSearch"],
        },
    }


def agent_env(lib: Path) -> dict[str, str]:
    """python3 must be the base interpreter, since the repo's .venv sits inside a denied path;
    pypdf is copied to a private lib dir for the same reason."""
    import pypdf

    shutil.copytree(Path(pypdf.__file__).parent, lib / "pypdf")
    env = {k: v for k, v in os.environ.items() if k not in API_KEY_VARS}
    python_bin = Path(os.path.realpath(sys.executable)).parent
    env["PATH"] = os.pathsep.join([str(python_bin), env.get("PATH", "")])
    env["PYTHONPATH"] = str(lib)
    return env


_ABS_PATH = re.compile(r"(?<![\w.])(/(?:Users|home|private|var|tmp|etc|Volumes|opt)/[^\s'\"]*)")
_NETWORK = re.compile(r"https?://|\b(?:curl|wget|urllib|requests|httpx|socket|git\s+clone|gh\s)\b", re.I)
_ANSWER_KEY = re.compile(r"questions\.ya?ml|results\.jsonl|trajectories\.jsonl|\.git\b", re.I)


def audit(events: list[dict[str, Any]], cwd: str, deny_read: list[Path]) -> list[str]:
    """Flags (recorded, not enforced) for tool calls reaching outside cwd, the network, or the answer key."""
    flags = []
    for e in events:
        if e.get("type") != "assistant":
            continue
        for block in (e.get("message") or {}).get("content") or []:
            if block.get("type") != "tool_use" or block.get("name") == "StructuredOutput":
                continue
            text = json.dumps(block.get("input"), ensure_ascii=False)
            outside = [m for m in _ABS_PATH.findall(text) if not m.startswith(cwd)]
            if outside:
                flags.append(f"{block['name']}: path outside workdir: {outside[0][:120]}")
            if _NETWORK.search(text):
                flags.append(f"{block['name']}: possible network use: {text[:120]}")
            if _ANSWER_KEY.search(text) or any(str(p) in text for p in deny_read):
                flags.append(f"{block['name']}: looks for the answer key: {text[:120]}")
    for e in events:
        if e.get("type") == "result":
            for d in e.get("permission_denials") or []:
                flags.append(f"denied {d.get('tool_name')}: {json.dumps(d.get('tool_input'))[:120]}")
    return flags
