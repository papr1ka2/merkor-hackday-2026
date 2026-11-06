"""Read a dataset directory into schema objects, failing loudly on bad data."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml

from .schema import (
    ANSWER_KINDS,
    SOURCES,
    REVISION_NAME,
    Dataset,
    Document,
    Evidence,
    AnswerType,
    Question,
    Revision,
)

IGNORED = {".DS_Store"}


class DataError(ValueError):
    pass


def load(root: str | Path) -> Dataset:
    root = Path(root)
    documents = load_documents(root)
    by_path = {rev.path: rev for doc in documents.values() for rev in doc.revisions}
    questions = load_questions(root / "questions.yaml", by_path)
    return Dataset(root=root, documents=documents, questions=questions)


def load_documents(root: Path) -> dict[str, Document]:
    docs_dir = root / "documents"
    if not docs_dir.is_dir():
        raise DataError(f"missing {docs_dir}")

    documents = {}
    for d in sorted(p for p in docs_dir.rglob("*") if p.is_dir()):
        entries = [p for p in d.iterdir() if p.name not in IGNORED]
        files = [p for p in entries if p.is_file()]
        if not files:
            continue  # a grouping folder
        if len(files) != len(entries):
            raise DataError(f"{d}: a document folder holds only revision files, no subfolders")
        bad = [p.name for p in files if not REVISION_NAME.match(p.name)]
        if bad:
            raise DataError(f"{d}: files must be named rNN__<original name>: {bad}")
        revisions = tuple(
            sorted((Revision(p.relative_to(root)) for p in files), key=lambda r: r.number)
        )
        numbers = [r.number for r in revisions]
        if numbers != list(range(1, len(numbers) + 1)):
            raise DataError(f"{d}: revisions must be numbered r01..rNN with no gaps, got {numbers}")
        doc_id = d.relative_to(docs_dir).as_posix()
        documents[doc_id] = Document(id=doc_id, revisions=revisions)

    if not documents:
        raise DataError(f"no documents under {docs_dir}")
    return documents


def load_questions(path: Path, revisions: dict[Path, Revision]) -> list[Question]:
    if not path.exists():
        raise DataError(f"missing {path}")
    items = yaml.safe_load(path.read_text())
    if not isinstance(items, list):
        raise DataError(f"{path}: expected a list of questions")

    questions, seen = [], set()
    for item in items:
        qid = str(item.get("id", ""))
        where = f"{path}: question {qid!r}"
        if not qid or qid in seen:
            raise DataError(f"{where}: missing or duplicate id")
        seen.add(qid)
        for key in ("title", "prompt", "files"):
            if not item.get(key):
                raise DataError(f"{where}: missing {key!r}")
        if item.get("source") not in SOURCES:
            raise DataError(f"{where}: source must be one of {SOURCES}, got {item.get('source')!r}")
        if not isinstance(item.get("reviewed"), bool):
            raise DataError(f"{where}: reviewed must be true or false")

        files = []
        for f in item["files"]:
            rev = revisions.get(Path(f))
            if rev is None:
                raise DataError(f"{where}: file not found in documents/: {f}")
            files.append(rev)
        names = [r.filename for r in files]
        if len(set(names)) != len(names):
            raise DataError(f"{where}: cited files must have distinct filenames: {names}")

        evidence = []
        for ev in item.get("evidence") or ():
            rev = revisions.get(Path(str(ev.get("file", ""))))
            if rev not in files:
                raise DataError(f"{where}: evidence file must be one of the question's files: {ev.get('file')}")
            if not str(ev.get("quote", "")).strip():
                raise DataError(f"{where}: evidence entry missing quote")
            evidence.append(Evidence(file=rev, quote=str(ev["quote"])))

        answer_type, expected = None, None
        if item.get("expected") is not None:
            answer_type, expected = _parse_expected(item["expected"], f"{where}: expected")

        questions.append(
            Question(
                id=qid,
                source=item["source"],
                reviewed=item["reviewed"],
                title=item["title"],
                prompt=item["prompt"],
                files=tuple(files),
                answer_type=answer_type,
                expected=expected,
                evidence=tuple(evidence),
            )
        )
    return questions


def _parse_expected(spec: Any, where: str) -> tuple[AnswerType, Any]:
    if not isinstance(spec, dict) or "type" not in spec or "value" not in spec:
        raise DataError(f"{where}: expected one answer as {{type: ..., value: ...}}")
    ftype, value = spec["type"], spec["value"]
    if ftype not in ANSWER_KINDS:
        raise DataError(f"{where}: type must be one of {ANSWER_KINDS}, got {ftype!r}")

    choices = tuple(str(c) for c in spec.get("choices") or ())
    if ftype == "choice":
        if not choices:
            raise DataError(f"{where}: choice answers need 'choices'")
        if str(value) not in choices:
            raise DataError(f"{where}: {value!r} not in choices {choices}")
        value = str(value)
    elif ftype == "bool" and not isinstance(value, bool):
        raise DataError(f"{where}: bool value must be true/false, got {value!r}")
    elif ftype == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
        raise DataError(f"{where}: number value must be numeric, got {value!r}")
    elif ftype == "date":
        try:
            value = dt.date.fromisoformat(str(value)).isoformat()
        except ValueError:
            raise DataError(f"{where}: date value must be YYYY-MM-DD, got {value!r}") from None

    return AnswerType(kind=ftype, choices=choices), value
