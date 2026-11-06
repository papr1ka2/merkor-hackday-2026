"""Grader-side quote matching in the raw contract files (the agent reads the files itself)."""

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
    # Quote marks are dropped entirely: PDF extraction often turns curly quotes into "?".
    text = re.sub(r"[\"'?]", "", text.translate(_TRANSLATE))
    return re.sub(r"\s+", " ", text).strip().casefold()


@cache
def readings(path: Path) -> tuple[tuple[str, ...], ...]:
    """Alternative texts of the file, each a tuple of normalized paragraphs.

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
    """'¶N' (paragraph, or line for PDFs) where the quote starts, or None. "…" skips text;
    paragraphs are tried one by one first, then joined so a quote may span them."""
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


def _docx_readings(path: Path) -> tuple[list[str], list[str], list[str]]:
    """Body text with tracked changes accepted, the same as originally written, and comments."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
        names = set(z.namelist())
        comments_xml = z.read("word/comments.xml") if "word/comments.xml" in names else None
    accepted, original = [], []
    for p in root.iter(f"{W}p"):
        acc, org = [], []
        _walk(p, acc, org, in_ins=False)
        accepted.append("".join(acc))
        original.append("".join(org))
    comments = []
    if comments_xml:
        for p in ET.fromstring(comments_xml).iter(f"{W}p"):
            acc, org = [], []
            _walk(p, acc, org, in_ins=False)
            comments.append("".join(acc))
    return accepted, original, comments


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
