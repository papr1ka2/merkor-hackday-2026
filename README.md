# cqa: contract QA benchmark

Tests whether an agent understands contracts and their redlines. Each question cites one or more
raw contract files (.docx with tracked changes, or .pdf). The agent gets exactly those files and
the question, and returns typed answer fields that are graded deterministically against the
expert answers in `dataset/questions.yaml`.

## Quick start

```sh
uv sync
uv run pytest            # offline tests
uv run cqa check         # validate dataset/, verify expert evidence quotes, show revision chains
export ANTHROPIC_API_KEY=...
uv run cqa run                                          # all gradable questions
uv run cqa run -q A -q B                                # just these
uv run cqa run --source expert                          # only the team's questions
```

Options: `--effort low|medium|high|xhigh|max` (default high), `--workers N`, `--runs-dir DIR`.
`CQA_MODEL` overrides the model (default `claude-opus-5-5`).

Every run writes `runs/<UTC timestamp>/` (git-ignored):

| file | contents |
|---|---|
| `run.json` | model, effort, git commit, question ids, start/end time |
| `results.jsonl` | one graded result per question: verdict, reason, answer, per-field correctness, citations (found? where? controlling?), explanation, error |
| `trajectories.jsonl` | one line per question: everything the agent did: uploaded files, the request, every API response (including code-execution steps), nudges, and the error if it failed |
| `report.md` | the markdown report |

## Dataset

```
dataset/
  SOURCES.md                           # where each set of documents came from, licenses
  questions.yaml
  documents/anonymized-demo-contracts/<document>/
    r01__<original filename>.docx      # oldest revision
    r02__<original filename>.docx      # next revision of the same document
  documents/cuad/<category>/<contract>/r01__<original filename>.pdf   # CUAD v1, 510 contracts
```

- A **document** is any folder of `rNN__` files; its id is its path under `documents/`. Its
  **revisions** are the files, ordered by the prefix. Folders holding only folders just group.
  The agent sees the original filename (prefix stripped), since questions refer to versions by name.
- To add a revision, drop the file in as the next `rNN__`. To add a document, add a folder.
- `anonymized-demo-contracts/` holds the team's anonymized contracts and redlines. `cuad/` holds the CUAD v1 contracts
  (CC BY 4.0, see `SOURCES.md`); no questions are written over them yet.

`questions.yaml`, one entry per question:

```yaml
- id: E
  source: expert                           # expert (team's Q&A) | synthetic (written by Claude)
  reviewed: false                          # has an expert checked expected/evidence?
  title: LabsCo–AuditCo master services agreement (February 9, 2026)
  prompt: What is the most AuditCo can recover from LabsCo, and is LabsCo's recovery capped?
  files:                                   # relative to dataset/; the agent gets exactly these
    - documents/anonymized-demo-contracts/labsco_msa/r01__2026-02-09 - AuditCo MSA.docx
  expected:                                # stage 1: typed answer fields
    max_auditco_recovery_usd: {type: number, value: 7500}
    labsco_recovery_is_capped: {type: bool, value: false}
  evidence:                                # stage 2: expert-annotated controlling language
    - file: documents/anonymized-demo-contracts/labsco_msa/r01__2026-02-09 - AuditCo MSA.docx
      quote: IN NO EVENT SHALL COMPANY BE LIABLE FOR … LOSS OF BUSINESS PROFITS
  answer: (expert's prose answer)          # for humans
  basis: (supporting contract text)        # for humans
  traps: [known wrong answers]             # for humans (also: notes)
```

Field types: `bool`, `number`, `date` (YYYY-MM-DD), `choice` (with `choices: [...]`). A question
with no `expected` is **not graded yet**: its answer is free text, or no expert answer exists yet. To check an
intermediate step of a calculation, add it as another `expected` field.

Answers live only in `questions.yaml`; no answer values appear in code or tests.

**Provenance.** All current questions are `source: expert`:
- A–Q: verbatim from the team's Q&A index; their `expected` fields and `evidence` quotes were
  derived by Claude from the expert answer and basis, hence `reviewed: false`.
- R: the legal expert's Task E (VentureCo SAFE), with their gold answer, reasoning, evidence and
  traps; `reviewed: true`.
- S–X: the team's instruction-fidelity and round-causation questions over the redline chains
  (with background timelines in `dataset/negotiation/`); `reviewed: false`.
- CUAD-A to CUAD-D: the legal expert's questions over CUAD contracts; no answers yet, so not graded. Questions Claude writes itself must be `source: synthetic`. The
made-up questions in `tests/` are fixtures in temporary datasets and never touch `questions.yaml`.

## Grading

The agent gets the prompt and the cited raw files, plus each answer field's key, type and allowed
choices (never the value, never the evidence). It submits:

```json
{"answer": {"max_auditco_recovery_usd": 7500, "labsco_recovery_is_capped": false},
 "citations": [{"file": "2026-02-09 - AuditCo MSA.docx", "quote": "IN NO EVENT SHALL ..."}],
 "explanation": "..."}
```

Two independent, deterministic checks:

- **Answer:** each field vs `expected` (numbers exact, dates by ISO date, choices case-insensitive).
- **Evidence:** each cited quote must exist in the cited file. Text is normalized, `…` may skip
  words, and a .docx matches with tracked changes either accepted or rejected. A citation is
  *controlling* if it shares 40+ characters with one of the expert `evidence` quotes.

| answer | evidence | verdict |
|---|---|---|
| wrong | anything | **REJECT** |
| right | a cited quote isn't in the file | **ESCALATE** |
| right | no controlling clause cited | **ESCALATE** |
| right | quotes found, at least one controlling | **ACCEPT** |

The explanation isn't graded; it appears in the report next to the answer, the citations
(✓/✗ with `file:¶N` locations), the expert's controlling clauses, and the verdict.

`ClaudeAgent` uploads the cited files into Claude's code-execution sandbox, lets it read them
(including tracked changes) however it likes, and takes its submission from a `submit_answer`
tool whose strict schema is built from the fields.

Agent failures (e.g. API errors) are REJECT and listed in a warning at the top of the report.

## Code

```
src/cqa/
  schema.py    Revision, Document, Field, Question, Dataset, Result
  loader.py    dataset/ -> schema, with validation
  agent.py     Agent protocol, ClaudeAgent, StaticAgent
  llm.py       the only Claude API call site
  graders.py   answer grading, citation checks, verdict
  evidence.py  grader-side text access: find quotes in .docx/.pdf
  runner.py    runs the agent on each gradable question, grades it
  report.py    markdown report (summary + per-question details), JSONL
  cli.py       `cqa check` / `cqa run`
```

To test another agent, implement
`answer(prompt, files: list[(abs_path, display_name)], fields) -> submission dict`
and pass it to `runner.run`.
