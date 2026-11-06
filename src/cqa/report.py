"""Turn results into metrics and a readable report."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .schema import Family, Result


def metrics(results: list[Result]) -> dict[str, tuple[int, int]]:
    """Each metric is (correct, total).

    base       accuracy on base (v0) contracts
    redlined   accuracy on all non-base versions
    flip       on non-base versions, questions whose answer the redline changed
    stability  on non-base versions, questions whose answer stayed the same
    """
    buckets = {
        "overall": results,
        "base": [r for r in results if r.changed is None],
        "redlined": [r for r in results if r.changed is not None],
        "flip": [r for r in results if r.changed is True],
        "stability": [r for r in results if r.changed is False],
    }
    return {name: (sum(r.correct for r in rs), len(rs)) for name, rs in buckets.items()}


def render(results: list[Result]) -> str:
    lines = []
    errors = [r for r in results if r.error]
    if errors:
        lines += [
            f"WARNING: {len(errors)}/{len(results)} answers errored and are scored as wrong.",
            f"First error: {errors[0].error}",
            "",
        ]
    lines += ["| metric | score |", "|---|---|"]
    for name, (ok, n) in metrics(results).items():
        lines.append(f"| {name} | {_pct(ok, n)} ({ok}/{n}) |")

    lines += ["", "| version | correct |", "|---|---|"]
    for key in dict.fromkeys(f"{r.family}/{r.version}" for r in results):
        rs = [r for r in results if f"{r.family}/{r.version}" == key]
        ok = sum(r.correct for r in rs)
        lines.append(f"| {key} | {_pct(ok, len(rs))} ({ok}/{len(rs)}) |")

    misses = [r for r in results if not r.correct and not r.error]
    if misses:
        lines += ["", "Misses:"]
        for r in misses:
            tag = "  [should flip]" if r.changed else ""
            lines.append(
                f"- {r.family}/{r.version} {r.question_id}: "
                f"expected {r.expected!r}, got {r.got!r}{tag}"
            )
    return "\n".join(lines)


def render_changes(families: list[Family]) -> str:
    """For reviewers: which answers each version changes relative to v0."""
    lines = []
    for fam in families:
        base = fam.base
        for v in fam.versions:
            if v.is_base:
                continue
            changed = sorted(fam.changed_questions(v))
            lines.append(f"{v.key}: {len(changed)} answer(s) differ from {base.id}")
            for qid in changed:
                lines.append(f"  {qid}: {base.answers[qid]!r} -> {v.answers[qid]!r}")
            if not changed:
                lines.append("  (none; is this redline expected to change nothing?)")
    return "\n".join(lines)


def write_jsonl(results: list[Result], path: str | Path) -> None:
    with open(path, "w") as f:
        for r in results:
            f.write(json.dumps(asdict(r), default=str) + "\n")


def _pct(ok: int, n: int) -> str:
    return f"{100 * ok / n:.1f}%" if n else "n/a"
