# VERDICT internals

## Modules

```
src/verdict/
  cli.py          verdict check / verdict run
  loader.py       reads and validates dataset/
  agent.py        ClaudeAgent (API) and the agent interface
  claude_code.py  ClaudeCodeAgent (claude -p) and its sandbox settings
  llm.py          the only Claude API call
  runner.py       runs the agent per question
  graders.py      answer grading, citation checks, verdict
  evidence.py     finds quotes in .docx / .pdf (grader only)
  report.py       report and run folder
  schema.py       data types
```

A run: `cli` loads the dataset (`loader`), `runner` calls the agent once per graded question, `graders` checks the answer and the citations, `report` writes the run folder.

## The agents

Both get the question prompt, the cited files, and the answer type (never the expected answer or the evidence). Both return `{"answer", "citations", "explanation", "trajectory"}`.

| | `ClaudeAgent` (`agent.py`) | `ClaudeCodeAgent` (`claude_code.py`) |
|---|---|---|
| runs | Anthropic API (`llm.py`) | `claude -p` subprocess |
| files | uploaded to the API's code-execution sandbox | copied into a temp workdir |
| answer | strict `submit_answer` tool built from the answer type | `--json-schema` with the same schema |
| trajectory | every API response | Claude Code's stream-json events |
| billing | `ANTHROPIC_API_KEY` | your Claude Code login; API-key env vars are removed |

## Keeping the answers hidden

The answer key lives in this repo, so the agent must not be able to read it.

- **`ClaudeAgent`** only sees the files uploaded for that question, in Anthropic's sandbox. It has no access to your machine.
- **`ClaudeCodeAgent`** runs on your machine, so each question is locked down:
  - It works in a temp folder holding copies of only the cited files.
  - Claude Code's sandbox is mandatory (`--settings`, see `isolation_settings`): the repo (answer key, git history) and the runs folder can't be read by any of its tools or by `python3`, and its shell has no network. If the sandbox is unavailable, `claude` exits instead of running unsandboxed.
  - Its only tools are Read, Grep, Glob and Bash (`python3` with `pypdf`, `unzip`). No web tools, MCP servers or user settings.
  - Its `python3` is the base interpreter (outside the repo) with a private copy of `pypdf`.
  - Every tool call is checked after the run (`audit`); anything reaching outside its folder is flagged in the report.
  - Works on macOS, Linux and WSL2 (Linux needs `bubblewrap` and `socat`). Refuses to run on native Windows.
  - `--no-isolation` turns this off. Don't use it for real runs.

## Quote matching (`evidence.py`)

- The grader reads text out of the files; the agents never use this.
- Text is compared ignoring case, quote style, dashes and whitespace; `…` in a quote skips words.
- A `.docx` is read twice, with tracked changes accepted and rejected; a quote may match either.
- A `.pdf` is read with two extraction modes, since one can scramble reading order.
- A citation "matches" the expert evidence if they share 40+ characters.
