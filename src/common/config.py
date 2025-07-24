from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any
import yaml

# -------------------------
# Dataclasses
# -------------------------

@dataclass
class TimingConfig:
    hard_timeout_seconds: int = 10

@dataclass
class TaggedConfig:
    min_toc_entries: int = 1

@dataclass
class FilteringConfig:
    min_core_chars: int = 3
    max_heading_chars: int = 100
    drop_first_page_headings_from_outline: bool = False
    # (optional) when you want to drop tiny 1-word shards
    min_chars_single_word: int = 4

@dataclass
class BodyProfileConfig:
    sample_pages: int = 3
    use_median_font_size: bool = False

@dataclass
class ScoringConfig:
    rel_font_size_threshold: float = 1.15
    top_pct_threshold: float = 0.15
    vertical_gap_multiplier: float = 1.5

    rel_font_size_score: int = 2
    is_bold_score: int = 2
    top_pct_score: int = 1
    vertical_gap_score: int = 1
    short_line_score: int = 1
    has_numeric_prefix_score: int = 2

    ends_with_colon_score: int = 2
    title_case_score: int = 1
    uppercase_ratio_score: int = 1
    ends_with_period_penalty: int = -1

    rel_font_below_body_penalty: int = -2

    # very short heading boost
    very_short_char_threshold: int = 20
    very_short_line_score: int = 1

    semantic_boost_enabled: bool = False
    semantic_boost_score: int = 2
    semantic_sim_threshold: float = 0.5

    heading_score_threshold: int = 6
    min_rules_fired: int = 3

@dataclass
class LevelRule:
    rel_font_min: float
    page_top_pct_max: float

@dataclass
class LevelsConfig:
    h1: LevelRule
    h2: LevelRule
    h3: LevelRule

@dataclass
class SalienceWeights:
    bold: float = 2.0
    center: float = 2.0
    vertical_gap_z: float = 1.0
    topness: float = 1.0
    numeric_prefix: float = 1.0
    short_line: float = 0.5
    word_count_norm: float = -0.5

@dataclass
class SalienceConfig:
    enable: bool = True
    font_ratio_std_epsilon: float = 0.15
    q_h1: float = 0.85
    q_h2: float = 0.50
    weights: SalienceWeights = field(default_factory=SalienceWeights)

@dataclass
class KeywordsConfig:
    enabled: bool = True
    boost_score: int = 2
    max_extra: int = 1
    apply_if_score_at_least: int = 5
    max_chars: int = 80
    frontmatter_only: bool = True
    force_h1_if_early: bool = True
    force_h1_max_page: int = 5
    list: List[str] = field(default_factory=list)

@dataclass
class PageNumberingConfig:
    mode: str = "index1"
    offset: int = 0

@dataclass
class HierarchyConfig:
    appendix_base_level: int = 2
    appendix_children_bump: int = 1

@dataclass
class PromotionConfig:
    enable: bool = True
    allow_h1: bool = False
    h2_q: float = 0.85

@dataclass
class RepetitionConfig:
    enable: bool = True
    min_occurrences: int = 3
    max_words: int = 8
    boost_score: int = 2
    min_occurrences_block: int = 2
    block_scope: str = "page"
    block_bonus: int = 2

@dataclass
class SpatialConfig:
    enable: bool = True
    use_page_stats: bool = True
    z_above_min: float = 1.2
    z_below_min: float = 1.0
    both_sides_bonus: int = 2
    one_side_bonus: int = 1
    first_line_on_page_ignore_above: bool = True

@dataclass
class ContextConfig:
    enable: bool = True
    k_lookahead: int = 5
    min_bullets: int = 2
    bullet_block_bonus: int = 2

@dataclass
class RecipeConfig:
    enable: bool = True
    back_look_lines: int = 8
    labels: List[str] = field(default_factory=lambda: ["ingredients:", "instructions:", "method:", "directions:"])
    promote_level: str = "H2"
    min_title_words: int = 1
    max_title_words: int = 6

# ---- NEW ----
@dataclass
class SemanticFilterConfig:
    enable: bool = True
    use_spacy: bool = True
    model: str = "en_core_web_sm"
    max_chars: int = 120
    min_alpha_ratio: float = 0.5
    accept_all_caps_minlen: int = 2
    require_content_pos: bool = True
    content_pos: List[str] = field(default_factory=lambda: ["NOUN", "PROPN", "VERB", "ADJ"])

@dataclass
class Task1AConfig:
    timing: TimingConfig
    tagged: TaggedConfig
    filtering: FilteringConfig
    body_profile: BodyProfileConfig
    scoring: ScoringConfig
    levels: LevelsConfig
    salience: SalienceConfig = field(default_factory=SalienceConfig)
    keywords: KeywordsConfig = field(default_factory=KeywordsConfig)
    page_numbering: PageNumberingConfig = field(default_factory=PageNumberingConfig)
    hierarchy: HierarchyConfig = field(default_factory=HierarchyConfig)
    promotion: PromotionConfig = field(default_factory=PromotionConfig)
    repetition: RepetitionConfig = field(default_factory=RepetitionConfig)
    spatial: SpatialConfig = field(default_factory=SpatialConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    recipe: RecipeConfig = field(default_factory=RecipeConfig)
    semantic_filter: SemanticFilterConfig = field(default_factory=SemanticFilterConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timing": self.timing.__dict__,
            "tagged": self.tagged.__dict__,
            "filtering": self.filtering.__dict__,
            "body_profile": self.body_profile.__dict__,
            "scoring": self.scoring.__dict__,
            "levels": {
                "h1": self.levels.h1.__dict__,
                "h2": self.levels.h2.__dict__,
                "h3": self.levels.h3.__dict__,
            },
            "salience": {
                **self.salience.__dict__,
                "weights": self.salience.weights.__dict__,
            },
            "keywords": self.keywords.__dict__,
            "page_numbering": self.page_numbering.__dict__,
            "hierarchy": self.hierarchy.__dict__,
            "promotion": self.promotion.__dict__,
            "repetition": self.repetition.__dict__,
            "spatial": self.spatial.__dict__,
            "context": self.context.__dict__,
            "recipe": {
                **self.recipe.__dict__,
                "labels": list(self.recipe.labels),
            },
            "semantic_filter": {
                **self.semantic_filter.__dict__,
                "content_pos": list(self.semantic_filter.content_pos),
            },
        }

# -------------------------
# Loader
# -------------------------

def load_config(path: Path | str) -> Task1AConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    timing = TimingConfig(**data.get("timing", {}))
    tagged = TaggedConfig(**data.get("tagged", {}))
    filtering = FilteringConfig(**data.get("filtering", {}))
    body_profile = BodyProfileConfig(**data.get("body_profile", {}))
    scoring = ScoringConfig(**data.get("scoring", {}))

    lv = data.get("levels", {})
    levels = LevelsConfig(
        h1=LevelRule(**lv.get("h1", {"rel_font_min": 1.8, "page_top_pct_max": 0.04})),
        h2=LevelRule(**lv.get("h2", {"rel_font_min": 1.45, "page_top_pct_max": 0.08})),
        h3=LevelRule(**lv.get("h3", {"rel_font_min": 1.15, "page_top_pct_max": 1.00})),
    )

    sal_data = data.get("salience", {})
    weights = SalienceWeights(**sal_data.get("weights", {}))
    salience = SalienceConfig(
        enable=sal_data.get("enable", True),
        font_ratio_std_epsilon=sal_data.get("font_ratio_std_epsilon", 0.15),
        q_h1=sal_data.get("q_h1", 0.85),
        q_h2=sal_data.get("q_h2", 0.50),
        weights=weights,
    )

    kw_data = data.get("keywords", {})
    keywords = KeywordsConfig(
        enabled=kw_data.get("enabled", True),
        boost_score=kw_data.get("boost_score", 2),
        max_extra=kw_data.get("max_extra", 1),
        apply_if_score_at_least=kw_data.get("apply_if_score_at_least", 5),
        max_chars=kw_data.get("max_chars", 80),
        frontmatter_only=kw_data.get("frontmatter_only", True),
        force_h1_if_early=kw_data.get("force_h1_if_early", True),
        force_h1_max_page=kw_data.get("force_h1_max_page", 5),
        list=kw_data.get("list", []),
    )

    pn_data = data.get("page_numbering", {})
    page_numbering = PageNumberingConfig(
        mode=pn_data.get("mode", "index1"),
        offset=pn_data.get("offset", 0),
    )

    hier_data = data.get("hierarchy", {})
    hierarchy = HierarchyConfig(
        appendix_base_level=hier_data.get("appendix_base_level", 2),
        appendix_children_bump=hier_data.get("appendix_children_bump", 1),
    )

    prom_data = data.get("promotion", {})
    promotion = PromotionConfig(
        enable=prom_data.get("enable", True),
        allow_h1=prom_data.get("allow_h1", False),
        h2_q=prom_data.get("h2_q", 0.85),
    )

    rep_data = data.get("repetition", {})
    repetition = RepetitionConfig(
        enable=rep_data.get("enable", True),
        min_occurrences=rep_data.get("min_occurrences", 3),
        max_words=rep_data.get("max_words", 8),
        boost_score=rep_data.get("boost_score", 2),
        min_occurrences_block=rep_data.get("min_occurrences_block", 2),
        block_scope=rep_data.get("block_scope", "page"),
        block_bonus=rep_data.get("block_bonus", 2),
    )

    sp_data = data.get("spatial", {})
    spatial = SpatialConfig(
        enable=sp_data.get("enable", True),
        use_page_stats=sp_data.get("use_page_stats", True),
        z_above_min=sp_data.get("z_above_min", 1.2),
        z_below_min=sp_data.get("z_below_min", 1.0),
        both_sides_bonus=sp_data.get("both_sides_bonus", 2),
        one_side_bonus=sp_data.get("one_side_bonus", 1),
        first_line_on_page_ignore_above=sp_data.get("first_line_on_page_ignore_above", True),
    )

    ctx_data = data.get("context", {})
    context = ContextConfig(
        enable=ctx_data.get("enable", True),
        k_lookahead=ctx_data.get("k_lookahead", 5),
        min_bullets=ctx_data.get("min_bullets", 2),
        bullet_block_bonus=ctx_data.get("bullet_block_bonus", 2),
    )

    rec_data = data.get("recipe", {})
    recipe = RecipeConfig(
        enable=rec_data.get("enable", True),
        back_look_lines=rec_data.get("back_look_lines", 8),
        labels=rec_data.get("labels", ["ingredients:", "instructions:", "method:", "directions:"]),
        promote_level=rec_data.get("promote_level", "H2"),
        min_title_words=rec_data.get("min_title_words", 1),
        max_title_words=rec_data.get("max_title_words", 6),
    )

    sf_data = data.get("semantic_filter", {})
    semantic_filter = SemanticFilterConfig(
        enable=sf_data.get("enable", True),
        use_spacy=sf_data.get("use_spacy", True),
        model=sf_data.get("model", "en_core_web_sm"),
        max_chars=sf_data.get("max_chars", 120),
        min_alpha_ratio=sf_data.get("min_alpha_ratio", 0.5),
        accept_all_caps_minlen=sf_data.get("accept_all_caps_minlen", 2),
        require_content_pos=sf_data.get("require_content_pos", True),
        content_pos=sf_data.get("content_pos", ["NOUN", "PROPN", "VERB", "ADJ"]),
    )

    return Task1AConfig(
        timing=timing,
        tagged=tagged,
        filtering=filtering,
        body_profile=body_profile,
        scoring=scoring,
        levels=levels,
        salience=salience,
        keywords=keywords,
        page_numbering=page_numbering,
        hierarchy=hierarchy,
        promotion=promotion,
        repetition=repetition,
        spatial=spatial,
        context=context,
        recipe=recipe,
        semantic_filter=semantic_filter,
    )
