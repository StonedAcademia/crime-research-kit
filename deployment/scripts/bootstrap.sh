#!/usr/bin/env bash
# Bootstrap the minimum CRK toolchain: proto plus pinned moon/python/uv.
# Run once before the README quick start.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

TOOLCHAIN_ONLY=false
CONFIGURE=false
NON_INTERACTIVE=false
FORCE=false
DRY_RUN=false
WORKFLOW="self-hosted"
ENV_FILE=""
SEARXNG_SETTINGS_FILE=""
SET_ARGS=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --toolchain-only) TOOLCHAIN_ONLY=true ;;
    --configure) CONFIGURE=true ;;
    --non-interactive) NON_INTERACTIVE=true ;;
    --force) FORCE=true ;;
    --dry-run) DRY_RUN=true ;;
    --workflow)
      shift
      WORKFLOW="${1:?--workflow requires a value}"
      ;;
    --env-file)
      shift
      ENV_FILE="${1:?--env-file requires a value}"
      ;;
    --searxng-settings-file)
      shift
      SEARXNG_SETTINGS_FILE="${1:?--searxng-settings-file requires a value}"
      ;;
    --set)
      shift
      SET_ARGS+=("--set" "${1:?--set requires KEY=VALUE}")
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
  shift
done

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

run_configure() {
  args=("deployment/scripts/bootstrap_env.py" "configure" "--workflow" "$WORKFLOW")
  if [ "$NON_INTERACTIVE" = true ]; then args+=("--non-interactive"); fi
  if [ "$FORCE" = true ]; then args+=("--force"); fi
  if [ "$DRY_RUN" = true ]; then args+=("--dry-run"); fi
  if [ -n "$ENV_FILE" ]; then args+=("--env-file" "$ENV_FILE"); fi
  if [ -n "$SEARXNG_SETTINGS_FILE" ]; then args+=("--searxng-settings-file" "$SEARXNG_SETTINGS_FILE"); fi
  args+=("${SET_ARGS[@]}")
  python "${args[@]}"
}

if [ "$TOOLCHAIN_ONLY" = true ]; then
  exit 0
fi

if [ "$CONFIGURE" = true ]; then
  run_configure
elif [ -t 0 ] && [ -t 1 ]; then
  read -r -p "Configure local CRK environment now? [Y/n] " answer
  case "${answer:-Y}" in
    y|Y|yes|YES) run_configure ;;
  esac
else
  echo "To configure local deployment env later:"
  echo "  ./deployment/scripts/bootstrap.sh --configure"
fi
