#!/usr/bin/env bash
# Bootstrap the minimum TRCR toolchain: proto, plus the moon and python
# versions pinned in .prototools. Run once before the README quick start.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if ! command -v proto >/dev/null 2>&1; then
  echo "Installing proto (https://moonrepo.dev/proto)..."
  curl -fsSL https://moonrepo.dev/install/proto.sh | bash -s -- --yes
  export PATH="$HOME/.proto/bin:$HOME/.proto/shims:$PATH"
fi

echo "Installing tools pinned in .prototools (moon, python)..."
proto use

echo
echo "Toolchain ready. Continue with the README quick start:"
echo "  moon run trcr:install-dev"
