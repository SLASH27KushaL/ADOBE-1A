from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from src.common.config import Task1AConfig
from src.common import pdf_reader as pr
from src.task1a import semantic_filter


from src.task1a import (
    tagged_extractor,
    feature_extractor,
    heuristics,
    level_classifier,
    postprocess,
    promotion,
    writer,
    repetition,
)

log = logging.getLogger(__name__)

def run_pipeline(pdf_path: Path, cfg: Task1AConfig) -> Dict[str, Any]:
    with pr.open_document(pdf_path) as doc:
        toc = pr.get_toc(doc)
        if len(toc) >= cfg.tagged.min_toc_entries:
            log.debug("Tagged / TOC detected: using fast-path extractor for %s", pdf_path.name)
            tagged_result = tagged_extractor.extract(doc, toc, cfg)
            if tagged_result is not None:
                return writer.make_output_from_tagged(tagged_result, cfg)

        log.debug("Heuristic path for %s", pdf_path.name)

        body_profile = pr.infer_body_font_profile(
            doc,
            sample_pages=cfg.body_profile.sample_pages,
            use_median_font_size=cfg.body_profile.use_median_font_size,
        )

        pages_info = pr.get_pages_info(doc)
        page_nums = _make_page_numbers(doc, cfg)

        feature_rows = feature_extractor.extract_features(
            doc=doc,
            pages_info=pages_info,
            body_profile=body_profile,
            cfg=cfg,
            page_nums=page_nums,
        )

        repeated_titles = repetition.find_repeated_headings(feature_rows, cfg)

        heading_candidates = heuristics.detect_headings(
            feature_rows=feature_rows,
            cfg=cfg,
            repeated_titles=repeated_titles,
        )
        heading_candidates = semantic_filter.filter_candidates(heading_candidates, cfg)


        labeled_headings = level_classifier.assign_levels(
            heading_candidates=heading_candidates,
            cfg=cfg,
        )

        labeled_headings = promotion.promote_non_numbered(labeled_headings, cfg)

        structured_outline = postprocess.build_outline(
            labeled_headings=labeled_headings,
            cfg=cfg,
        )

        result = writer.make_output_from_outline(
            outline=structured_outline,
            cfg=cfg,
        )

        return result

def _make_page_numbers(doc, cfg: Task1AConfig) -> List[int]:
    pn = cfg.page_numbering
    mode = pn.mode
    offset = pn.offset

    n_pages = len(doc)

    if mode == "labels":
        nums = pr.get_page_number_map(doc, fallback_offset=0)
        return [n + offset for n in nums]

    if mode == "index0":
        return [i + offset for i in range(n_pages)]

    return [i + 1 + offset for i in range(n_pages)]
