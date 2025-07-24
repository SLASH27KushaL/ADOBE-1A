from __future__ import annotations

import re
from typing import List, Dict, Any

from src.common.config import Task1AConfig
from src.task1a.tagged_extractor import TaggedHeading

_GARBAGE_RE = re.compile(r"(.)\s*\1\s*(\1|\s)*", re.IGNORECASE)

def make_output_from_tagged(tagged_headings: List[TaggedHeading], cfg: Task1AConfig) -> Dict[str, Any]:
    outline = [{"level": th.level, "text": th.text, "page": th.page, "score": 0} for th in tagged_headings]
    title = _select_title_from_outline(outline)
    return {"title": title, "outline": [{k: v for k, v in o.items() if k != "score"} for o in outline]}

def make_output_from_outline(outline: List[Dict[str, Any]], cfg: Task1AConfig) -> Dict[str, Any]:
    title = _select_title_from_outline(outline)
    return {"title": title, "outline": [{k: v for k, v in o.items() if k != "score"} for o in outline]}

def _select_title_from_outline(outline: List[Dict[str, Any]]) -> str:
    if not outline:
        return "Untitled Document"

    best = None
    best_score = -1
    for o in outline:
        if o.get("level") == "H1":
            txt = (o.get("text") or "").strip()
            if not _looks_garbage(txt):
                sc = o.get("score", 0)
                if sc > best_score:
                    best_score = sc
                    best = txt
    if best:
        return best

    for o in outline:
        if o.get("level") == "H1":
            txt = (o.get("text") or "").strip()
            if txt:
                return txt

    return (outline[0].get("text") or "").strip() or "Untitled Document"

def _looks_garbage(text: str) -> bool:
    if not text:
        return True
    no_space = re.sub(r"\s+", "", text)
    if len(no_space) < 3:
        return True
    return bool(_GARBAGE_RE.search(text))
