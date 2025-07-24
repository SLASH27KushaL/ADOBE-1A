# src/task1a/tagged_extractor.py
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from src.common.config import Task1AConfig
from src.common import pdf_reader as pr

log = logging.getLogger(__name__)


@dataclass
class TaggedHeading:
    level: str          # "H1" | "H2" | "H3"
    text: str
    page: int           # 1-based


def extract(doc: fitz.Document,
            toc: List[Tuple[int, str, int]],
            cfg: Task1AConfig) -> Optional[List[TaggedHeading]]:
    """
    Convert PyMuPDF's TOC into a normalized list of TaggedHeading.
    Return None if the TOC is empty or unusable (so the caller can fall back to heuristics).

    PyMuPDF TOC tuple format: (level:int, title:str, page:int[1-based])
    We collapse:
        level <= 1  -> H1
        level == 2  -> H2
        level >= 3  -> H3
    """
    if not toc:
        return None

    headings: List[TaggedHeading] = []
    min_chars = cfg.filtering.min_core_chars

    for lvl, title, page in toc:
        text = (title or "").strip()
        if _core_len(text) < min_chars:
            # skip noise / ultra-short items
            continue

        h = _map_level_to_h(lvl)
        page_num = max(1, int(page))  # TOC already 1-based, just sanitize
        headings.append(TaggedHeading(level=h, text=text, page=page_num))

    if not headings:
        return None

    return headings


# -------------------------
# helpers
# -------------------------

_CORE_STRIP_RE = re.compile(r"[\s.,!?'\-_*:;(){}\[\]]")


def _core_len(text: str) -> int:
    """Length after stripping whitespace & specials."""
    return len(_CORE_STRIP_RE.sub("", text))


def _map_level_to_h(toc_level: int) -> str:
    """
    Map arbitrary TOC levels to H1 / H2 / H3.
    """
    if toc_level <= 1:
        return "H1"
    if toc_level == 2:
        return "H2"
    return "H3"


__all__ = ["TaggedHeading", "extract"]
