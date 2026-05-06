#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${OURO_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: ./scripts/play-real.sh [extra ouro play args]

Starts a real-provider Ouro Agent battle through the DashScope Anthropic bridge.

Environment overrides:
  OURO_API_KEY       DashScope API key. If missing, the script prompts for it.
  OURO_SEED          Battle seed. Default: 2.
  OURO_DELAY         Delay between frames. Default: 0.2.
  OURO_PROMPT_STYLE  Strategy template. Default: control.

Examples:
  ./scripts/play-real.sh
  OURO_SEED=3 ./scripts/play-real.sh --hero hero_broken_string_hunter
  OURO_DELAY=0 ./scripts/play-real.sh --no-animation
EOF
  exit 0
fi

if [[ -z "${OURO_API_KEY:-}" ]]; then
  if [[ ! -t 0 ]]; then
    printf "OURO_API_KEY is not set, and stdin is not interactive.\n" >&2
    printf "Run: export OURO_API_KEY='your key'\n" >&2
    exit 2
  fi
  printf "DashScope API key (input is hidden): "
  stty -echo
  read -r OURO_API_KEY
  stty echo
  printf "\n"
  export OURO_API_KEY
fi

"$PYTHON_BIN" -m ouro_agent.cli.main config set provider anthropic >/dev/null
"$PYTHON_BIN" -m ouro_agent.cli.main config set api_key_env OURO_API_KEY >/dev/null
"$PYTHON_BIN" -m ouro_agent.cli.main config set base_url https://coding.dashscope.aliyuncs.com/apps/anthropic >/dev/null
"$PYTHON_BIN" -m ouro_agent.cli.main config set model qwen3.6-plus >/dev/null
"$PYTHON_BIN" -m ouro_agent.cli.main config set timeout_seconds 90 >/dev/null

printf "Starting Ouro Agent with qwen3.6-plus. First model turn can take 30-60s...\n"
exec "$PYTHON_BIN" -m ouro_agent.cli.main play --seed "${OURO_SEED:-2}" --delay "${OURO_DELAY:-0.2}" --prompt-style "${OURO_PROMPT_STYLE:-control}" "$@"
