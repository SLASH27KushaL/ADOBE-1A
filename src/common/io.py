# src/common/io.py
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List

log = logging.getLogger(__name__)

_PDF_SUFFIXES = {".pdf"}


def list_input_pdfs(input_dir: Path, recursive: bool = False) -> List[Path]:
    """
    Return a sorted list of PDF file paths inside input_dir.

    Parameters
    ----------
    input_dir : Path
        Directory that contains PDFs.
    recursive : bool
        If True, search recursively with rglob. Defaults to False.

    Returns
    -------
    List[Path]
        Sorted list of PDF paths.
    """
    if not input_dir.exists():
        log.warning("Input directory does not exist: %s", input_dir)
        return []

    if recursive:
        it = input_dir.rglob("*.pdf")
    else:
        it = input_dir.glob("*.pdf")

    pdfs = [p for p in it if p.is_file() and p.suffix.lower() in _PDF_SUFFIXES]
    pdfs.sort(key=lambda p: p.name.lower())
    return pdfs


_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_stem(p: Path) -> str:
    """
    Create a filesystem-safe stem for output JSON filenames.

    Keeps letters, numbers, dot, underscore, dash.
    Collapses other runs into a single underscore.
    """
    stem = p.stem
    stem = _SANITIZE_RE.sub("_", stem).strip("._-")
    return stem or "output"


def write_json(obj: dict, out_path: Path, indent: int = 2) -> None:
    """
    Write a JSON file to out_path, creating parent dirs if needed.
    Uses UTF-8 and keeps unicode characters (ensure_ascii=False).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
