"""Run an agent over every gradable question and grade each submission."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .agent import Agent
from .graders import check_citations, grade, verdict
from .schema import Dataset, Question, Result


def run(
    dataset: Dataset,
    agent: Agent,
    only: set[str] | None = None,
    source: str | None = None,
    workers: int = 4,
) -> list[Result]:
    questions = [
        q
        for q in dataset.questions
        if not q.deferred
        and (only is None or q.id in only)
        and (source is None or q.source == source)
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda q: run_one(dataset, agent, q), questions))


def run_one(dataset: Dataset, agent: Agent, q: Question) -> Result:
    files = [(dataset.abspath(rev), rev.filename) for rev in q.files]
    try:
        sub = agent.answer(q.prompt, files, q.fields)
    except Exception as e:  # one bad call shouldn't sink the whole run
        fields = {f.key: False for f in q.fields}
        return Result(q.id, "REJECT", "agent error", {}, fields, error=repr(e))

    answer = sub.get("answer") or {}
    fields_correct = grade(q, answer)
    citations = check_citations(dataset, q, sub.get("citations") or [])
    v, reason = verdict(q, fields_correct, citations)
    return Result(
        question_id=q.id,
        verdict=v,
        reason=reason,
        answer=answer,
        fields_correct=fields_correct,
        citations=citations,
        explanation=str(sub.get("explanation") or ""),
    )
