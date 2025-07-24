from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import List, Tuple

from src.common.config import Task1AConfig, SalienceConfig
from src.task1a.heuristics import HeadingCandidate

@dataclass
class LabeledHeading:
    level: str
    page_index0: int
    page_num1: int
    text: str
    score: int

    font_size_ratio: float
    line_font_size: float
    is_bold_majority: bool
    page_top_distance: float
    y_position: float
    width_ratio: float
    vertical_gap: float
    gap_below: float
    gap_above_z: float
    gap_below_z: float
    size_vs_prev: float
    char_count: int
    word_count: int
    has_numeric_prefix: int
    center_deviation: float

    bbox: Tuple[float, float, float, float]

_NUM_SINGLE_OR_NESTED = re.compile(r'^\s*(\d+(\.\d+)*)(?:\s|$)')

def assign_levels(
    heading_candidates: List[HeadingCandidate],
    cfg: Task1AConfig,
) -> List[LabeledHeading]:
    if not heading_candidates:
        return []

    sal_cfg: SalienceConfig = cfg.salience
    font_ratios = [h.font_size_ratio for h in heading_candidates]
    use_salience = False

    try:
        if sal_cfg.enable and len(font_ratios) > 1:
            std_ratio = statistics.pstdev(font_ratios)
            distinct = len({round(r, 2) for r in font_ratios})
            use_salience = (std_ratio < sal_cfg.font_ratio_std_epsilon) or (distinct <= 2)
    except Exception:
        use_salience = False

    if use_salience:
        return _assign_levels_salience(heading_candidates, cfg, sal_cfg)

    out: List[LabeledHeading] = []
    for hc in heading_candidates:
        level = _decide_level(
            text=hc.text,
            font_size_ratio=hc.font_size_ratio,
            page_top_distance=hc.page_top_distance,
            cfg=cfg,
        )
        out.append(_mk_label(hc, level))
    return out

def _mk_label(hc: HeadingCandidate, level: str) -> LabeledHeading:
    return LabeledHeading(
        level=level,
        page_index0=hc.page_index0,
        page_num1=hc.page_num1,
        text=hc.text,
        score=hc.score,
        font_size_ratio=hc.font_size_ratio,
        line_font_size=hc.line_font_size,
        is_bold_majority=hc.is_bold_majority,
        page_top_distance=hc.page_top_distance,
        y_position=hc.y_position,
        width_ratio=hc.width_ratio,
        vertical_gap=hc.vertical_gap,
        gap_below=hc.gap_below,
        gap_above_z=hc.gap_above_z,
        gap_below_z=hc.gap_below_z,
        size_vs_prev=hc.size_vs_prev,
        char_count=hc.char_count,
        word_count=hc.word_count,
        has_numeric_prefix=hc.has_numeric_prefix,
        center_deviation=hc.center_deviation,
        bbox=hc.bbox,
    )

def _decide_level(text: str, font_size_ratio: float, page_top_distance: float, cfg: Task1AConfig) -> str:
    lvl = _infer_level_from_numbering(text)
    if lvl is not None:
        return lvl

    h1 = cfg.levels.h1
    h2 = cfg.levels.h2

    if (font_size_ratio >= h1.rel_font_min) or (page_top_distance <= h1.page_top_pct_max):
        return "H1"
    if (font_size_ratio >= h2.rel_font_min) or (page_top_distance <= h2.page_top_pct_max):
        return "H2"
    return "H3"

def _infer_level_from_numbering(text: str) -> str | None:
    m = _NUM_SINGLE_OR_NESTED.match(text or "")
    if not m:
        return None
    dot_cnt = m.group(1).count(".")
    depth = dot_cnt + 1
    if depth <= 1:
        return "H1"
    if depth == 2:
        return "H2"
    return "H3"

def _assign_levels_salience(
    heading_candidates: List[HeadingCandidate],
    cfg: Task1AConfig,
    sal_cfg: SalienceConfig,
) -> List[LabeledHeading]:
    scores = _compute_salience_scores(heading_candidates, sal_cfg)
    vals = [scores[id(h)] for h in heading_candidates]
    q_h1, q_h2 = _quantiles(vals, sal_cfg.q_h1, sal_cfg.q_h2)

    out: List[LabeledHeading] = []
    for hc in heading_candidates:
        level = _map_by_quantile(scores[id(hc)], q_h1, q_h2)
        out.append(_mk_label(hc, level))
    return out

def _compute_salience_scores(
    heading_candidates: List[HeadingCandidate],
    sal_cfg: SalienceConfig,
) -> dict[int, float]:
    import statistics
    vertical_gaps = [hc.vertical_gap for hc in heading_candidates]
    try:
        mean_vg = statistics.mean(vertical_gaps)
        std_vg = statistics.pstdev(vertical_gaps) or 1.0
    except statistics.StatisticsError:
        mean_vg, std_vg = 0.0, 1.0

    max_words = max((hc.word_count for hc in heading_candidates), default=1)

    scores: dict[int, float] = {}
    W = sal_cfg.weights

    for hc in heading_candidates:
        z_vgap = (hc.vertical_gap - mean_vg) / std_vg
        salience = 0.0
        salience += W.bold * (1.0 if hc.is_bold_majority else 0.0)
        salience += W.center * (1.0 - hc.center_deviation)
        salience += W.vertical_gap_z * z_vgap
        salience += W.topness * (1.0 - hc.page_top_distance)
        salience += W.numeric_prefix * (1.0 if hc.has_numeric_prefix else 0.0)
        short_line_bonus = 1.0 if hc.char_count <= 100 else 0.0
        salience += W.short_line * short_line_bonus
        word_norm = hc.word_count / max_words if max_words > 0 else 0.0
        salience += W.word_count_norm * word_norm

        scores[id(hc)] = salience

    return scores

def _quantiles(vals: List[float], q1: float, q2: float) -> Tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    xs = sorted(vals)
    n = len(xs)

    def _pick(q: float) -> float:
        if n == 1:
            return xs[0]
        pos = q * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        return xs[lo] * (1 - frac) + xs[hi] * frac

    return _pick(q1), _pick(q2)

def _map_by_quantile(val: float, q_h1: float, q_h2: float) -> str:
    if val >= q_h1:
        return "H1"
    if val >= q_h2:
        return "H2"
    return "H3"

__all__ = ["LabeledHeading", "assign_levels"]
