from __future__ import annotations

import re
from typing import List, Dict

APP_RE = re.compile(r'^\s*appendix\s+[A-Z]\b', re.IGNORECASE)
NUM_RE = re.compile(r'^\s*(\d+(?:\.\d+)*)')

def renormalize_by_number_tree(
    items: List[Dict],
    appendix_base_level: int = 2,
    appendix_children_bump: int = 1,
) -> List[Dict]:
    out: List[Dict] = []
    stack: List[tuple[tuple[int, ...], int]] = []
    base_after_appendix: int | None = None

    def clamp(x: int) -> int:
        return max(1, min(3, x))

    for it in items:
        text = (it.get("text") or "").strip()

        if APP_RE.match(text):
            base_after_appendix = appendix_base_level
            stack.clear()
            it["level"] = f"H{clamp(appendix_base_level)}"
            out.append(it)
            continue

        m = NUM_RE.match(text)
        if m:
            num_tuple = tuple(int(x) for x in m.group(1).split("."))

            if base_after_appendix is not None:
                level_int = clamp(base_after_appendix + appendix_children_bump)
                it["level"] = f"H{level_int}"
                stack.append((num_tuple, level_int))
                out.append(it)
                continue

            while stack and not _is_prefix(stack[-1][0], num_tuple):
                stack.pop()

            if not stack:
                level_int = 1
            else:
                parent_tuple, parent_level = stack[-1]
                rel_depth = max(1, len(num_tuple) - len(parent_tuple))
                level_int = clamp(parent_level + rel_depth)

            it["level"] = f"H{level_int}"
            stack.append((num_tuple, level_int))
            out.append(it)
            continue

        out.append(it)

    return out

def _is_prefix(prefix: tuple[int, ...], full: tuple[int, ...]) -> bool:
    return len(prefix) <= len(full) and full[:len(prefix)] == prefix
