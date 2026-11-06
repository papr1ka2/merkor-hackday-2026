# VERDICT (by Q.E.D. Guys)

A contract QA benchmark. An agent gets contract files and one question, answers with a typed value plus verbatim quotes, and is graded deterministically against expert answers. No LLM judge.

## Run

```sh
uv sync
uv run pytest                        # offline tests
uv run verdict check                 # validate dataset/, verify expert evidence quotes
uv run verdict run                   # all graded questions
uv run verdict run -q A.1 -q B       # some questions
uv run verdict run --source expert   # only expert questions
```

| `--agent` | runs | needs |
|---|---|---|
| `claude-code` (default) | Claude Code headless (`claude -p`) | `claude` logged in; uses your Pro/Max subscription |
| `claude-api` | Anthropic API, code-execution sandbox | `ANTHROPIC_API_KEY` |

| option | default |
|---|---|
| `--model` | `opus` (claude-code); `claude-opus-5-5` or `$VERDICT_MODEL` (claude-api) |
| `--effort low\|medium\|high\|xhigh\|max` | `high` |
| `--workers N` | 4 (lower it if you hit subscription rate limits) |
| `--runs-dir DIR` | `runs` |
| `--no-isolation` | off (claude-code only, see below) |


## Isolation

`claude-api` only sees the uploaded files, in Anthropic's sandbox.

`claude-code`:
- Each question runs in a temp dir holding copies of only the cited files.
- Tools: Read, Grep, Glob, Bash (`python3` with `pypdf`, `unzip`). No web tools, MCP servers, user/project settings or saved sessions.
- API-key env vars are removed, so it always runs on your subscription.
- Claude Code's sandbox is on and mandatory (macOS, Linux, WSL2; Linux needs `bubblewrap` and `socat`; native Windows is refused).
- The repo (answer key, git history) and the runs dir are unreadable to its tools and shell, including `python3`. Shell commands have no network.
- Tool calls are audited after each run; anything reaching outside the workdir is flagged in the report.
- `--no-isolation` turns the sandbox and deny rules off.

## Output

Each run writes `runs/<UTC timestamp>/` (git-ignored):

| file | contents |
|---|---|
| `run.json` | agent, model, effort, isolation, git commit, question ids, start/end time |
| `results.jsonl` | per question: verdict, reason, answer, correct?, citations, explanation, error, audit flags |
| `trajectories.jsonl` | per question: everything the agent did (API responses or Claude Code stream-json events), incl. on error |
| `report.md` | summary table and per-question details |

## Dataset

```
dataset/
  questions.yaml
  SOURCES.md                                   # provenance, licenses
  negotiation/<matter>.md                      # background timelines (not given to the agent)
  documents/anonymized-demo-contracts/<doc>/rNN__<original filename>
  documents/cuad/<category>/<contract>/r01__<original filename>.pdf
```

- A document is a folder of `rNN__` files; `rNN` orders its revisions (r01, r02, … with no gaps).
- The agent sees the original filename, without the `rNN__` prefix.

`questions.yaml`, one entry per question with one answer:

```yaml
- id: A.1
  split_from: A                 # optional: split from a multi-part question
  source: expert                # expert | synthetic
  reviewed: false               # has an expert checked expected + evidence?
  title: ClientCo–AuditCo MSA
  prompt: Is the agreement still in force on April 1, 2027 under the HL Draft 3.2.26 version?
  files:                        # the agent gets exactly these
    - documents/anonymized-demo-contracts/clientco_msa/r01__....docx
  expected: {type: bool, value: true}
  evidence:                     # controlling language a correct answer should cite
    - file: documents/anonymized-demo-contracts/clientco_msa/r01__....docx
      quote: will automatically renew for one (1) year terms thereafter
  answer: ...                   # for humans; also basis, trap(s), notes
```

| `expected.type` | `value` | answer graded as |
|---|---|---|
| `bool` | `true` / `false` | exact (`"yes"`/`"no"` accepted) |
| `number` | number | exact (one number in a string, e.g. `"$1,000"`, accepted) |
| `date` | `YYYY-MM-DD` | same date |
| `choice` | one of `choices` | case-insensitive |

No `expected` = not graded yet.

## Grading

The agent submits:

```json
{"answer": true,
 "citations": [{"file": "<filename>", "quote": "<verbatim text>"}],
 "explanation": "..."}
```

| answer | citations | verdict |
|---|---|---|
| wrong (or agent error) | any | REJECT |
| right | a quote isn't in the file | ESCALATE |
| right | no quote overlaps `evidence` | ESCALATE |
| right | quotes found, one overlaps `evidence` | ACCEPT |
| right | question has no `evidence` | ACCEPT |

- Quote matching ignores case, quote style, dashes and whitespace; `…` skips words.
- A `.docx` quote matches with tracked changes accepted or rejected.
- "Overlaps" = 40+ shared characters.
- Agent errors are flagged in the report.

## Where the data comes from

| questions | contracts | questions and answers |
|---|---|---|
| A–AC | `anonymized-demo-contracts/` | from the team's actual legal interactions on these contracts |
| CUAD-A–D | `cuad/` | written by the team on demo day after reviewing each contract with legal expertise; no answers yet, so not graded |

- Multi-part questions are split into one-answer entries (`A.1`, `A.2`, …).
- `reviewed: false` on every entry until an expert has checked the final entries.

## Code

| `src/verdict/` | does |
|---|---|
| `schema.py` | data types |
| `loader.py` | reads and validates `dataset/` |
| `agent.py` | `ClaudeAgent` (API, code-execution sandbox + `submit_answer` tool) |
| `claude_code.py` | `ClaudeCodeAgent` (`claude -p` with `--json-schema`) |
| `llm.py` | the only Claude API call |
| `graders.py` | answer grading, citation checks, verdict |
| `evidence.py` | finds quotes in `.docx` / `.pdf` (grader only) |
| `runner.py` | runs the agent per question |
| `report.py` | report, run folder |
| `cli.py` | `verdict check`, `verdict run` |

## How to add data or agents

**Add a contract**
1. Put it at `dataset/documents/<group>/<document>/r01__<original filename>`.*
2. A later revision of the same contract goes in the same folder as `r02__…`, `r03__…` (no gaps).
3. Note where it came from in `dataset/SOURCES.md`.

**Add a question**
1. Append an entry to `dataset/questions.yaml` (format above): one question, one `expected` answer.
2. List in `files` exactly the revisions the agent should get.
3. Add `evidence`: verbatim quotes of the controlling language from those files.
4. Set `source` and `reviewed`.
5. Run `uv run verdict check`. It fails if a path is wrong, `expected` is malformed, or an evidence quote isn't in its file.

**Add an agent**

```python
from verdict import loader, report, runner

class MyAgent:
    def answer(self, prompt, files, answer_type):
        # files: [(path on disk, filename to show)]; answer_type.kind / answer_type.choices
        return {"answer": ..., "citations": [{"file": "<filename>", "quote": "<verbatim>"}], "explanation": "..."}

ds = loader.load("dataset")
print(report.render(ds, runner.run(ds, MyAgent())))
```

Optional return keys: `trajectory` (list of events) and `audit` (list of flags). Raise `verdict.agent.AgentError(msg, trajectory)` to keep a partial trajectory on failure.

\* The built-in agents send the cited contracts to Anthropic. Only add contracts that are anonymized, public, or that you're otherwise allowed to share.
