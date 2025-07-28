#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="${INPUT_DIR:-/app/input}"
OUTPUT_DIR="${OUTPUT_DIR:-/app/output}"
CONFIG_PATH="${CONFIG_PATH:-configs/task1a.yaml}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

python -m src.run \
  --input "$INPUT_DIR" \
  --output "$OUTPUT_DIR" \
  --config "$CONFIG_PATH" \
  --log-level "$LOG_LEVEL" \
  "$@"
  