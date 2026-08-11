#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SJSEED_PROJECT_DIR:-}" ]]; then
  echo "SJSEED_PROJECT_DIR is required." >&2
  exit 1
fi

exec docker compose \
  --project-directory "${SJSEED_PROJECT_DIR}" \
  logs \
  --follow \
  --no-color \
  --since 0s \
  ai worker
