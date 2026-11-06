# cqa: contract QA benchmark

Tests whether an agent understands contracts and their redlines. Each question cites one or more
raw contract files (.docx with tracked changes, or .pdf). The agent gets exactly those files and
the question, and returns typed answer fields that are graded deterministically against the
expert answers in `dataset/questions.yaml`.

## Quick start

```sh
uv sync
uv run pytest            # offline tests
uv run cqa check         # validate dataset/, show each document's revision chain
export ANTHROPIC_API_KEY=...
uv run cqa run --out results.jsonl          # all gradable questions
uv run cqa run -q A -q B                    # just these
```

Options: `--effort low|medium|high|xhigh|max` (default high), `--workers N`. `CQA_MODEL` overrides
the model (default `claude-opus-5-5`).

## Dataset

```
dataset/
  questions.yaml
  documents/<document_id>/
    r01__<original filename>.docx      # oldest revision
    r02__<original filename>.docx      # next revision of the same document
```

- A **document** is a folder; its **revisions** are the files in it, ordered by the `rNN__` prefix.
  Nothing is read from inside the files; the directory is the source of truth. The agent sees
  the original filename (prefix stripped), since questions refer to versions by name.
- To add a revision, drop the file in as the next `rNN__`. To add a document, add a folder.

`questions.yaml`, one entry per question:

```yaml
- id: A
  title: ClientCo–AuditCo master services agreement (HL Draft 3.2.26 vs. HL Draft 3.18.26)
  prompt: Is the agreement still in force on April 1, 2027 under (i) ... and (ii) ...?
  files:                                   # relative to dataset/; the agent gets exactly these
    - documents/clientco_msa/r01__ClientCo - AUDITCO MSA - (HL Draft 3.2.26).docx
    - documents/clientco_msa/r06__....docx
  expected:                                # typed fields, graded deterministically
    in_force_under_v1: {type: bool, value: true}
    in_force_under_v2: {type: bool, value: false}
  answer: (expert's prose answer)
  basis: (supporting contract text)
  trap: (optional; a known wrong path)
```

Field types: `bool`, `number`, `date` (YYYY-MM-DD), `choice` (with `choices: [...]`). A question
with no `expected` is **deferred**: its answer is free text and it isn't graded yet.

Answers live only in `questions.yaml`; no answer values appear in code or tests.

## How grading works

The agent is told each field's key, type and allowed choices (never the value) and must
return a value per field. A question is correct only if every field is. Numbers compare exactly;
dates by ISO date; choices case-insensitively.

`ClaudeAgent` uploads the cited files into Claude's code-execution sandbox, lets it read them
(including tracked changes) however it likes, and takes its answer from a `submit_answer` tool
whose strict schema is built from the fields.

Agent failures (e.g. API errors) count as wrong and are listed in a warning at the top of the report.

## Code

```
src/cqa/
  schema.py    Revision, Document, Field, Question, Dataset, Result
  loader.py    dataset/ -> schema, with validation
  agent.py     Agent protocol, ClaudeAgent, StaticAgent
  llm.py       the only Claude API call site
  graders.py   per-field-type deterministic graders
  runner.py    runs the agent on each gradable question, grades it
  report.py    score, per-question table, misses, JSONL
  cli.py       `cqa check` / `cqa run`
```

To test another agent, implement
`answer(prompt, files: list[(abs_path, display_name)], fields) -> {field_key: value}`
and pass it to `runner.run`.
