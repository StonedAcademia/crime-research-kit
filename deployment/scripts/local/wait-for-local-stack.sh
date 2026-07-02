#!/usr/bin/env sh
set -eu

wait_for_url() {
  name="$1"
  url="$2"
  attempts="${3:-120}"
  echo "Waiting for $name at $url..."
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is ready"
      return 0
    fi
    sleep 1
  done
  echo "$name did not become ready at $url" >&2
  return 1
}

QDRANT_URL="${CRK_QDRANT_URL:-http://qdrant:6333}"
SEARXNG_URL="${CRK_SEARXNG_URL:-http://searxng:8080}"
OLLAMA_URL="${OLLAMA_HOST:-http://ollama:11434}"

wait_for_url "Qdrant" "$QDRANT_URL/readyz"
wait_for_url "SearXNG" "$SEARXNG_URL/search?q=crk&format=json"
wait_for_url "Ollama" "$OLLAMA_URL/api/tags"

