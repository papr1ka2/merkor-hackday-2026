from cqa import report, runner
from cqa.agent import StaticAgent, answer_schema
from cqa.loader import load

from .conftest import REPO_DATASET


class OracleAgent:
    """Answers with the dataset's own expected values, read from questions.yaml at runtime."""

    def __init__(self, dataset):
        self.by_prompt = {q.prompt: q.expected for q in dataset.questions}

    def answer(self, prompt, files, fields):
        assert all(path.exists() for path, _ in files)
        assert all(not name.startswith("r0") for _, name in files)  # agent sees original names
        return dict(self.by_prompt[prompt])


def test_oracle_scores_100_and_deferred_are_skipped():
    ds = load(REPO_DATASET)
    results = runner.run(ds, OracleAgent(ds), workers=1)
    gradable = [q for q in ds.questions if not q.deferred]
    assert len(results) == len(gradable)
    assert all(r.correct for r in results)
    assert f"Score: {len(results)}/{len(results)}" in report.render(ds, results)


def test_empty_answers_fail_and_show_as_misses():
    ds = load(REPO_DATASET)
    results = runner.run(ds, StaticAgent({}), workers=1)
    assert not any(r.correct for r in results)
    assert "Misses:" in report.render(ds, results)


def test_agent_errors_are_flagged():
    class Broken:
        def answer(self, prompt, files, fields):
            raise RuntimeError("boom")

    ds = load(REPO_DATASET)
    results = runner.run(ds, Broken(), workers=1)
    assert all(r.error and "boom" in r.error and not r.correct for r in results)
    assert report.render(ds, results).startswith(f"WARNING: {len(results)}/{len(results)}")


def test_only_filter():
    ds = load(REPO_DATASET)
    first = next(q for q in ds.questions if not q.deferred)
    results = runner.run(ds, StaticAgent({}), only={first.id}, workers=1)
    assert [r.question_id for r in results] == [first.id]


def test_answer_schema_has_fields_but_no_expected_values():
    ds = load(REPO_DATASET)
    for q in ds.questions:
        schema = answer_schema(q.fields)
        assert set(schema["required"]) == set(q.expected)
        assert "value" not in repr(schema)
