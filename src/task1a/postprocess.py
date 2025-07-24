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
            # prevent jumps like H1 -> H3
            if level_int > last_level_int + 1:
                normalized_level_int = min(last_level_int + 1, 3)
            else:
                normalized_level_int = level_int
        normalized_level = _INT2LEVEL[normalized_level_int]

        # same-page duplicate H1 demotion
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

    # hierarchy re-normalization based on numbering & appendix
    outline = renormalize_by_number_tree(
        raw_outline,
        appendix_base_level=cfg.hierarchy.appendix_base_level,
        appendix_children_bump=cfg.hierarchy.appendix_children_bump,
    )

    # stricter merge of trailing short tokens
    outline = _merge_trailing_short_tokens(outline)

    return outline

def _normalize_text(text: str) -> str:
    return _NORMALIZE_WS.sub(" ", (text or "").strip().lower())

def _merge_trailing_short_tokens(outline: List[Dict]) -> List[Dict]:
    """
    Stricter: only merge when:
      - same page & same level
      - the second text is <= 2 words
      - the second text does NOT look like a heading (title-cased / long alpha)
      - and either:
          * previous text ends with ':', '-' or '—'
          * OR the score difference is tiny (<= 1)
    """
    if not outline:
        return outline

    merged: List[Dict] = []
    for item in outline:
        if not merged:
            merged.append(item)
            continue

        prev = merged[-1]

        # Basic guards
        if item["page"] != prev["page"]:
            merged.append(item)
            continue
        if item["level"] != prev["level"]:
            merged.append(item)
            continue

        txt = (item["text"] or "").strip()
        if _should_merge(prev, item, txt):
            prev["text"] = (prev["text"].rstrip() + " " + txt).strip()
            prev["score"] = max(prev.get("score", 0), item.get("score", 0))
        else:
            merged.append(item)

    return merged

def _should_merge(prev: Dict, item: Dict, txt: str) -> bool:
    # word length constraint
    words = txt.split()
    if len(words) == 0 or len(words) > 2:
        return False

    # never merge if it looks like a numbered header (e.g., "2.1", "1", "3)")
    if _looks_numbered(txt):
        return False

    # prevent merging something that "looks like a heading"
    if _looks_heading_like(txt):
        return False

    # Allow if the previous text ends with a connector
    if prev["text"].rstrip().endswith((':', '-', '—')):
        return True

    # Otherwise require scores to be very close (likely same visual line broken)
    prev_sc = prev.get("score", 0)
    cur_sc = item.get("score", 0)
    if abs(prev_sc - cur_sc) <= 1:
        return True

    return False

def _looks_heading_like(text: str) -> bool:
    """
    A simplistic heuristic: looks like a heading if
    - contains >= 3 alphabetic letters and
    - at least one word starts with uppercase (TitleCase-like),
    - or it's all uppercase and at least 2 letters long
    """
    alpha = [c for c in text if c.isalpha()]
    if len(alpha) >= 3:
        words = text.split()
        has_titleish = any(w[:1].isupper() for w in words if w)
        all_upper = "".join(alpha).isupper()
        if has_titleish or (all_upper and len(alpha) >= 2):
            return True
    return False

def _looks_numbered(text: str) -> bool:
    return bool(re.match(r"^\s*\d+(\.\d+)*", text or ""))

__all__ = ["build_outline"]
