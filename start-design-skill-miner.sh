#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOST="127.0.0.1"
PORT="8765"
URL="http://${HOST}:${PORT}"

if command -v lsof >/dev/null 2>&1 && lsof -tiTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${URL}" >/dev/null 2>&1 || true
  fi
  exit 0
fi

cd "${ROOT_DIR}"

if command -v xdg-open >/dev/null 2>&1; then
  (sleep 2; xdg-open "${URL}" >/dev/null 2>&1 || true) &
fi

PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" python3 -m design_skill_miner serve --host "${HOST}" --port "${PORT}"
