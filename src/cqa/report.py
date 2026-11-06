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
        lines.append(f"Not graded yet (no typed expected answer): {', '.join(deferred)}.")

    lines += [
        "",
        "| question | source | verdict | answer | quotes found | reason |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        q = questions[r.question_id]
        found = sum(c.location is not None for c in r.citations)
        source = q.source + ("" if q.reviewed else " (unreviewed)")
        lines.append(
            f"| {r.question_id} | {source} | {r.verdict} | {'✓' if r.answer_correct else '✗'} "
            f"| {found}/{len(r.citations)} | {r.reason} |"
        )

    lines += ["", "## Details"]
    for r in results:
        q = questions[r.question_id]
        lines += ["", f"### {q.id}. {q.title}", "", f"**{r.verdict}**: {r.reason}", ""]
        if r.error:
            lines += [f"Error: `{r.error}`"]
            continue
        lines.append(f"Question: {q.prompt}")
        lines.append("")
        lines.append(f"Agent answer: `{r.answer!r}` · expected: `{q.expected!r}` {'✓' if r.answer_correct else '✗'}")
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
    """For `cqa check`: revision chains of documents that have several revisions or are cited
    by a question (with the citing questions), then a count of the rest per top-level folder."""
    cited: dict[Path, list[str]] = {}
    for q in dataset.questions:
        for rev in q.files:
            cited.setdefault(rev.path, []).append(q.id)

    lines, rest = [], Counter()
    for doc in dataset.documents.values():
        if len(doc.revisions) == 1 and doc.latest.path not in cited:
            rest[doc.id.split("/")[0] if "/" in doc.id else "(top level)"] += 1
            continue
        lines.append(doc.id)
        for rev in doc.revisions:
            qs = cited.get(rev.path)
            lines.append(f"  r{rev.number:02d}  {rev.filename}" + (f"   <- {', '.join(qs)}" if qs else ""))
    if rest:
        lines.append("")
        lines.append("Single-revision documents not cited by any question: "
                     + ", ".join(f"{group}: {n}" for group, n in sorted(rest.items())))
    return "\n".join(lines)


def unfound_evidence(dataset: Dataset) -> list[str]:
    """Expert evidence quotes that can't be found in their file (data errors)."""
    return [
        f"{q.id}: {ev.file.filename}: {ev.quote[:80]!r}"
        for q in dataset.questions
        for ev in q.evidence
        if not evidence.locate(dataset.abspath(ev.file), ev.quote)
    ]


def write_run(run_dir: Path, dataset: Dataset, results: list[Result], meta: dict) -> None:
    """One folder per run:
    run.json            settings and timing
    results.jsonl       one graded result per question
    trajectories.jsonl  one line per question: everything the agent did
    report.md           the markdown report
    """
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    with open(run_dir / "results.jsonl", "w") as f:
        for r in results:
            row = {k: v for k, v in asdict(r).items() if k != "trajectory"}
            f.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")
    with open(run_dir / "trajectories.jsonl", "w") as f:
        for r in results:
            row = {"question_id": r.question_id, "verdict": r.verdict, "trajectory": r.trajectory}
            f.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")
    (run_dir / "report.md").write_text(render(dataset, results))
