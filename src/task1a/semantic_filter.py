from __future__ import annotations

import re
from typing import List, Set
from functools import lru_cache

from src.common.config import Task1AConfig, SemanticFilterConfig
from src.task1a.heuristics import HeadingCandidate

_NUM_RE = re.compile(r'^\s*\d+(\.\d+)*')  # keep numbered headings


def filter_candidates(cands: List[HeadingCandidate], cfg: Task1AConfig) -> List[HeadingCandidate]:
    sf: SemanticFilterConfig = cfg.semantic_filter
    if not sf.enable:
        return cands

    out: List[HeadingCandidate] = []
    use_spacy = sf.use_spacy
    nlp = _get_nlp_by_model(sf.model) if use_spacy else None
    content_pos: Set[str] = set(sf.content_pos)

    for c in cands:
        text = (c.text or "").strip()

        # always keep numbered headings
        if _NUM_RE.match(text):
            out.append(c)
            continue

        # alpha ratio quick check
        if not _passes_alpha_ratio(text, sf.min_alpha_ratio):
            continue

        # accept acronyms / all caps like "RFP", "ODL" if length >= min
        if _looks_all_caps_acronym(text, sf.accept_all_caps_minlen):
            out.append(c)
            continue

        # long candidates: skip spacy (too slow, likely already meaningful)
        if len(text) > sf.max_chars:
            out.append(c)
            continue

        if use_spacy and nlp is not None:
            if _spacy_semantically_ok(text, nlp, content_pos, sf.require_content_pos):
                out.append(c)
            else:
                # drop meaningless shard
                pass
        else:
            # Fallback: simple acceptance on alpha-ratio only
            out.append(c)

    return out


def _passes_alpha_ratio(text: str, min_ratio: float) -> bool:
    letters = [c for c in text if c.isalpha()]
    total = sum(1 for c in text if not c.isspace())
    if total == 0:
        return False
    return (len(letters) / total) >= min_ratio


def _looks_all_caps_acronym(text: str, minlen: int) -> bool:
    letters = "".join([c for c in text if c.isalpha()])
    return len(letters) >= minlen and letters.isupper()


def _spacy_semantically_ok(
    text: str,
    nlp,
    content_pos: Set[str],
    require_content_pos: bool
) -> bool:
    doc = nlp(text)
    if not require_content_pos:
        return True
    for tok in doc:
        if tok.is_alpha and tok.pos_ in content_pos and len(tok.text) > 2:
            return True
    return False


@lru_cache(maxsize=4)
def _get_nlp_by_model(model_name: str):
    """Cache spaCy model by its name (hashable)."""
    try:
        import spacy
        return spacy.load(model_name)
    except Exception as e:
        print(f"[semantic_filter] Could not load spaCy model '{model_name}': {e}")
        return None
