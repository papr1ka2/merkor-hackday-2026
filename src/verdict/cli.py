from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

from . import llm, loader, report, runner
from .agent import ClaudeAgent
from .claude_code import ClaudeCodeAgent, session_dirs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verdict")
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="validate the dataset and show revision chains")
    check.add_argument("dataset", nargs="?", default="dataset")

    run = sub.add_parser("run", help="run the agent and grade it")
    run.add_argument("dataset", nargs="?", default="dataset")
    run.add_argument("-q", "--question", action="append", help="only these question ids")
    run.add_argument("--source", choices=["expert", "synthetic"], help="only questions from this source")
    run.add_argument("--agent", default="claude-code", choices=["claude-code", "claude-api"])
    run.add_argument("--model", help="claude-code: alias or model id (default opus); claude-api: model id")
    run.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--runs-dir", default="runs", help="where run folders are written")
    run.add_argument(
        "--no-isolation",
        action="store_true",
        help="claude-code: don't sandbox the agent away from the repo (answer key, past runs)",
    )

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
            f"({by_source}; {sum(q.deferred for q in qs)} not graded yet; "
            f"{sum(not q.reviewed for q in qs)} awaiting expert review)\n"
        )
        print(report.render_documents(dataset))
        missing = report.unfound_evidence(dataset)
        if missing:
            print("\nexpert evidence quotes not found in their file:", *missing, sep="\n  ")
            return 1
        return 0

    only = set(args.question) if args.question else None
    started = dt.datetime.now(dt.timezone.utc)
    if args.agent == "claude-code":
        model = args.model or "opus"
        # The repo holds the answer key and git history; past runs hold graded answers.
        repo = Path(args.dataset).resolve().parent
        deny = [repo, Path(args.runs_dir).resolve(), *session_dirs(repo)]
        agent = ClaudeCodeAgent(
            model=model, effort=args.effort, deny_read=deny, isolate=not args.no_isolation
        )
    else:
        model = llm.MODEL = args.model or llm.MODEL
        agent = ClaudeAgent(effort=args.effort)
    results = runner.run(dataset, agent, only=only, source=args.source, workers=args.workers)
    meta = {
        "started_at": started.isoformat(),
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "agent": args.agent,
        "model": model,
        "effort": args.effort,
        "isolation": "n/a" if args.agent != "claude-code" else (
            "none" if args.no_isolation else "claude code sandbox: repo and runs dir unreadable, no shell network"
        ),
        "dataset": str(args.dataset),
        "git_commit": _git_commit(),
        "questions": [r.question_id for r in results],
    }
    run_dir = Path(args.runs_dir) / started.strftime("%Y%m%d-%H%M%S")
    report.write_run(run_dir, dataset, results, meta)
    print(report.render(dataset, results).split("## Details")[0].rstrip())
    print(f"\nwrote {run_dir}/ (run.json, results.jsonl, trajectories.jsonl, report.md)")
    return 0


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None
