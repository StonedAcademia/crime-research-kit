#!/usr/bin/env sh
set -eu

MODEL_SPEC="${CRK_MODEL:-ollama:llama3.1}"
PROVIDER="${MODEL_SPEC%%:*}"
MODEL="${MODEL_SPEC#*:}"

if [ "$PROVIDER" != "ollama" ] || [ "$MODEL" = "$MODEL_SPEC" ] || [ -z "$MODEL" ]; then
  echo "CRK_MODEL must be an ollama model spec like ollama:llama3.1" >&2
  exit 1
fi

OLLAMA_URL="${OLLAMA_HOST:-http://ollama:11434}"

echo "Waiting for Ollama at $OLLAMA_URL..."
for _ in $(seq 1 120); do
  if curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -fsS "$OLLAMA_URL/api/tags" >/dev/null
echo "Pulling Ollama model: $MODEL"
curl -fsS "$OLLAMA_URL/api/pull" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$MODEL\"}"
echo
curl -fsS "$OLLAMA_URL/api/tags"
echo

