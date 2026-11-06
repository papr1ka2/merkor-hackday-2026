"""Local viewer for VERDICT runs.

    uv run python web/server.py            # http://127.0.0.1:8000
    uv run python web/server.py --port 8080 --runs-dir runs --dataset dataset
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

from verdict import loader

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
AGENTS = ("claude-code", "claude-api")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
HUMAN_FIELDS = ("answer", "basis", "trap", "traps", "notes", "split_from")


class Viewer:
    def __init__(self, dataset: Path, runs: Path):
        self.dataset_dir = dataset.resolve()
        self.runs_dir = runs.resolve()
        self.job: dict | None = None
        self.lock = threading.Lock()

    # Reloaded per request so edits to questions.yaml or new runs show up without a restart.
    def questions(self) -> list[dict]:
        ds = loader.load(self.dataset_dir)
        raw = {str(q["id"]): q for q in yaml.safe_load((self.dataset_dir / "questions.yaml").read_text())}
        out = []
        for q in ds.questions:
            extra = {k: raw[q.id][k] for k in HUMAN_FIELDS if k in raw[q.id]}
            out.append({
                "id": q.id,
                "title": q.title,
                "prompt": q.prompt,
                "source": q.source,
                "reviewed": q.reviewed,
                "graded": not q.deferred,
                "kind": q.answer_type.kind if q.answer_type else None,
                "choices": list(q.answer_type.choices) if q.answer_type else [],
                "expected": q.expected,
                "files": [{"path": r.path.as_posix(), "name": r.filename, "revision": r.number} for r in q.files],
                "evidence": [{"path": e.file.path.as_posix(), "name": e.file.filename, "quote": e.quote} for e in q.evidence],
                **extra,
            })  # fmt: skip
        return out

    def version(self) -> str:
        """Changes whenever questions.yaml or any run's files change; the page polls it to refresh."""
        paths = [self.dataset_dir / "questions.yaml"]
        if self.runs_dir.is_dir():
            paths += [f for d in self.runs_dir.iterdir() if d.is_dir() for f in d.iterdir()]
        return str(hash(tuple(sorted((str(p), p.stat().st_mtime_ns) for p in paths if p.exists()))))

    def runs(self) -> list[dict]:
        if not self.runs_dir.is_dir():
            return []
        out = []
        for d in sorted(self.runs_dir.iterdir(), reverse=True):
            if (d / "results.jsonl").exists():
                meta = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
                out.append({"id": d.name, "meta": meta})
        return out

    def results(self, run: str) -> list[dict]:
        return _jsonl(self._run_dir(run) / "results.jsonl")

    def trajectory(self, run: str, qid: str) -> list:
        for row in _jsonl(self._run_dir(run) / "trajectories.jsonl"):
            if row.get("question_id") == qid:
                return row.get("trajectory") or []
        return []

    def start_job(self, req: dict) -> dict:
        """Start `verdict run` for the given questions in the background. One job at a time."""
        ids = req.get("questions") or []
        agent, model, effort = req.get("agent", "claude-code"), req.get("model", "haiku"), req.get("effort", "high")
        known = {q["id"] for q in self.questions() if q["graded"]}
        if not ids or not set(ids) <= known:
            raise ValueError(f"unknown or ungraded questions: {sorted(set(ids) - known)}")
        if agent not in AGENTS or effort not in EFFORTS or not MODEL_RE.match(str(model)):
            raise ValueError("invalid agent, model or effort")
        with self.lock:
            if self.job and self.job["proc"].poll() is None:
                raise RuntimeError("a run is already in progress")
            cmd = [sys.executable, "-m", "verdict", "run", str(self.dataset_dir), "--agent", agent,
                   "--model", model, "--effort", effort, "--runs-dir", str(self.runs_dir)]
            for qid in ids:
                cmd += ["-q", qid]
            log = []
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            threading.Thread(target=lambda: log.extend(proc.stdout), daemon=True).start()
            self.job = {"proc": proc, "log": log, "questions": ids, "agent": agent, "model": model,
                        "effort": effort, "started": time.time()}  # fmt: skip
        return self.job_status()

    def job_status(self) -> dict:
        job = self.job
        if not job:
            return {"state": "idle"}
        code = job["proc"].poll()
        return {
            "state": "running" if code is None else ("done" if code == 0 else "failed"),
            "exit_code": code,
            "questions": job["questions"],
            "agent": job["agent"], "model": job["model"], "effort": job["effort"],
            "elapsed": round(time.time() - job["started"]),
            "log": "".join(job["log"])[-3000:],
        }  # fmt: skip

    def contract_file(self, rel: str) -> Path | None:
        path = (self.dataset_dir / rel).resolve()
        docs = self.dataset_dir / "documents"
        return path if path.is_file() and docs in path.parents else None

    def _run_dir(self, run: str) -> Path:
        d = (self.runs_dir / run).resolve()
        if d.parent != self.runs_dir or not d.is_dir():
            raise FileNotFoundError(run)
        return d


def _jsonl(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def make_handler(viewer: Viewer):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = [unquote(p) for p in urlparse(self.path).path.split("/") if p]
            try:
                match parts:
                    case []:
                        self._file(STATIC / "index.html")
                    case ["static", name] if (STATIC / name).is_file():
                        self._file(STATIC / name)
                    case ["api", "questions"]:
                        self._json(viewer.questions())
                    case ["api", "runs"]:
                        self._json(viewer.runs())
                    case ["api", "runs", run, "results"]:
                        self._json(viewer.results(run))
                    case ["api", "version"]:
                        self._json({"version": viewer.version()})
                    case ["api", "job"]:
                        self._json(viewer.job_status())
                    case ["api", "runs", run, "trajectory", qid]:
                        self._json(viewer.trajectory(run, qid))
                    case ["files", *rel] if (path := viewer.contract_file("/".join(rel))):
                        self._file(path, download=path.suffix.lower() != ".pdf")
                    case _:
                        self.send_error(404)
            except FileNotFoundError:
                self.send_error(404)
            except loader.DataError as e:
                self._json({"error": str(e)}, status=500)

        def do_POST(self):
            # Runs send contracts to Anthropic: only accept requests from this page on localhost.
            # The custom header can't be set by other sites without a CORS preflight, which we never allow.
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in ("127.0.0.1", "localhost") or self.headers.get("X-Verdict") != "1":
                return self.send_error(403)
            if urlparse(self.path).path != "/api/run":
                return self.send_error(404)
            try:
                length = int(self.headers.get("Content-Length") or 0)
                req = json.loads(self.rfile.read(min(length, 100_000)) or b"{}")
                self._json(viewer.start_job(req))
            except (ValueError, json.JSONDecodeError) as e:
                self._json({"error": str(e)}, status=400)
            except RuntimeError as e:
                self._json({"error": str(e)}, status=409)

        def _json(self, data, status: int = 200):
            body = json.dumps(data, default=str, ensure_ascii=False).encode()
            self._send(body, "application/json; charset=utf-8", status)

        def _file(self, path: Path, download: bool = False):
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("javascript"):
                ctype += "; charset=utf-8"
            headers = {}
            if download:
                headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{_quote(path.name.split('__', 1)[-1])}"
            self._send(path.read_bytes(), ctype, 200, headers)

        def _send(self, body: bytes, ctype: str, status: int, headers: dict | None = None):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return Handler


def _quote(name: str) -> str:
    from urllib.parse import quote

    return quote(name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local viewer for VERDICT runs")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dataset", default="dataset")
    parser.add_argument("--runs-dir", default="runs")
    args = parser.parse_args()
    viewer = Viewer(Path(args.dataset), Path(args.runs_dir))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(viewer))
    print(f"VERDICT viewer on http://127.0.0.1:{args.port}  (Ctrl+C to stop)")
    server.serve_forever()


if __name__ == "__main__":
    main()
