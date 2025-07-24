from __future__ import annotations

from collections import Counter
from typing import Iterable, Set

from src.common.config import Task1AConfig
from src.task1a.feature_extractor import FeatureRow

def _norm_exact(text: str) -> str:
    # exact whole-line match: lowercase + collapse whitespace
    return " ".join((text or "").strip().split()).lower()

def find_repeated_headings(rows: Iterable[FeatureRow], cfg: Task1AConfig) -> Set[str]:
    rep = cfg.repetition
    if not rep.enable:
        return set()

    counts = Counter()
    for r in rows:
        if r.word_count == 0 or r.word_count > rep.max_words:
            continue
        t = _norm_exact(r.text)
        if t:
            counts[t] += 1

    return {t for t, c in counts.items() if c >= rep.min_occurrences}

def is_repeated_exact(text: str, repeated: Set[str]) -> bool:
    return _norm_exact(text) in repeated
