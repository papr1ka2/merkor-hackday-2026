# VERDICT (by Q.E.D. Guys)

A contract QA benchmark. An agent gets the contract files for one question, answers with a typed value plus verbatim quotes, and is graded against expert answers: ACCEPT, REJECT or ESCALATE. No LLM judge.

## Quick start

```sh
uv sync
uv run verdict check                 # validate the dataset
uv run verdict run -q B              # one question
uv run verdict run                   # all graded questions
```

Results land in `runs/<UTC timestamp>/report.md`. `uv run pytest` runs the offline tests.

## Running the benchmark

| `--agent` | runs | needs |
|---|---|---|
| `claude-code` (default) | Claude Code headless (`claude -p`) | `claude` logged in; runs on your Pro/Max subscription |
| `claude-api` | Anthropic API with a code-execution sandbox | `ANTHROPIC_API_KEY` |

| option | default |
|---|---|
| `-q ID` (repeatable) | all graded questions |
| `--source expert\|synthetic` | both |
| `--model` | `opus` (claude-code); `claude-opus-5-5` or `$VERDICT_MODEL` (claude-api) |
| `--effort low\|medium\|high\|xhigh\|max` | `high` |
| `--workers N` | 4 (lower it if you hit subscription rate limits) |
| `--runs-dir DIR` | `runs` |
| `--no-isolation` | off; see [Keeping the answers hidden](#keeping-the-answers-hidden) |

Each run writes `runs/<UTC timestamp>/` (git-ignored):

| file | contents |
|---|---|
| `report.md` | summary table, then per question: answer vs expected, citations, verdict, explanation |
| `results.jsonl` | one graded result per question |
| `trajectories.jsonl` | everything the agent did per question, including on errors |
| `run.json` | agent, model, effort, isolation, git commit, questions, start/end time |

## Adding data

**A contract**
1. Put it at `dataset/documents/<group>/<document>/r01__<original filename>`.*
2. A later revision of the same contract goes in the same folder as `r02__…`, `r03__…` (no gaps).
3. Note where it came from in `dataset/SOURCES.md`.

**A question:** append an entry to `dataset/questions.yaml`. One question, one answer:

```yaml
- id: A.1
  source: expert                # expert | synthetic
  reviewed: false               # has an expert checked expected + evidence?
  title: ClientCo–AuditCo MSA
  prompt: Is the agreement still in force on April 1, 2027 under the HL Draft 3.2.26 version?
  files:                        # the agent gets exactly these
    - documents/anonymized-demo-contracts/clientco_msa/r01__....docx
  expected: {type: bool, value: true}
  evidence:                     # controlling language a correct answer should quote
    - file: documents/anonymized-demo-contracts/clientco_msa/r01__....docx
      quote: will automatically renew for one (1) year terms thereafter
  answer: ...                   # optional, for humans; also basis, trap(s), notes, split_from
```

| `expected.type` | `value` | an answer counts as right if |
|---|---|---|
| `bool` | `true` / `false` | it matches (`"yes"`/`"no"` accepted) |
| `number` | a number | it matches exactly (`"$1,000"` accepted) |
| `date` | `YYYY-MM-DD` | same date |
| `choice` | one of `choices` | it matches, ignoring case |

Leave out `expected` and the question isn't graded yet. Then run `uv run verdict check`: it fails on a wrong path, a malformed `expected`, or an evidence quote that isn't in its file.

## Adding an agent

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

## How grading works

The agent submits `{"answer": …, "citations": [{"file", "quote"}], "explanation": …}`.

| answer | citations | verdict |
|---|---|---|
| wrong, or the agent failed | any | REJECT |
| right | a quote isn't in the file | ESCALATE |
| right | no quote matches the expert `evidence` | ESCALATE |
| right | quotes are real and one matches the `evidence` | ACCEPT |
| right | the question has no `evidence` | ACCEPT |

- Quotes are matched ignoring case, quote style, dashes and whitespace; `…` skips words.
- A `.docx` quote may come from the text with tracked changes accepted or rejected.
- A quote "matches" the evidence if they share 40+ characters.
- The explanation isn't graded; it's shown in the report.

## Keeping the answers hidden

The answer key lives in this repo, so the agent must not be able to read it.

- **`claude-api`** only sees the files uploaded for that question, in Anthropic's sandbox. It has no access to your machine.
- **`claude-code`** runs on your machine, so each question is locked down:
  - It works in a temp folder holding copies of only the cited files.
  - Claude Code's sandbox is mandatory: the repo (answer key, git history) and the runs folder can't be read by any of its tools or by `python3`, and its shell has no network.
  - Its only tools are Read, Grep, Glob and Bash (`python3` with `pypdf`, `unzip`). No web tools, MCP servers or your settings.
  - Every tool call is checked after the run; anything reaching outside its folder is flagged in the report.
  - Works on macOS, Linux and WSL2 (Linux needs `bubblewrap` and `socat`). Refuses to run on native Windows.
  - `--no-isolation` turns this off. Don't use it for real runs.

## Where the data comes from

| questions | contracts | questions and answers |
|---|---|---|
| A–AC | `anonymized-demo-contracts/` | from the team's actual legal interactions on these contracts |
| CUAD-A–D | `cuad/` (CUAD v1, CC BY 4.0) | written by the team on demo day after reviewing each contract with legal expertise; no answers yet, so not graded |

- Multi-part questions are split into one-answer entries (`A.1`, `A.2`, …).
- `reviewed: false` on every entry until an expert has checked it.
- Licenses and details: `dataset/SOURCES.md`.

## Project layout

```
dataset/
  questions.yaml
  SOURCES.md
  negotiation/<matter>.md       # background timelines, never given to the agent
  documents/anonymized-demo-contracts/<document>/rNN__<original filename>
  documents/cuad/<category>/<contract>/r01__<original filename>.pdf
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
