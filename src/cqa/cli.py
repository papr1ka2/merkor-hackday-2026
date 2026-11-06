"""Command line entry point.

    cqa check [dataset]                       validate the dataset, show revision chains
    cqa run [dataset] --out results.jsonl     run the Claude agent and grade it
"""

from __future__ import annotations

import argparse
import sys

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
    run.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--out", help="write per-question results as JSONL")

    args = parser.parse_args(argv)

    try:
        dataset = loader.load(args.dataset)
    except loader.DataError as e:
        print(f"data error: {e}", file=sys.stderr)
        return 1

    if args.cmd == "check":
        n_rev = sum(len(d.revisions) for d in dataset.documents.values())
        n_def = sum(q.deferred for q in dataset.questions)
        print(
            f"OK: {len(dataset.documents)} documents, {n_rev} revisions, "
            f"{len(dataset.questions)} questions ({n_def} deferred)\n"
        )
        print(report.render_documents(dataset))
        return 0

    only = set(args.question) if args.question else None
    results = runner.run(dataset, ClaudeAgent(effort=args.effort), only=only, workers=args.workers)
    print(report.render(dataset, results))
    if args.out:
        report.write_jsonl(results, args.out)
        print(f"\nwrote {len(results)} results to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
