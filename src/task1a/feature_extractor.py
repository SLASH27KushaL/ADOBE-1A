from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import List, Tuple
import fitz

from src.common.config import Task1AConfig
from src.common import pdf_reader as pr

_CORE_STRIP_RE = re.compile(r"[\s.,!?'\-_*:;(){}\[\]]")
WORD_RE = re.compile(r"\b\w[\w'-]*\b")
NUMERIC_PREFIX_RE = re.compile(r'^\s*((\d+(\.\d+)*\.)|\(\d+\)|\d+\))')

@dataclass
class FeatureRow:
    page_index0: int
    page_num1: int
    text: str
    bbox: Tuple[float, float, float, float]

    line_font_size: float
    is_bold_majority: bool

    y_position: float
    width_ratio: float
    vertical_gap: float
    gap_below: float
    gap_above_z: float
    gap_below_z: float

    font_size_ratio: float
    has_numeric_prefix: int
    word_count: int
    center_deviation: float
    size_vs_prev: float
    page_top_distance: float
    char_count: int

    ends_with_colon: int
    ends_with_period: int
    title_case_ratio: float
    uppercase_ratio: float

    page_width: float
    page_height: float

def extract_features(
    doc: fitz.Document,
    pages_info: List[pr.PageInfo],
    body_profile: pr.BodyFontProfile,
    cfg: Task1AConfig,
    page_nums: List[int],
) -> List[FeatureRow]:
    results: List[FeatureRow] = []
    body_font_size = max(1e-6, body_profile.size)

    for pinfo in pages_info:
        lines = list(pr.iter_page_lines(doc, pinfo.index))

        # compute raw gaps
        raw_gaps_above = []
        raw_gaps_below = []

        prev_bottom = 0.0
        first_on_page = True
        for i, line in enumerate(lines):
            x0, y0, x1, y1 = line.bbox
            if first_on_page:
                gap_above = y0  # distance from page top
                first_on_page = False
            else:
                gap_above = max(0.0, y0 - prev_bottom)
            raw_gaps_above.append(gap_above)
            prev_bottom = y1

        # compute gap_below per line
        for i, line in enumerate(lines):
            if i == len(lines) - 1:
                gap_below = (pinfo.height - lines[i].bbox[3])  # to page bottom
            else:
                gap_below = max(0.0, lines[i + 1].bbox[1] - lines[i].bbox[3])
            raw_gaps_below.append(gap_below)

        # stats (page-level or doc-level)
        gaps_above = [g for g in raw_gaps_above if g is not None]
        gaps_below = [g for g in raw_gaps_below if g is not None]

        def _safe_stats(data):
            if not data:
                return 0.0, 1.0
            mu = statistics.mean(data)
            sd = statistics.pstdev(data) or 1.0
            return mu, sd

        if cfg.spatial.use_page_stats:
            mu_above, sd_above = _safe_stats(gaps_above)
            mu_below, sd_below = _safe_stats(gaps_below)
        else:
            # (You could compute once across doc; keeping page-only here for simplicity)
            mu_above, sd_above = _safe_stats(gaps_above)
            mu_below, sd_below = _safe_stats(gaps_below)

        printed_page_num = page_nums[pinfo.index] if pinfo.index < len(page_nums) else (pinfo.index + 1)

        prev_font_size = body_font_size
        page_w, page_h = pinfo.width, pinfo.height

        for i, line in enumerate(lines):
            text = (line.text or "").strip()
            core_len = _core_len(text)
            if core_len < cfg.filtering.min_core_chars:
                continue

            line_font_size = line.majority_font_size() or body_font_size
            is_bold_majority = line.majority_is_bold()

            x0, y0, x1, y1 = line.bbox
            width_ratio = (x1 - x0) / page_w if page_w > 0 else 0.0

            gap_above = raw_gaps_above[i]
            gap_below = raw_gaps_below[i]

            gap_above_z = (gap_above - mu_above) / sd_above if sd_above > 0 else 0.0
            gap_below_z = (gap_below - mu_below) / sd_below if sd_below > 0 else 0.0

            font_size_ratio = line_font_size / body_font_size
            size_vs_prev = line_font_size / (prev_font_size or line_font_size)

            line_center = (x0 + x1) / 2.0
            page_center = page_w / 2.0
            denom = (page_w / 2.0) if page_w > 0 else 1.0
            center_deviation = min(1.0, abs(line_center - page_center) / denom)

            page_top_distance = y0 / page_h if page_h > 0 else 0.0

            has_numeric_prefix = 1 if NUMERIC_PREFIX_RE.match(text) else 0
            words = WORD_RE.findall(text)
            word_count = len(words)

            ends_with_colon = 1 if text.endswith(":") else 0
            ends_with_period = 1 if text.endswith(".") else 0
            title_case_ratio = _title_case_ratio(words)
            uppercase_ratio = _uppercase_ratio(text)

            row = FeatureRow(
                page_index0=pinfo.index,
                page_num1=printed_page_num,
                text=line.text,
                bbox=line.bbox,
                line_font_size=line_font_size,
                is_bold_majority=is_bold_majority,
                y_position=y0,
                width_ratio=width_ratio,
                vertical_gap=gap_above,
                gap_below=gap_below,
                gap_above_z=gap_above_z,
                gap_below_z=gap_below_z,
                font_size_ratio=font_size_ratio,
                has_numeric_prefix=has_numeric_prefix,
                word_count=word_count,
                center_deviation=center_deviation,
                size_vs_prev=size_vs_prev,
                page_top_distance=page_top_distance,
                char_count=core_len,
                ends_with_colon=ends_with_colon,
                ends_with_period=ends_with_period,
                title_case_ratio=title_case_ratio,
                uppercase_ratio=uppercase_ratio,
                page_width=page_w,
                page_height=page_h,
            )
            results.append(row)

            prev_font_size = line_font_size

    return results

def _core_len(text: str) -> int:
    return len(_CORE_STRIP_RE.sub("", text or ""))

def _is_title_case(w: str) -> bool:
    if not w:
        return False
    if len(w) == 1:
        return w[0].isupper()
    return w[0].isupper() and w[1:].islower()

def _title_case_ratio(words: List[str]) -> float:
    if not words:
        return 0.0
    return sum(_is_title_case(w) for w in words) / len(words)

def _uppercase_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)
