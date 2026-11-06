from verdict import report, runner
from verdict.agent import StaticAgent, submission_schema
from verdict.loader import load

from .conftest import REPO_DATASET


class OracleAgent:
    """Submits the dataset's own expected answers and evidence, read from questions.yaml."""

    def __init__(self, dataset):
        self.by_prompt = {q.prompt: q for q in dataset.questions}

    def answer(self, prompt, files, answer_type):
        q = self.by_prompt[prompt]
        assert all(path.exists() for path, _ in files)
        assert all(not name.startswith("r0") for _, name in files)  # agent sees original names
        cites = [{"file": ev.file.filename, "quote": ev.quote} for ev in q.evidence]
        return {"answer": q.expected, "citations": cites, "explanation": "oracle"}


def test_oracle_is_accepted_everywhere():
    ds = load(REPO_DATASET)
    results = runner.run(ds, OracleAgent(ds), workers=1)
    assert len(results) == sum(not q.deferred for q in ds.questions)
    bad = [(r.question_id, r.verdict, r.reason) for r in results if r.verdict != "ACCEPT"]
    assert bad == []
    md = report.render(ds, results)
    assert f"{len(results)} ACCEPT" in md and "## Details" in md


def test_right_answer_with_fabricated_quote_escalates():
    ds = load(REPO_DATASET)
    q = next(q for q in ds.questions if not q.deferred and q.evidence)
    fake = {"file": q.files[0].filename, "quote": "the parties agree to exchange one ceremonial goat"}
    agent = StaticAgent({q.prompt: {"answer": q.expected, "citations": [fake], "explanation": ""}})
    [r] = runner.run(ds, agent, only={q.id}, workers=1)
    assert r.verdict == "ESCALATE" and r.answer_correct
    assert "NOT FOUND" in report.render(ds, [r])


def test_empty_submission_is_rejected():
    ds = load(REPO_DATASET)
    results = runner.run(ds, StaticAgent({}), workers=1)
    assert {r.verdict for r in results} == {"REJECT"}


def test_agent_errors_are_flagged():
    class Broken:
        def answer(self, prompt, files, answer_type):
            raise RuntimeError("boom")

    ds = load(REPO_DATASET)
    results = runner.run(ds, Broken(), workers=1)
    assert all(r.error and "boom" in r.error and r.verdict == "REJECT" for r in results)
    assert "WARNING" in report.render(ds, results)


def test_schema_has_answer_type_and_filenames_but_no_expected_value():
    ds = load(REPO_DATASET)
    for q in ds.questions:
        if q.deferred:
            continue
        names = [r.filename for r in q.files]
        schema = submission_schema(q.answer_type, names)
        assert schema["properties"]["citations"]["items"]["properties"]["file"]["enum"] == names
        if q.answer_type.kind != "choice":  # choice answers list every option, incl. the right one
            assert repr(q.expected) not in repr(schema["properties"]["answer"])


def test_source_filter():
    ds = load(REPO_DATASET)
    assert runner.run(ds, StaticAgent({}), source="synthetic", workers=1) == []
    assert len(runner.run(ds, StaticAgent({}), source="expert", workers=1)) == sum(
        not q.deferred for q in ds.questions
    )
