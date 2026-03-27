#!/bin/zsh
set -euo pipefail

ROOT_DIR="/Users/fan/code/design-skill-miner"
HOST="127.0.0.1"
PORT="8765"
URL="http://${HOST}:${PORT}"

if lsof -tiTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Design Skill Miner 已在运行。"
  open "${URL}"
  exit 0
fi

cd "${ROOT_DIR}"

echo "正在启动 Design Skill Miner..."
echo "项目目录: ${ROOT_DIR}"
echo "访问地址: ${URL}"
echo ""

(sleep 2; open "${URL}") &

exec zsh ./run-local.sh serve --host "${HOST}" --port "${PORT}"
