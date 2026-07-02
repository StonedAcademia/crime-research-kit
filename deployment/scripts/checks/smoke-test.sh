#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
"$SCRIPT_DIR/wait-for-local-stack.sh"

python -m case_builder.cli --help >/dev/null
trcr-case-builder plan /tmp/trcr_install_smoke \
  --title "TRCR Container Smoke" \
  --subject "self-hosted deployment smoke test" >/tmp/trcr-plan.json

python -c "from case_builder.mcp.server import create_server; create_server()"

tesseract --version >/dev/null
gs --version >/dev/null
ocrmypdf --version >/dev/null

python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/examples/synthetic_case

curl -fsS "${TRCR_QDRANT_URL:-http://qdrant:6333}/readyz" >/dev/null
curl -fsS "${TRCR_SEARXNG_URL:-http://searxng:8080}/search?q=trcr&format=json" >/dev/null
curl -fsS "${OLLAMA_HOST:-http://ollama:11434}/api/tags" >/dev/null

MODEL_SPEC="${TRCR_MODEL:-ollama:llama3.1}"
MODEL="${MODEL_SPEC#*:}"
curl -fsS "${OLLAMA_HOST:-http://ollama:11434}/api/tags" | python -c '
import json
import os
import sys

model = os.environ.get("TRCR_MODEL", "ollama:llama3.1").split(":", 1)[1]
payload = json.load(sys.stdin)
names = {item.get("name", "").split(":", 1)[0] for item in payload.get("models", [])}
names.update(item.get("name", "") for item in payload.get("models", []))
if model not in names:
    raise SystemExit(f"Ollama model not found: {model}")
'

echo "TRCR local deployment smoke test passed."
