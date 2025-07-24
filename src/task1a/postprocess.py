from __future__ import annotations

import re
from typing import List, Dict

from src.common.config import Task1AConfig
from src.task1a.level_classifier import LabeledHeading
from src.task1a.hierarchy import renormalize_by_number_tree

_LEVEL2INT = {"H1": 1, "H2": 2, "H3": 3}
_INT2LEVEL = {1: "H1", 2: "H2", 3: "H3"}

_NORMALIZE_WS = re.compile(r"\s+")

def build_outline(
    labeled_headings: List[LabeledHeading],
    cfg: Task1AConfig,
) -> List[Dict]:
    if not labeled_headings:
        return []

    labeled_headings.sort(key=lambda h: (h.page_index0, h.y_position))

    drop_fp = cfg.filtering.drop_first_page_headings_from_outline
    kw = cfg.keywords
    kw_list = set(k.lower() for k in kw.list) if kw.enabled else set()

    all_pages = [h.page_num1 for h in labeled_headings]
    first_page_num = min(all_pages) if all_pages else 0

    raw_outline: List[Dict] = []
    seen_key = set()
    last_level_int = 0

    first_h1_seen = {}

    for h in labeled_headings:
        if drop_fp and h.page_num1 == first_page_num:
            continue

        level_int = _LEVEL2INT.get(h.level, 3)
        if last_level_int == 0:
            normalized_level_int = level_int
        else:
            if level_int > last_level_int + 1:
                normalized_level_int = min(last_level_int + 1, 3)
            else:
                normalized_level_int = level_int
        normalized_level = _INT2LEVEL[normalized_level_int]

        if normalized_level == "H1":
            if h.page_num1 in first_h1_seen:
                normalized_level = "H2"
            else:
                first_h1_seen[h.page_num1] = True

        key = (h.page_num1, _normalize_text(h.text))
        if key in seen_key:
            continue
        seen_key.add(key)

        if kw.enabled and kw.force_h1_if_early and (h.page_num1 <= kw.force_h1_max_page):
            if (h.text or "").strip().lower() in kw_list:
                normalized_level = "H1"

        raw_outline.append(
            {
                "level": normalized_level,
                "text": h.text.strip(),
                "page": h.page_num1,
                "score": h.score,
            }
        )
        last_level_int = _LEVEL2INT[normalized_level]

    outline = renormalize_by_number_tree(
        raw_outline,
        appendix_base_level=cfg.hierarchy.appendix_base_level,
        appendix_children_bump=cfg.hierarchy.appendix_children_bump,
    )

    outline = _merge_trailing_short_tokens(outline)

    return outline

def _normalize_text(text: str) -> str:
    return _NORMALIZE_WS.sub(" ", (text or "").strip().lower())

def _merge_trailing_short_tokens(outline: List[Dict]) -> List[Dict]:
    if not outline:
        return outline

    merged: List[Dict] = []
    for item in outline:
        if not merged:
            merged.append(item)
            continue

        prev = merged[-1]
        txt = item["text"].strip()
        if (
            item["page"] == prev["page"]
            and len(txt.split()) <= 2
            and not _looks_numbered(txt)
            and item["level"] == prev["level"]
        ):
            prev["text"] = (prev["text"].rstrip() + " " + txt).strip()
            prev["score"] = max(prev.get("score", 0), item.get("score", 0))
        else:
            merged.append(item)
    return merged

def _looks_numbered(text: str) -> bool:
    return bool(re.match(r"^\s*\d+(\.\d+)*", text or ""))

__all__ = ["build_outline"]
