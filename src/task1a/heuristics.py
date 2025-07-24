from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Set, Dict
import re
from collections import defaultdict, Counter

from src.common.config import Task1AConfig
from src.task1a.feature_extractor import FeatureRow
from src.task1a.repetition import is_repeated_exact

NUM_PATTERN = re.compile(r'^\s*\d+(\.\d+)+\s')
BULLET_RE = re.compile(r'^\s*[\-\u2022\*]\s+')

@dataclass
class HeadingCandidate:
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

def detect_headings(
    feature_rows: List[FeatureRow],
    cfg: Task1AConfig,
    repeated_titles: Set[str] | None = None,
) -> List[HeadingCandidate]:
    sc = cfg.scoring
    filt = cfg.filtering
    kw = cfg.keywords
    rep_cfg = cfg.repetition
    sp = cfg.spatial
    ctx = cfg.context
    rec = cfg.recipe

    repeated_titles = repeated_titles or set()

    rows = sorted(feature_rows, key=lambda r: (r.page_index0, r.y_position))
    bullet_flags = [is_bullet_like(r.text) for r in rows]
    kw_set = set(k.lower().strip() for k in kw.list) if kw.enabled else set()

    # Page-level repetition
    page_counts: Dict[int, Counter] = defaultdict(Counter)
    short_norm_texts: List[str] = []
    for r in rows:
        t_norm = norm_text(r.text)
        short_norm_texts.append(t_norm)
        if r.word_count > 0 and r.word_count <= rep_cfg.max_words and t_norm:
            page_counts[r.page_index0][t_norm] += 1

    # Recipe back-link
    recipe_forced_indices: Set[int] = set()
    if rec.enable:
        labels = set(l.lower() for l in rec.labels)
        for i, r in enumerate(rows):
            t = (r.text or "").strip().lower()
            if t in labels:
                back = max(0, i - rec.back_look_lines)
                for j in range(i - 1, back - 1, -1):
                    rj = rows[j]
                    tj = (rj.text or "").strip()
                    w = rj.word_count
                    if w >= rec.min_title_words and w <= rec.max_title_words:
                        if not tj.endswith(":") and not is_bullet_like(tj):
                            recipe_forced_indices.add(j)
                            break

    # Context bullet-block
    context_bonus_indices: Set[int] = set()
    if ctx.enable:
        k = ctx.k_lookahead
        for i, r in enumerate(rows):
            if r.word_count == 0 or r.word_count > 12:
                continue
            limit = min(len(rows), i + 1 + k)
            bullets = 0
            for j in range(i + 1, limit):
                if rows[j].page_index0 != r.page_index0:
                    break
                if bullet_flags[j]:
                    bullets += 1
                if rows[j].word_count > 25:
                    break
            if bullets >= ctx.min_bullets:
                context_bonus_indices.add(i)

    out: List[HeadingCandidate] = []

    for i, row in enumerate(rows):
        score = 0
        rules_fired = 0

        # penalty if smaller than body font
        if row.font_size_ratio < 1.0:
            score += sc.rel_font_below_body_penalty

        # 1) Relative font size
        if row.font_size_ratio > sc.rel_font_size_threshold:
            score += sc.rel_font_size_score; rules_fired += 1

        # 2) Bold
        if row.is_bold_majority:
            score += sc.is_bold_score; rules_fired += 1

        # 3) Top-of-page
        if row.page_top_distance <= sc.top_pct_threshold:
            score += sc.top_pct_score; rules_fired += 1

        # 4) Vertical gap (above)
        if row.vertical_gap > (sc.vertical_gap_multiplier * row.line_font_size):
            score += sc.vertical_gap_score; rules_fired += 1

        # 5) Short-ish line (<= max_heading_chars)
        if row.char_count <= filt.max_heading_chars:
            score += sc.short_line_score; rules_fired += 1

        # NEW 5b) Very short line (<= very_short_char_threshold)
        if row.char_count <= sc.very_short_char_threshold:
            score += sc.very_short_line_score; rules_fired += 1

        # 6) Numeric prefix
        if row.has_numeric_prefix:
            score += sc.has_numeric_prefix_score; rules_fired += 1

        # 7) Ends with colon
        if row.ends_with_colon:
            score += sc.ends_with_colon_score; rules_fired += 1

        # 8) Title case ratio
        if row.title_case_ratio >= 0.6:
            score += sc.title_case_score; rules_fired += 1

        # 9) Uppercase ratio
        if row.uppercase_ratio >= 0.6 and row.char_count <= 60:
            score += sc.uppercase_ratio_score; rules_fired += 1

        # 10) Ends with period (penalize)
        if row.ends_with_period and not row.has_numeric_prefix:
            score += sc.ends_with_period_penalty

        # 11) Exact whole-line repetition (doc)
        if rep_cfg.enable and row.word_count <= rep_cfg.max_words:
            if is_repeated_exact(row.text, repeated_titles):
                score += rep_cfg.boost_score
                rules_fired += 1

        # 12) Block (page) repetition bonus
        if rep_cfg.enable and rep_cfg.block_scope == "page":
            t_norm = short_norm_texts[i]
            if t_norm and row.word_count <= rep_cfg.max_words:
                if page_counts[row.page_index0][t_norm] >= rep_cfg.min_occurrences_block:
                    score += rep_cfg.block_bonus
                    rules_fired += 1

        # 13) Spatial isolation
        if cfg.spatial.enable:
            above_ok = (row.gap_above_z >= sp.z_above_min)
            below_ok = (row.gap_below_z >= sp.z_below_min)
            if sp.first_line_on_page_ignore_above and row.vertical_gap == row.y_position:
                above_ok = False
            if above_ok and below_ok:
                score += sp.both_sides_bonus; rules_fired += 1
            elif above_ok or below_ok:
                score += sp.one_side_bonus; rules_fired += 1

        # 14) Context bullet-block lookahead
        if i in context_bonus_indices:
            score += ctx.bullet_block_bonus
            rules_fired += 1

        # 15) Recipe back-link force
        if i in recipe_forced_indices:
            need = max(0, sc.heading_score_threshold - score)
            score += need + 1
            rules_fired += 1

        # Bullet-like discount if weak
        if bullet_flags[i] and score < (sc.heading_score_threshold + 1):
            score -= 1

        # Keyword tie-breaker (FIXED: kw.max_chars)
        if kw.enabled and row.char_count <= kw.max_chars:
            txt_norm = (row.text or "").strip().lower()
            in_frontmatter = (row.page_num1 <= kw.force_h1_max_page) if kw.frontmatter_only else True
            if in_frontmatter and (score >= kw.apply_if_score_at_least) and (txt_norm in kw_set):
                score += min(kw.boost_score, kw.max_extra)

        force_pick = NUM_PATTERN.match(row.text or "") is not None

        accept = (
            (score >= sc.heading_score_threshold)
            or (rules_fired >= sc.min_rules_fired and score >= (sc.heading_score_threshold - 1))
            or force_pick
            or (i in recipe_forced_indices)
        )

        if accept:
            out.append(HeadingCandidate(
                page_index0=row.page_index0,
                page_num1=row.page_num1,
                text=row.text,
                score=score,
                font_size_ratio=row.font_size_ratio,
                line_font_size=row.line_font_size,
                is_bold_majority=row.is_bold_majority,
                page_top_distance=row.page_top_distance,
                y_position=row.y_position,
                width_ratio=row.width_ratio,
                vertical_gap=row.vertical_gap,
                gap_below=row.gap_below,
                gap_above_z=row.gap_above_z,
                gap_below_z=row.gap_below_z,
                size_vs_prev=row.size_vs_prev,
                char_count=row.char_count,
                word_count=row.word_count,
                has_numeric_prefix=row.has_numeric_prefix,
                center_deviation=row.center_deviation,
                bbox=row.bbox,
            ))

    return out

def is_bullet_like(text: str | None) -> bool:
    if not text:
        return False
    t = text.strip()
    if BULLET_RE.match(t):
        return True
    return False

def norm_text(text: str | None) -> str:
    return " ".join((text or "").strip().split()).lower()
