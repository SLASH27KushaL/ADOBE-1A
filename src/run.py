# src/run.py
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from time import perf_counter

from src.common.config import load_config, Task1AConfig

# You will implement these:
#   - src/common/io.py:list_input_pdfs(input_dir: Path) -> list[Path]
#   - src/common/io.py:write_json(obj: dict, out_path: Path) -> None
#   - src/common/io.py:safe_stem(p: Path) -> str
from src.common import io as io_utils

# You will implement this:
#   - src/task1a/pipeline.py:run_pipeline(pdf_path: Path, cfg: Task1AConfig) -> dict
from src.task1a.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Task 1A: Extract Title + H1/H2/H3 outline from PDFs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing input PDFs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory to write JSON outputs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/task1a.yaml"),
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging level.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    log = logging.getLogger("task1a")

    cfg: Task1AConfig = load_config(args.config)
    log.debug("Loaded config: %s", cfg.to_dict())

    input_dir: Path = args.input
    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = io_utils.list_input_pdfs(input_dir)
    if not pdf_paths:
        log.warning("No PDFs found in input directory: %s", input_dir)

    overall_start = perf_counter()
    processed = 0
    failed = 0

    for pdf_path in pdf_paths:
        start = perf_counter()
        try:
            log.info("Processing: %s", pdf_path.name)
            result = run_pipeline(pdf_path, cfg)  # expected to return dict with {title, outline: [...]}

            out_name = f"{io_utils.safe_stem(pdf_path)}.json"
            out_path = output_dir / out_name
            io_utils.write_json(result, out_path)

            elapsed = perf_counter() - start
            log.info("Done: %s in %.3fs -> %s", pdf_path.name, elapsed, out_path.name)
            processed += 1

            # Soft timing assertion (log-only). Hard-kill would be handled outside by orchestrator if needed.
            if elapsed > cfg.timing.hard_timeout_seconds:
                log.warning(
                    "⚠️ File %s exceeded hard_timeout_seconds (%.2fs > %ds)",
                    pdf_path.name,
                    elapsed,
                    cfg.timing.hard_timeout_seconds,
                )

        except Exception as e:
            failed += 1
            log.exception("Failed processing %s: %s", pdf_path.name, e)

    total_elapsed = perf_counter() - overall_start
    log.info(
        "Finished. processed=%d failed=%d total_time=%.3fs",
        processed,
        failed,
        total_elapsed,
    )

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
