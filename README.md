# VERDICT (by Q.E.D. Guys)

A contract QA benchmark. An agent gets the contract files for one question, answers with a typed value plus verbatim quotes, and is graded against expert answers: ACCEPT, REJECT or ESCALATE. No LLM judge.

## Quick start

```sh
uv sync
uv run verdict check                 # validate the dataset
uv run verdict run -q B              # one question
uv run verdict run                   # all graded questions
```

Browse results, questions, contract files and agent trajectories in a local viewer:

```sh
uv run python web/server.py          # http://127.0.0.1:8000
```

Each run is also saved to `runs/<UTC timestamp>/` (`report.md` is readable as-is). `uv run pytest` runs the offline tests.

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
| `--no-isolation` | off; see [`src/README.md`](src/README.md#keeping-the-answers-hidden) |

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

| answer | citations | verdict |
|---|---|---|
| wrong, or the agent failed | any | REJECT |
| right | a quote isn't in the file | ESCALATE |
| right | no quote matches the expert `evidence` | ESCALATE |
| right | quotes are real and one matches the `evidence` | ACCEPT |
| right | the question has no `evidence` | ACCEPT |

How quotes are matched, how the agents work, and how they're kept from the answer key: [`src/README.md`](src/README.md).

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
src/verdict/                    # the benchmark code; see src/README.md
web/                            # local results viewer (server.py + static/)
tests/
```
