"""Turn results into a markdown report and JSONL."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from . import evidence
from .schema import Dataset, Result


def render(dataset: Dataset, results: list[Result]) -> str:
    questions = {q.id: q for q in dataset.questions}
    lines = ["# Results", ""]

    errors = [r for r in results if r.error]
    if errors:
        lines += [
            f"**WARNING: {len(errors)}/{len(results)} questions errored** (scored REJECT). "
            f"First ({errors[0].question_id}): `{errors[0].error}`",
            "",
        ]

    counts = Counter(r.verdict for r in results)
    n_ok = sum(r.answer_correct for r in results)
    lines.append(
        f"**{counts['ACCEPT']} ACCEPT · {counts['ESCALATE']} ESCALATE · {counts['REJECT']} REJECT** "
        f"of {len(results)} questions. Answers correct: {n_ok}/{len(results)}."
    )
    deferred = [q.id for q in dataset.questions if q.deferred]
    if deferred:
        lines.append(f"Deferred (free-text, not graded): {', '.join(deferred)}.")

    lines += ["", "| question | verdict | answer | quotes found | reason |", "|---|---|---|---|---|"]
    for r in results:
        found = sum(c.location is not None for c in r.citations)
        lines.append(
            f"| {r.question_id} | {r.verdict} | {'✓' if r.answer_correct else '✗'} "
            f"| {found}/{len(r.citations)} | {r.reason} |"
        )

    lines += ["", "## Details"]
    for r in results:
        q = questions[r.question_id]
        lines += ["", f"### {q.id}. {q.title}", "", f"**{r.verdict}**: {r.reason}", ""]
        if r.error:
            lines += [f"Error: `{r.error}`"]
            continue
        lines.append("| field | agent | expected | |")
        lines.append("|---|---|---|---|")
        for key, ok in r.fields_correct.items():
            lines.append(f"| {key} | {r.answer.get(key)!r} | {q.expected[key]!r} | {'✓' if ok else '✗'} |")
        if r.citations:
            lines += ["", "Agent citations:"]
            for c in r.citations:
                where = f"{c.file}:{c.location}" if c.location else f"{c.file}: NOT FOUND"
                tag = " (controlling)" if c.controlling else ""
                lines.append(f"- {'✓' if c.location else '✗'} `{where}`{tag}: \"{c.quote}\"")
        if q.evidence:
            lines += ["", "Expert controlling clauses:"]
            for ev in q.evidence:
                cited = any(c.controlling and evidence.overlaps(c.quote, ev.quote) for c in r.citations)
                loc = evidence.locate(dataset.abspath(ev.file), ev.quote) or "?"
                lines.append(f"- {'cited' if cited else 'not cited'} `{ev.file.filename}:{loc}`: \"{ev.quote}\"")
        if r.explanation:
            lines += ["", "Agent explanation:", "", "> " + r.explanation.replace("\n", "\n> ")]
    return "\n".join(lines) + "\n"


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


def unfound_evidence(dataset: Dataset) -> list[str]:
    """Expert evidence quotes that can't be found in their file (data errors)."""
    return [
        f"{q.id}: {ev.file.filename}: {ev.quote[:80]!r}"
        for q in dataset.questions
        for ev in q.evidence
        if not evidence.locate(dataset.abspath(ev.file), ev.quote)
    ]


def write_jsonl(results: list[Result], path: str | Path) -> None:
    with open(path, "w") as f:
        for r in results:
            row = {**asdict(r), "answer_correct": r.answer_correct}
            f.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")
