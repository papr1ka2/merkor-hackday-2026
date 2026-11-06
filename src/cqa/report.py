"""Turn results into a readable report and JSONL."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .schema import Dataset, Result


def render(dataset: Dataset, results: list[Result]) -> str:
    questions = {q.id: q for q in dataset.questions}
    lines = []

    errors = [r for r in results if r.error]
    if errors:
        lines += [
            f"WARNING: {len(errors)}/{len(results)} questions errored and are scored as wrong.",
            f"First error ({errors[0].question_id}): {errors[0].error}",
            "",
        ]

    ok = sum(r.correct for r in results)
    deferred = [q.id for q in dataset.questions if q.deferred]
    lines.append(f"Score: {ok}/{len(results)} questions correct" + (f" ({100 * ok / len(results):.1f}%)" if results else ""))
    if deferred:
        lines.append(f"Deferred (free-text, not graded): {', '.join(deferred)}")

    lines += ["", "| question | result | title |", "|---|---|---|"]
    for r in results:
        mark = "error" if r.error else "pass" if r.correct else "FAIL"
        lines.append(f"| {r.question_id} | {mark} | {questions[r.question_id].title} |")

    misses = [r for r in results if not r.correct and not r.error]
    if misses:
        lines += ["", "Misses:"]
        for r in misses:
            q = questions[r.question_id]
            for key, correct in r.fields_correct.items():
                if not correct:
                    lines.append(f"- {r.question_id}.{key}: expected {q.expected[key]!r}, got {r.got.get(key)!r}")
    return "\n".join(lines)


def render_documents(dataset: Dataset) -> str:
    """For `cqa check`: each document's revision chain and which questions cite each revision."""
    cited: dict[Path, list[str]] = {}
    for q in dataset.questions:
        for rev in q.files:
            cited.setdefault(rev.path, []).append(q.id)

    lines = []
    for doc in dataset.documents.values():
        lines.append(doc.id)
        for rev in doc.revisions:
            qs = cited.get(rev.path)
            lines.append(f"  r{rev.number:02d}  {rev.filename}" + (f"   <- {', '.join(qs)}" if qs else ""))
    return "\n".join(lines)


def write_jsonl(results: list[Result], path: str | Path) -> None:
    with open(path, "w") as f:
        for r in results:
            f.write(json.dumps({**asdict(r), "correct": r.correct}, default=str) + "\n")
