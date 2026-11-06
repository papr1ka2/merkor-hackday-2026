"""Command line entry point.

    cqa check [dataset]          validate the dataset and expert evidence, show revision chains
    cqa run [dataset]            run the Claude agent and grade it
        --out results.jsonl      per-question results
        --report report.md       full markdown report (answers, citations, verdicts)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import loader, report, runner
from .agent import ClaudeAgent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cqa")
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="validate the dataset and show revision chains")
    check.add_argument("dataset", nargs="?", default="dataset")

    run = sub.add_parser("run", help="run the agent and grade it")
    run.add_argument("dataset", nargs="?", default="dataset")
    run.add_argument("-q", "--question", action="append", help="only these question ids")
    run.add_argument("--source", choices=["expert", "synthetic"], help="only questions from this source")
    run.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--out", help="write per-question results as JSONL")
    run.add_argument("--report", help="write the full markdown report here")

    args = parser.parse_args(argv)

    try:
        dataset = loader.load(args.dataset)
    except loader.DataError as e:
        print(f"data error: {e}", file=sys.stderr)
        return 1

    if args.cmd == "check":
        n_rev = sum(len(d.revisions) for d in dataset.documents.values())
        qs = dataset.questions
        by_source = ", ".join(
            f"{sum(q.source == s for q in qs)} {s}" for s in ("expert", "synthetic")
        )
        print(
            f"OK: {len(dataset.documents)} documents, {n_rev} revisions, {len(qs)} questions "
            f"({by_source}; {sum(q.deferred for q in qs)} deferred; "
            f"{sum(not q.reviewed for q in qs)} awaiting expert review)\n"
        )
        print(report.render_documents(dataset))
        missing = report.unfound_evidence(dataset)
        if missing:
            print("\nexpert evidence quotes not found in their file:", *missing, sep="\n  ")
            return 1
        return 0

    only = set(args.question) if args.question else None
    results = runner.run(
        dataset, ClaudeAgent(effort=args.effort), only=only, source=args.source, workers=args.workers
    )
    md = report.render(dataset, results)
    print(md.split("## Details")[0].rstrip())
    if args.report:
        Path(args.report).write_text(md)
        print(f"\nwrote report to {args.report}")
    if args.out:
        report.write_jsonl(results, args.out)
        print(f"\nwrote {len(results)} results to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
