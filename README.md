# cqa: contract QA benchmark

An agent gets contract files and one question, and answers with a typed value plus quotes.
We grade it against expert answers. No LLM judge.

## Run

```sh
uv sync
uv run pytest                    # offline tests
uv run cqa check                 # validate dataset/, verify evidence quotes
export ANTHROPIC_API_KEY=...
uv run cqa run                   # all graded questions
uv run cqa run -q A.1 -q B       # some questions
uv run cqa run --source expert   # only expert questions
```

Options: `--effort low|medium|high|xhigh|max` (default `high`), `--workers N`, `--runs-dir DIR`.
Model: `CQA_MODEL` (default `claude-opus-5-5`).

## Output

Each run writes `runs/<UTC timestamp>/` (git-ignored):

| file | contents |
|---|---|
| `run.json` | model, effort, git commit, question ids, start/end time |
| `results.jsonl` | per question: verdict, reason, answer, correct?, citations, explanation, error |
| `trajectories.jsonl` | per question: files uploaded, request, every API response, errors |
| `report.md` | summary table and per-question details |

## Dataset

```
dataset/
  questions.yaml
  SOURCES.md                                         # provenance, licenses
  negotiation/<matter>.md                            # background timelines (not given to the agent)
  documents/anonymized-demo-contracts/<doc>/rNN__<original filename>
  documents/cuad/<category>/<contract>/r01__<original filename>.pdf
```

- A document is a folder of `rNN__` files. `rNN` orders its revisions.
- The agent sees the original filename (no `rNN__` prefix).

## questions.yaml

One entry = one question, one answer.

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

| `expected.type` | `value` | graded as |
|---|---|---|
| `bool` | `true` / `false` | exact |
| `number` | number | exact |
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
| wrong | any | REJECT |
| right | a quote isn't in the file | ESCALATE |
| right | no quote overlaps `evidence` | ESCALATE |
| right | quotes found, one overlaps `evidence` | ACCEPT |

- Quote matching ignores case, quote style, dashes and whitespace. `…` skips words.
- A `.docx` quote matches with tracked changes accepted or rejected.
- "Overlaps" = 40+ shared characters.
- No `evidence` on a question: graded on the answer only.
- Agent errors: REJECT, flagged in the report.

## Provenance

| questions | from | `reviewed` |
|---|---|---|
| A–Q | team Q&A index; Claude wrote `expected`/`evidence` from the expert answer | false |
| R | legal expert (Task E: answer, reasoning, evidence, traps) | false (split into R.1/R.2) |
| S–X, Y–AC | team | false |
| CUAD-A–D | legal expert; no answers yet | not graded |

Multi-part questions were split into single-answer entries (`A.1`, `A.2`, …) by Claude.
No questions in `questions.yaml` were written by Claude. Test fixtures live only in `tests/`.

## Code

| file | does |
|---|---|
| `schema.py` | data types |
| `loader.py` | reads and validates `dataset/` |
| `agent.py` | `ClaudeAgent` (code-execution sandbox + `submit_answer` tool), `StaticAgent` |
| `llm.py` | the only Claude API call |
| `graders.py` | answer grading, citation checks, verdict |
| `evidence.py` | finds quotes in `.docx` / `.pdf` (grader only) |
| `runner.py` | runs the agent per question |
| `report.py` | report, run folder |
| `cli.py` | `cqa check`, `cqa run` |

Custom agent: implement `answer(prompt, files, answer_type) -> {"answer", "citations", "explanation"}`
and pass it to `runner.run`.
