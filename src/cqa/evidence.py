"""Grader-side text access: find quoted evidence in the raw contract files.

The agent never uses this; it reads the raw files itself. Matching is done on
normalized text (case, quotes, dashes, whitespace) and a quote may skip text with "…".
A .docx yields two readings, with tracked changes accepted and rejected; a quote is
found if it appears in either.
"""

from __future__ import annotations

import re
import zipfile
from difflib import SequenceMatcher
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_ELLIPSIS = re.compile(r"\s*(?:…|\.\.\.)\s*")
_TRANSLATE = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})
MIN_OVERLAP = 40  # chars of shared text for a citation to count as citing an expert clause


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_TRANSLATE)).strip().casefold()


@cache
def readings(path: Path) -> tuple[tuple[str, ...], ...]:
    """The file's text as one or more readings, each a tuple of normalized paragraphs.

    .docx: tracked changes accepted, and rejected (same paragraph numbering in both).
    .pdf:  plain and layout extraction (plain can scramble order; layout can merge columns).
    """
    if path.suffix.lower() == ".docx":
        raw = _docx_readings(path)
    elif path.suffix.lower() == ".pdf":
        raw = _pdf_readings(path)
    else:
        raw = (path.read_text(errors="ignore").splitlines(),)
    return tuple(tuple(normalize(t) for t in reading) for reading in raw)


def locate(path: Path, quote: str) -> str | None:
    """Return '¶N' (paragraph, or line for PDFs) where the quote starts, or None if not found.

    Each reading is searched separately, first paragraph by paragraph, then as one joined
    text so a quote may span paragraphs.
    """
    parts = [p for p in (normalize(s).rstrip(".,;:") for s in _ELLIPSIS.split(quote)) if p]
    if not parts:
        return None
    for paras in readings(path):
        for i, text in enumerate(paras, 1):
            if _in_order(parts, text):
                return f"¶{i}"
    for paras in readings(path):
        joined = " ".join(paras)
        if _in_order(parts, joined):
            at = joined.find(parts[0])
            return f"¶{_para_at(paras, at)}"
    return None


def _para_at(paras: tuple[str, ...], offset: int) -> int:
    pos = 0
    for i, text in enumerate(paras, 1):
        pos += len(text) + 1
        if offset < pos:
            return i
    return len(paras)


def overlaps(a: str, b: str) -> bool:
    """Do two quotes share a substantial stretch of text?"""
    a, b = normalize(_ELLIPSIS.sub(" ", a)), normalize(_ELLIPSIS.sub(" ", b))
    if not a or not b:
        return False
    m = SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return m.size >= min(MIN_OVERLAP, len(a), len(b))


def _in_order(parts: list[str], text: str) -> bool:
    pos = 0
    for part in parts:
        pos = text.find(part, pos)
        if pos < 0:
            return False
        pos += len(part)
    return True


def _docx_readings(path: Path) -> tuple[list[str], list[str]]:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    accepted, original = [], []
    for p in root.iter(f"{W}p"):
        acc, org = [], []
        _walk(p, acc, org, in_ins=False)
        accepted.append("".join(acc))
        original.append("".join(org))
    return accepted, original


def _walk(el: ET.Element, acc: list[str], org: list[str], in_ins: bool) -> None:
    for child in el:
        tag = child.tag
        if tag == f"{W}p":  # nested paragraphs (text boxes) are visited on their own
            continue
        if tag == f"{W}t" and child.text:
            acc.append(child.text)
            if not in_ins:
                org.append(child.text)
        elif tag == f"{W}delText" and child.text:
            org.append(child.text)
        elif tag in (f"{W}tab", f"{W}br"):
            acc.append(" ")
            org.append(" ")
        _walk(child, acc, org, in_ins or tag == f"{W}ins")


def _pdf_readings(path: Path) -> tuple[list[str], list[str]]:
    from pypdf import PdfReader

    plain, layout = [], []
    for page in PdfReader(path).pages:
        plain += (page.extract_text() or "").splitlines()
        layout += (page.extract_text(extraction_mode="layout") or "").splitlines()
    return plain, layout
