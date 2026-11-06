"""Command line entry point.

    cqa check data/contracts                 validate data, show what each redline changes
    cqa run data/contracts --out results.jsonl   run the Claude agent and grade it
"""

from __future__ import annotations

import argparse
import sys

from . import loader, report, runner
from .agent import ClaudeAgent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cqa")
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="validate data and show answer changes per version")
    check.add_argument("data", help="directory containing contract families")

    run = sub.add_parser("run", help="run the agent and grade it")
    run.add_argument("data", help="directory containing contract families")
    run.add_argument("--family", action="append", help="only run these family ids")
    run.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--out", help="write per-question results as JSONL")

    args = parser.parse_args(argv)

    try:
        families = loader.load_all(args.data)
    except loader.DataError as e:
        print(f"data error: {e}", file=sys.stderr)
        return 1

    if args.cmd == "check":
        n = sum(len(f.versions) for f in families)
        print(f"OK: {len(families)} families, {n} versions\n")
        print(report.render_changes(families))
        return 0

    if args.family:
        families = [f for f in families if f.id in args.family]
    results = runner.run(families, ClaudeAgent(effort=args.effort), workers=args.workers)
    print(report.render(results))
    if args.out:
        report.write_jsonl(results, args.out)
        print(f"\nwrote {len(results)} results to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
