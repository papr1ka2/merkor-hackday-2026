from pathlib import Path

from cqa import report, runner
from cqa.agent import StaticAgent
from cqa.loader import load_all

DATA = Path(__file__).parent.parent / "data" / "contracts"


def always_correct_judge(q, expected, got):
    return True


def test_lazy_agent_that_ignores_redlines():
    """An agent that always gives the v0 answers: perfect on base and stability, zero flips."""
    fam = next(f for f in load_all(DATA) if f.id == "msa_001")
    base_answers = {k: str(v) for k, v in fam.base.answers.items()}
    agent = StaticAgent({v.text: base_answers for v in fam.versions})

    results = runner.run([fam], agent, judge=lambda q, e, g: e == g, workers=1)
    m = report.metrics(results)

    n_q = len(fam.questions)
    n_changed = sum(len(fam.changed_questions(v)) for v in fam.versions)
    assert m["base"] == (n_q, n_q)
    assert m["flip"] == (0, n_changed)
    assert m["stability"] == (2 * n_q - n_changed, 2 * n_q - n_changed)
    assert "[should flip]" in report.render(results)


def test_agent_failure_is_recorded_as_wrong_not_crash():
    class Broken:
        def answer(self, contract, questions):
            raise RuntimeError("boom")

    fam = next(f for f in load_all(DATA) if f.id == "msa_001")
    results = runner.run([fam], Broken(), judge=always_correct_judge, workers=1)
    assert len(results) == len(fam.questions) * len(fam.versions)
    assert not any(r.correct for r in results)


def test_jsonl_roundtrip(tmp_path):
    fam = next(f for f in load_all(DATA) if f.id == "msa_001")
    results = runner.run([fam], StaticAgent({}), judge=always_correct_judge, workers=1)
    out = tmp_path / "r.jsonl"
    report.write_jsonl(results, out)
    assert len(out.read_text().splitlines()) == len(results)


def test_errors_are_flagged_in_report():
    class Broken:
        def answer(self, contract, questions):
            raise RuntimeError("boom")

    fam = next(f for f in load_all(DATA) if f.id == "msa_001")
    results = runner.run([fam], Broken(), workers=1)
    assert all(r.error and "boom" in r.error for r in results)
    assert report.render(results).startswith("WARNING: 24/24 answers errored")


def test_judge_error_is_recorded_per_question():
    def bad_judge(q, e, g):
        raise RuntimeError("judge down")

    fam = next(f for f in load_all(DATA) if f.id == "msa_001")
    answers = {k: str(v) for k, v in fam.base.answers.items()}
    results = runner.run([fam], StaticAgent({fam.base.text: answers}), judge=bad_judge, workers=1)
    errored = {r.question_id for r in results if r.error}
    assert errored == {"cap_carveouts"}
