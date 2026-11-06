"""Run an agent over every gradable question and grade each answer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .agent import Agent
from .graders import grade
from .schema import Dataset, Question, Result


def run(
    dataset: Dataset, agent: Agent, only: set[str] | None = None, workers: int = 4
) -> list[Result]:
    questions = [
        q for q in dataset.questions if not q.deferred and (only is None or q.id in only)
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda q: run_one(dataset, agent, q), questions))


def run_one(dataset: Dataset, agent: Agent, q: Question) -> Result:
    files = [(dataset.abspath(rev), rev.filename) for rev in q.files]
    try:
        got = agent.answer(q.prompt, files, q.fields)
    except Exception as e:  # one bad call shouldn't sink the whole run
        return Result(q.id, {}, {f.key: False for f in q.fields}, error=repr(e))
    return Result(q.id, got, grade(q, got))
