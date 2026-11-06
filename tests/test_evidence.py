import zipfile

from cqa import evidence

DOC = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:r><w:t>1. Term.</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Obligations survive for a period of </w:t></w:r>
<w:del><w:r><w:delText>five (5)</w:delText></w:r></w:del>
<w:ins><w:r><w:t>two (2)</w:t></w:r></w:ins>
<w:r><w:t xml:space="preserve"> years after the Recipient’s receipt of notice.</w:t></w:r></w:p>
</w:body></w:document>"""


def make_docx(tmp_path):
    path = tmp_path / "nda.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", DOC)
    return path


def test_both_readings_of_tracked_changes(tmp_path):
    path = make_docx(tmp_path)
    assert evidence.locate(path, "survive for a period of two (2) years") == "¶2"  # accepted
    assert evidence.locate(path, "survive for a period of five (5) years") is not None  # original
    assert evidence.locate(path, "survive for a period of ten (10) years") is None


def test_quote_normalization(tmp_path):
    path = make_docx(tmp_path)
    assert evidence.locate(path, "OBLIGATIONS SURVIVE … the Recipient's receipt of notice.") == "¶2"
    assert evidence.locate(path, "receipt of notice … Obligations survive") is None  # order matters


def test_overlaps():
    clause = "survive termination for a period of two (2) years; provided, recipient's obligations"
    assert evidence.overlaps("for a period of two (2) years; provided, recipient", clause)
    assert not evidence.overlaps("governed by the laws of Delaware", clause)
