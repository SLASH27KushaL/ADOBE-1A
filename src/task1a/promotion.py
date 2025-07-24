from __future__ import annotations

from typing import List
from src.common.config import Task1AConfig, PromotionConfig
from src.task1a.level_classifier import LabeledHeading
import re

_NUM_RE = re.compile(r'^\s*\d+(\.\d+)*')

def promote_non_numbered(headings: List[LabeledHeading], cfg: Task1AConfig) -> List[LabeledHeading]:
    prom: PromotionConfig = cfg.promotion
    if not prom.enable or not headings:
        return headings

    ratios = [h.font_size_ratio for h in headings if not _is_numbered(h.text)]
    ratios_sorted = sorted(ratios)
    q_h2 = _quantile(ratios_sorted, prom.h2_q)

    for h in headings:
        if _is_numbered(h.text):
            continue
        # only promote to H2 at most
        if h.font_size_ratio >= q_h2 and h.level == "H3":
            h.level = "H2"

    return headings

def _is_numbered(text: str) -> bool:
    return bool(_NUM_RE.match(text or ""))

def _quantile(xs, q):
    if not xs:
        return 0.0
    n = len(xs)
    if n == 1:
        return xs[0]
    pos = q * (n - 1)
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac
