from pathlib import Path

import pytest

REPO_DATASET = Path(__file__).parent.parent / "dataset"


@pytest.fixture
def make_dataset(tmp_path):
    """Build a small dataset: make_dataset({doc: [filenames]}, questions_yaml)."""

    def make(documents: dict[str, list[str]], questions: str) -> Path:
        root = tmp_path / "ds"
        (root / "documents").mkdir(parents=True)
        for doc, names in documents.items():
            (root / "documents" / doc).mkdir()
            for name in names:
                (root / "documents" / doc / name).write_bytes(b"raw file")
        (root / "questions.yaml").write_text(questions)
        return root

    return make
