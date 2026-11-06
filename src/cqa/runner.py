"""Run an agent over every contract version and grade each answer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .agent import Agent
from .graders import Judge, grade
from .schema import Family, Result, Version


def run(
    families: list[Family], agent: Agent, judge: Judge | None = None, workers: int = 4
) -> list[Result]:
    jobs = [(fam, v) for fam in families for v in fam.versions]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        per_version = pool.map(lambda job: _run_version(*job, agent, judge), jobs)
        return [r for results in per_version for r in results]


def _run_version(fam: Family, version: Version, agent: Agent, judge: Judge | None) -> list[Result]:
    agent_error = None
    try:
        got = agent.answer(version.text, fam.questions)
    except Exception as e:  # one bad call shouldn't sink the whole run
        agent_error, got = f"agent: {e!r}", {}

    changed = fam.changed_questions(version)
    results = []
    for q in fam.questions:
        expected: Any = version.answers[q.id]
        answer = got.get(q.id)
        error = agent_error
        try:
            correct = error is None and grade(q, expected, answer, judge)
        except Exception as e:
            correct, error = False, f"judge: {e!r}"
        results.append(
            Result(
                family=fam.id,
                version=version.id,
                question_id=q.id,
                question_type=q.type,
                expected=expected,
                got=answer,
                correct=correct,
                changed=None if version.is_base else q.id in changed,
                error=error,
            )
        )
    return results
