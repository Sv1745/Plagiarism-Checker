#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-data/jobs}"
if [ -d "$TARGET_DIR" ]; then
  find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
fi

echo "Cleaned temporary job folders in $TARGET_DIR"
