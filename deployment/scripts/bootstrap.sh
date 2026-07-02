#!/usr/bin/env bash
# Bootstrap the minimum CRK toolchain: proto plus pinned moon/python/uv.
# Run once before the README quick start.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if ! command -v proto >/dev/null 2>&1; then
  echo "Installing proto (https://moonrepo.dev/proto)..."
  curl -fsSL https://moonrepo.dev/install/proto.sh | bash -s -- --yes
  export PATH="$HOME/.proto/bin:$HOME/.proto/shims:$PATH"
fi

echo "Installing tools pinned in .prototools (moon, python, uv)..."
proto use

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv (https://docs.astral.sh/uv/)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo
echo "Toolchain ready. Continue with the README quick start:"
echo "  moon run crk:check"
