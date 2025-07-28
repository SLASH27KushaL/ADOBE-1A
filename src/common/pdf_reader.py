# src/common/pdf_reader.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Dict
import logging
import statistics
from collections import defaultdict

import fitz  # PyMuPDF

log = logging.getLogger(__name__)


@dataclass
class Span:
    text: str
    size: float
    font: str
    flags: int
    bbox: Tuple[float, float, float, float]
    is_bold: bool


@dataclass
class Line:
    text: str
    bbox: Tuple[float, float, float, float]
    spans: List[Span]

    def majority_font_size(self) -> Optional[float]:
        if not self.spans:
            return None
        size_weight: Dict[float, int] = defaultdict(int)
        for s in self.spans:
            size_weight[s.size] += len(s.text)
        return max(size_weight.items(), key=lambda kv: kv[1])[0]

    def majority_font_name(self) -> Optional[str]:
        if not self.spans:
            return None
        font_weight: Dict[str, int] = defaultdict(int)
        for s in self.spans:
            font_weight[s.font] += len(s.text)
        return max(font_weight.items(), key=lambda kv: kv[1])[0]

    def majority_is_bold(self) -> bool:
        if not self.spans:
            return False
        w_bold, w_all = 0, 0
        for s in self.spans:
            w = len(s.text)
            w_all += w
            if s.is_bold:
                w_bold += w
        return w_bold >= (w_all / 2 if w_all else 0)


@dataclass
class PageInfo:
    index: int
    width: float
    height: float


@dataclass
class BodyFontProfile:
    size: float
    font: Optional[str]


def open_document(pdf_path: Path) -> fitz.Document:
    return fitz.open(pdf_path)


def get_toc(doc: fitz.Document) -> List[Tuple[int, str, int]]:
    """
    Returns a zero-based TOC: (level, title, page_index)
    Built-in TOC entries are 1-based, so we subtract 1 (clamp to 0).
    """
    raw = []
    try:
        raw = doc.get_toc() or []
    except Exception as e:
        log.warning("Unable to read TOC: %s", e)
    # convert 1-based pages to 0-based
    toc_zero: List[Tuple[int, str, int]] = []
    for level, title, page in raw:
        idx = page - 1 if isinstance(page, int) else 0
        toc_zero.append((level, title, max(0, idx)))
    return toc_zero


def get_pages_info(doc: fitz.Document) -> List[PageInfo]:
    infos: List[PageInfo] = []
    for i, page in enumerate(doc):
        r = page.rect
        infos.append(PageInfo(index=i, width=r.width, height=r.height))
    return infos


def get_page_number_map(doc: fitz.Document) -> List[int]:
    """
    Returns a list of 0-based page numbers.
    - If the PDF has exactly one page, always returns [0].
    - Otherwise:
        • Numeric page labels ("1", "2", ...) are converted to 0-based.
        • Unlabeled pages fall back to their raw 0-based indices.
    """
    if len(doc) == 1:
        return [0]

    nums: List[int] = []
    for i, page in enumerate(doc):
        try:
            label = page.get_label() or ""
            stripped = label.strip()
            if stripped.isdigit():
                nums.append(int(stripped) - 1)
                continue
        except Exception:
            pass
        nums.append(i)
    return nums


def iter_page_lines(doc: fitz.Document, page_index: int) -> Iterator[Line]:
    page = doc[page_index]
    text_dict = page.get_text("dict")

    for block in text_dict.get("blocks", []):
        if block.get("type", 0) != 0:
            continue
        for l in block.get("lines", []):
            spans_raw = l.get("spans", [])
            spans: List[Span] = []
            for s in spans_raw:
                text = s.get("text", "") or ""
                size = float(s.get("size", 0.0))
                font = s.get("font", "") or ""
                flags = int(s.get("flags", 0))
                bbox = tuple(s.get("bbox", (0.0, 0.0, 0.0, 0.0)))
                is_bold = is_bold_span(font, flags)
                spans.append(Span(text=text, size=size, font=font, flags=flags, bbox=bbox, is_bold=is_bold))
            if spans:
                x0 = min(s.bbox[0] for s in spans)
                y0 = min(s.bbox[1] for s in spans)
                x1 = max(s.bbox[2] for s in spans)
                y1 = max(s.bbox[3] for s in spans)
                bbox = (x0, y0, x1, y1)
                text_line = "".join(s.text for s in spans).strip()
                yield Line(text=text_line, bbox=bbox, spans=spans)


def infer_body_font_profile(
    doc: fitz.Document,
    sample_pages: int = 3,
    use_median_font_size: bool = False,
) -> BodyFontProfile:
    size_weights: Dict[float, int] = defaultdict(int)
    font_weights: Dict[str, int] = defaultdict(int)
    all_sizes: List[float] = []
    pages_to_scan = min(len(doc), max(1, sample_pages))
    for page_idx in range(pages_to_scan):
        for _, line in [(page_idx, l) for l in iter_page_lines(doc, page_idx)]:
            for span in line.spans:
                w = len(span.text)
                size_weights[span.size] += w
                if span.font:
                    font_weights[span.font] += w
                if w > 0:
                    all_sizes.extend([span.size] * w)
    if not size_weights:
        return BodyFontProfile(size=12.0, font=None)
    if use_median_font_size and all_sizes:
        try:
            body_size = float(statistics.median(all_sizes))
        except statistics.StatisticsError:
            body_size = max(size_weights.items(), key=lambda kv: kv[1])[0]
    else:
        body_size = max(size_weights.items(), key=lambda kv: kv[1])[0]
    body_font = None
    if font_weights:
        body_font = max(font_weights.items(), key=lambda kv: kv[1])[0]
    return BodyFontProfile(size=body_size, font=body_font)


def is_bold_span(font_name: str, flags: int) -> bool:
    fname_lower = (font_name or "").lower()
    return any(t in fname_lower for t in ("bold", "black", "heavy", "semibold", "demibold"))


def fallback_to_ocr(pdf_path: Path) -> List[Tuple[int, str]]:
    """
    OCR fallback: returns a list of (page_index, text) tuples.
    Enforces zero-based indexing, and for single-page PDFs always returns [(0, text)].
    """
    doc = fitz.open(pdf_path)
    # Single-page override
    if len(doc) == 1:
        page = doc[0]
        text = page.get_text("text")  # or your OCR pipeline here
        return [(0, text)]

    results: List[Tuple[int, str]] = []
    for i, page in enumerate(doc):
        text = page.get_text("text")  # replace with actual OCR if needed
        results.append((i, text))
    return results


__all__ = [
    "Span",
    "Line",
    "PageInfo",
    "BodyFontProfile",
    "open_document",
    "get_toc",
    "get_pages_info",
    "get_page_number_map",
    "iter_page_lines",
    "infer_body_font_profile",
    "is_bold_span",
    "fallback_to_ocr",
]
