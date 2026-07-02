#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
"$SCRIPT_DIR/../../local/wait-for-local-stack.sh"

python -m cli --help >/dev/null
cr-kit plan /tmp/crk_install_smoke \
  --title "CRK Container Smoke" \
  --subject "self-hosted deployment smoke test" >/tmp/crk-plan.json

python -c "from adapters.interfaces.mcp.server import create_server; create_server()"

tesseract --version >/dev/null
gs --version >/dev/null
ocrmypdf --version >/dev/null

python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/examples/synthetic_case

curl -fsS "${CRK_QDRANT_URL:-http://qdrant:6333}/readyz" >/dev/null
curl -fsS "${CRK_SEARXNG_URL:-http://searxng:8080}/search?q=crk&format=json" >/dev/null
curl -fsS "${OLLAMA_HOST:-http://ollama:11434}/api/tags" >/dev/null

MODEL_SPEC="${CRK_MODEL:-ollama:llama3.1}"
MODEL="${MODEL_SPEC#*:}"
curl -fsS "${OLLAMA_HOST:-http://ollama:11434}/api/tags" | python -c '
import json
import os
import sys

model = os.environ.get("CRK_MODEL", "ollama:llama3.1").split(":", 1)[1]
payload = json.load(sys.stdin)
names = {item.get("name", "").split(":", 1)[0] for item in payload.get("models", [])}
names.update(item.get("name", "") for item in payload.get("models", []))
if model not in names:
    raise SystemExit(f"Ollama model not found: {model}")
'

echo "CRK local deployment smoke test passed."
