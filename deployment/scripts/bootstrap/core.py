"""Bootstrap environment schema, validation, rendering, and secure writes."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE = ROOT / "deployment" / ".env"
DEFAULT_SEARXNG_SETTINGS = ROOT / "deployment" / "searxng" / "settings.local.yml"
TRACKED_SEARXNG_SETTINGS = ROOT / "deployment" / "searxng" / "settings.yml"
WORKFLOWS = {"core", "self-hosted", "mcp", "live-tests", "exposed-searxng"}
SELF_HOSTED_DEFAULTS = {
    "CRK_MODEL": "ollama:llama3.1",
    "CRK_EMBED_MODEL": "BAAI/bge-small-en-v1.5",
    "CRK_SEARXNG_HOST_PORT": "18080",
}
MCP_DEFAULTS = {
    "CRK_CASES_ROOT": str(ROOT / "data" / "cases"),
    "CRK_SKILL_ROOT": str(ROOT / ".agents" / "skills" / "truecrime-cult-research"),
}
LIVE_TEST_DEFAULTS = {
    "CRK_LIVE_MKULTRA": "1",
    "CRK_LIVE_CODEX": "0",
    "CRK_CODEX_BIN": "codex",
    "CRK_SEARXNG_URL": "http://127.0.0.1:18080",
    "CRK_QDRANT_URL": "http://127.0.0.1:6333",
    "OLLAMA_HOST": "http://127.0.0.1:11434",
    "CRK_MODEL": "ollama:llama3.1",
}
FIELD_LABELS = {
    "CRK_MODEL": "Ollama model spec",
    "CRK_EMBED_MODEL": "Embedding model",
    "CRK_SEARXNG_HOST_PORT": "SearXNG host port",
    "SEARXNG_BASE_URL": "SearXNG base URL",
    "CRK_CASES_ROOT": "MCP cases root",
    "CRK_SKILL_ROOT": "MCP skill root",
    "CRK_LIVE_MKULTRA": "Run MKULTRA live tests",
    "CRK_LIVE_CODEX": "Run Codex live leg",
    "CRK_CODEX_BIN": "Codex executable",
    "CRK_SEARXNG_URL": "Live SearXNG URL",
    "CRK_QDRANT_URL": "Live Qdrant URL",
    "OLLAMA_HOST": "Live Ollama URL",
}


@dataclass(frozen=True)
class ConfigField:
    name: str
    label: str
    default: str
    workflow: str
    sensitive: bool = False


@dataclass(frozen=True)
class WriteResult:
    path: Path
    written: bool
    sensitive: bool = False


def schema_for(workflow: str) -> list[ConfigField]:
    if workflow not in WORKFLOWS:
        raise ValueError(f"Unknown workflow: {workflow}")
    if workflow == "core":
        return []
    defaults = dict(SELF_HOSTED_DEFAULTS) if workflow in {"self-hosted", "exposed-searxng"} else {}
    if workflow == "mcp":
        defaults = dict(MCP_DEFAULTS)
    elif workflow == "live-tests":
        defaults = dict(LIVE_TEST_DEFAULTS)
    values = derive_values(defaults)
    return [ConfigField(name, FIELD_LABELS.get(name, name), value, workflow) for name, value in values.items()]


def derive_values(values: dict[str, str]) -> dict[str, str]:
    derived = dict(values)
    port = derived.get("CRK_SEARXNG_HOST_PORT")
    base = derived.get("SEARXNG_BASE_URL")
    if port and (not base or re.fullmatch(r"http://127\.0\.0\.1:\d+/?", base)):
        derived["SEARXNG_BASE_URL"] = f"http://127.0.0.1:{port}/"
    if "SEARXNG_BASE_URL" in derived and derived["SEARXNG_BASE_URL"] and not derived["SEARXNG_BASE_URL"].endswith("/"):
        derived["SEARXNG_BASE_URL"] += "/"
    return derived


def validate_values(values: dict[str, str], workflow: str) -> list[str]:
    errors: list[str] = []
    for key, value in values.items():
        if value == "":
            errors.append(f"{key} must not be empty")
    model = values.get("CRK_MODEL")
    if model and (":" not in model or not model.startswith("ollama:") or model.split(":", 1)[1] == ""):
        errors.append("CRK_MODEL must be an ollama model spec like ollama:llama3.1")
    port = values.get("CRK_SEARXNG_HOST_PORT")
    if port:
        try:
            number = int(port)
        except ValueError:
            errors.append("CRK_SEARXNG_HOST_PORT must be an integer")
        else:
            if number < 1 or number > 65535:
                errors.append("CRK_SEARXNG_HOST_PORT must be between 1 and 65535")
    for key in ("SEARXNG_BASE_URL", "CRK_SEARXNG_URL", "CRK_QDRANT_URL", "OLLAMA_HOST"):
        if key in values:
            parsed = urlparse(values[key])
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{key} must be an absolute http(s) URL")
    if workflow == "core" and values:
        errors.append("core workflow does not write environment values")
    return errors


def render_dotenv(values: dict[str, str]) -> str:
    lines = []
    for key in sorted(values):
        value = values[key]
        if "\n" in value or "\r" in value:
            raise ValueError(f"{key} contains an unsupported newline")
        if re.fullmatch(r"[A-Za-z0-9_./:@%+=,-]+", value):
            rendered = value
        else:
            rendered = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        lines.append(f"{key}={rendered}")
    return "\n".join(lines) + "\n"


def ensure_writable(path: Path, force: bool) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing to write through symlink: {path}")
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to replace it")


def write_secure(path: Path, content: str, *, force: bool = False, sensitive: bool = False) -> WriteResult:
    target = path.expanduser()
    ensure_writable(target, force)
    target = target.resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temp_path, target)
        os.chmod(target, 0o600)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return WriteResult(path=target, written=True, sensitive=sensitive)


def searxng_local_settings(secret: str) -> str:
    text = TRACKED_SEARXNG_SETTINGS.read_text(encoding="utf-8")
    updated, count = re.subn(r'^(\s*secret_key:\s*).+$', rf'\1"{secret}"', text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Could not replace SearXNG server.secret_key")
    return updated
