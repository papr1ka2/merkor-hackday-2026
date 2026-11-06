from pathlib import Path

import pytest

from cqa.loader import DataError, load_all, load_family

DATA = Path(__file__).parent.parent / "data" / "contracts"


def make_family(root: Path, answers: dict[str, str], questions: str | None = None) -> Path:
    fam = root / "fam"
    fam.mkdir()
    (fam / "questions.yaml").write_text(
        questions
        or "questions:\n"
        "  - {id: a, text: 'Auto renew?', type: bool}\n"
        "  - {id: b, text: 'Cap months?', type: number}\n"
    )
    for version, body in answers.items():
        (fam / version).mkdir()
        (fam / version / "contract.md").write_text(f"contract {version}")
        (fam / version / "answers.yaml").write_text(body)
    return fam


def test_sample_data_loads():
    families = load_all(DATA)
    fam = next(f for f in families if f.id == "msa_001")
    assert [v.id for v in fam.versions] == ["v0", "v1", "v2"]
    assert fam.base.answers["effective_date"] == "2025-03-01"  # YAML date normalized
    assert fam.changed_questions(fam.versions[1]) == {
        "liability_cap_months", "governing_law", "breach_notice_hours", "cap_carveouts",
    }


def test_changed_questions(tmp_path):
    fam = load_family(make_family(tmp_path, {"v0": "a: true\nb: 12\n", "v1": "a: true\nb: 24\n"}))
    assert fam.changed_questions(fam.versions[1]) == {"b"}
    assert fam.changed_questions(fam.base) == set()


def test_versions_sort_naturally(tmp_path):
    body = "a: true\nb: 1\n"
    fam = load_family(make_family(tmp_path, {"v0": body, "v10": body, "v2": body}))
    assert [v.id for v in fam.versions] == ["v0", "v2", "v10"]


@pytest.mark.parametrize(
    "answers,msg",
    [
        ({"v1": "a: true\nb: 1\n"}, "missing base version"),
        ({"v0": "a: true\n"}, "missing=['b']"),
        ({"v0": "a: true\nb: 1\nc: 2\n"}, "unknown=['c']"),
        ({"v0": "a: yes please\nb: 1\n"}, "bool answer"),
        ({"v0": "a: true\nb: twelve\n"}, "number answer"),
    ],
)
def test_bad_data_fails_loudly(tmp_path, answers, msg):
    with pytest.raises(DataError, match=msg.replace("[", r"\[").replace("]", r"\]")):
        load_family(make_family(tmp_path, answers))


def test_choice_answer_must_be_listed(tmp_path):
    q = "questions:\n  - {id: a, text: 'Law?', type: choice, choices: [NY, DE]}\n"
    with pytest.raises(DataError, match="not in choices"):
        load_family(make_family(tmp_path, {"v0": "a: CA\n"}, questions=q))
