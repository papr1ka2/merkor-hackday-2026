"""Read the data/ directory into schema objects, failing loudly on bad data.

Layout:
    <root>/<family>/questions.yaml
    <root>/<family>/<version>/contract.(md|txt)
    <root>/<family>/<version>/answers.yaml     # {question_id: answer}, complete
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

import yaml

from .schema import BASE_VERSION, QUESTION_TYPES, Family, Question, Version


class DataError(ValueError):
    pass


def load_all(root: str | Path) -> list[Family]:
    root = Path(root)
    families = [load_family(p) for p in sorted(root.iterdir()) if (p / "questions.yaml").exists()]
    if not families:
        raise DataError(f"no contract families (dirs with questions.yaml) under {root}")
    return families


def load_family(path: str | Path) -> Family:
    path = Path(path)
    questions = _load_questions(path / "questions.yaml")
    versions = [
        _load_version(path.name, d, questions)
        for d in sorted(path.iterdir(), key=_natural_key)
        if d.is_dir() and (d / "answers.yaml").exists()
    ]
    if not any(v.id == BASE_VERSION for v in versions):
        raise DataError(f"{path.name}: missing base version '{BASE_VERSION}/'")
    return Family(id=path.name, questions=questions, versions=versions)


def _load_questions(path: Path) -> list[Question]:
    raw = _read_yaml(path)
    items = raw.get("questions") if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise DataError(f"{path}: expected a non-empty 'questions:' list")

    questions, seen = [], set()
    for item in items:
        qid, qtype = str(item.get("id", "")), item.get("type")
        where = f"{path}: question '{qid}'"
        if not qid or qid in seen:
            raise DataError(f"{where}: missing or duplicate id")
        if qtype not in QUESTION_TYPES:
            raise DataError(f"{where}: type must be one of {QUESTION_TYPES}, got {qtype!r}")
        choices = tuple(str(c) for c in item.get("choices") or ())
        if qtype == "choice" and not choices:
            raise DataError(f"{where}: choice questions need 'choices'")
        if not item.get("text"):
            raise DataError(f"{where}: missing text")
        seen.add(qid)
        questions.append(Question(id=qid, text=item["text"], type=qtype, choices=choices))
    return questions


def _load_version(family: str, path: Path, questions: list[Question]) -> Version:
    contracts = sorted(path.glob("contract.*"))
    if len(contracts) != 1:
        raise DataError(f"{path}: expected exactly one contract.* file, found {len(contracts)}")

    raw = _read_yaml(path / "answers.yaml") or {}
    if not isinstance(raw, dict):
        raise DataError(f"{path}/answers.yaml: expected a mapping of question_id -> answer")
    answers = {str(k): v for k, v in raw.items()}

    expected_ids = {q.id for q in questions}
    missing, extra = expected_ids - answers.keys(), answers.keys() - expected_ids
    if missing or extra:
        raise DataError(
            f"{path}/answers.yaml: must answer exactly the questions in questions.yaml "
            f"(missing={sorted(missing)}, unknown={sorted(extra)})"
        )

    for q in questions:
        answers[q.id] = _check_answer(q, answers[q.id], f"{path}/answers.yaml: {q.id}")

    return Version(family=family, id=path.name, text=contracts[0].read_text(), answers=answers)


def _check_answer(q: Question, value: Any, where: str) -> Any:
    if q.type == "bool" and not isinstance(value, bool):
        raise DataError(f"{where}: bool answer must be true/false, got {value!r}")
    if q.type == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
        raise DataError(f"{where}: number answer must be numeric, got {value!r}")
    if q.type == "choice" and str(value) not in q.choices:
        raise DataError(f"{where}: {value!r} not in choices {q.choices}")
    if q.type == "date":
        if isinstance(value, dt.date):
            return value.isoformat()
        try:
            return dt.date.fromisoformat(str(value)).isoformat()
        except ValueError:
            raise DataError(f"{where}: date answer must be YYYY-MM-DD, got {value!r}") from None
    if q.type in ("choice", "text"):
        return str(value)
    return value


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        raise DataError(f"missing file: {path}")
    return yaml.safe_load(path.read_text())


def _natural_key(p: Path) -> tuple:
    """Sort v2 before v10."""
    return tuple(int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name))
