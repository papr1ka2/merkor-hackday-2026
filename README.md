# cqa: contract QA benchmark

Tests whether an agent understands a contract. For each contract we have a fixed question set
and expert answers. Redlined versions of the contract have their own expert answers, so we can
check that the agent **changes** the answers a redline should change and **keeps** the rest.

## Quick start

```sh
uv sync
uv run pytest                       # offline tests
uv run cqa check data/contracts     # validate data, list what each redline changes
export ANTHROPIC_API_KEY=...
uv run cqa run data/contracts --out results.jsonl
```

`cqa run` options: `--family ID` (repeatable), `--effort low|medium|high|xhigh|max`, `--workers N`.
Set `CQA_MODEL` to override the model (default `claude-opus-5-5`).

## Data layout

```
data/contracts/<family>/
  questions.yaml          # shared by every version of this contract
  v0/contract.md          # base contract (v0 is required)
  v0/answers.yaml         # complete expert answer key
  v1/contract.md          # a redlined version, full text
  v1/answers.yaml         # complete, self-contained answer key
  ...
```

`questions.yaml`:

```yaml
questions:
  - id: liability_cap_months
    text: The general liability cap equals the fees paid or payable over how many months?
    type: number            # bool | choice | number | date | text
  - id: governing_law
    text: Which jurisdiction's law governs the agreement?
    type: choice
    choices: [New York, Delaware, California, Other]
```

`answers.yaml` maps every question id to the expert answer: `true`/`false` for bool, one of the choices,
a number, `YYYY-MM-DD`, or free text. The loader rejects answer files with a missing or extra id, or with a value of the wrong type.

To add a redline, copy the previous version's folder, edit `contract.md`, and update `answers.yaml`.
Then run `cqa check` to confirm the answer changes match what the redline was meant to change.

## Grading

| type | how |
|---|---|
| bool | normalizes yes/no/true/false |
| choice | case-insensitive exact match |
| number | extracts exactly one number from the answer ("24 months" works, "12 or 24" fails) |
| date | ISO date equality |
| text | LLM judge compares to the expert answer (only non-deterministic grader) |

Prefer structured types when writing questions; keep `text` for what can't be structured.

## Metrics

| metric | meaning |
|---|---|
| base | accuracy on `v0` |
| redlined | accuracy on all other versions |
| flip | on redlined versions, questions whose expert answer differs from `v0` |
| stability | on redlined versions, questions whose expert answer is the same as `v0` |

An agent that ignores redlines scores perfectly on stability and zero on flip.

Agent or judge failures (e.g. an API error) are scored as wrong, flagged in the `error` field, and
listed in a warning at the top of the report.

## Code

```
src/cqa/
  schema.py    data types (Question, Version, Family, Result)
  loader.py    data/ -> schema, with validation
  agent.py     Agent protocol, ClaudeAgent, StaticAgent (tests)
  llm.py       the only Claude API call site (structured JSON output)
  graders.py   one grader per question type; judge is injectable
  runner.py    runs agent over all versions, grades each answer
  report.py    metrics, markdown report, JSONL output
  cli.py       `cqa check` / `cqa run`
```

To test a different agent, implement `answer(contract: str, questions: list[Question]) -> {question_id: answer}`
and pass it to `runner.run`.
