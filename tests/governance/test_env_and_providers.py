"""Governance: env registry and local-only provider policy (spec §5)."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

from tests.helpers import KIT_ROOT


# Policy source: docs/superpowers/specs/2026-07-02-governance-hardening-spec.md §5.
REGISTRY = KIT_ROOT / "docs" / "registry" / "env_vars.json"
APPROVED_PREFIXES = ("TRCR_", "OLLAMA_", "SEARXNG_")
APPROVED_SINGLETONS = {"HF_HOME", "TRANSFORMERS_CACHE", "SOURCE_DATE_EPOCH"}
RUNTIME_SCOPES = {"runtime"}
IGNORED_DEPLOYMENT_ENV = {"PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED", "PIP_NO_CACHE_DIR", "FORCE_OWNERSHIP"}
SAAS_DENYLIST = {
    "langsmith",
    "LANGCHAIN_TRACING",
    "LANGCHAIN_API_KEY",
    "smith.langchain.com",
    "pinecone",
    "weaviate.io",
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis",
    "wandb",
    "sentry.io",
}
SAAS_SCAN_ROOTS = ("src/", "deployment/", ".agents/skills/")
SAAS_EXEMPT_PATHS = {"tests/governance/test_env_and_providers.py"}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=KIT_ROOT, check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]


def registry_entries() -> dict[str, dict[str, str]]:
    data = json.loads(REGISTRY.read_text())
    return {entry["name"]: entry for entry in data["env_vars"]}


def literal_arg(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def py_env_reads(path: Path) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    dynamic: list[str] = []
    tree = ast.parse(path.read_text())
    rel_path = path.relative_to(KIT_ROOT).as_posix()
    for node in ast.walk(tree):
        key: str | None = None
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if isinstance(node.value.value, ast.Name) and node.value.value.id == "os" and node.value.attr == "environ":
                key = literal_arg(node.slice)
                if key is None:
                    dynamic.append(f"{path.relative_to(KIT_ROOT)}:{node.lineno}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in {"get", "setdefault"}:
                owner = func.value
                if isinstance(owner, ast.Attribute) and isinstance(owner.value, ast.Name):
                    if owner.value.id == "os" and owner.attr == "environ" and node.args:
                        key = literal_arg(node.args[0])
                        is_config_helper = rel_path == "src/case_builder/config.py" and isinstance(node.args[0], ast.Name)
                        if key is None and not is_config_helper:
                            dynamic.append(f"{rel_path}:{node.lineno}")
            elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id == "os" and func.attr == "getenv" and node.args:
                    key = literal_arg(node.args[0])
                    if key is None:
                        dynamic.append(f"{rel_path}:{node.lineno}")
            elif isinstance(func, ast.Name) and func.id in {"env_str", "env_int"} and node.args:
                key = literal_arg(node.args[0])
        if key:
            keys.add(key)
    return keys, dynamic


def deployment_env_keys(path: Path) -> set[str]:
    text = path.read_text(errors="replace")
    keys = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", text))
    keys.update(match.group(1) for match in re.finditer(r"^\s+([A-Z][A-Z0-9_]+):", text, re.MULTILINE))
    if path.name.startswith(".env"):
        keys.update(match.group(1) for match in re.finditer(r"^([A-Z][A-Z0-9_]*)=", text, re.MULTILINE))
    return {
        key
        for key in keys
        if key not in IGNORED_DEPLOYMENT_ENV and (key.startswith(APPROVED_PREFIXES) or key in APPROVED_SINGLETONS)
    }


def discovered_env_keys() -> tuple[set[str], list[str], set[str]]:
    keys: set[str] = set()
    dynamic: list[str] = []
    runtime_keys: set[str] = set()
    py_paths = [Path(p) for p in tracked_files() if p.startswith("src/") and p.endswith(".py")]
    py_paths += [Path(p) for p in tracked_files() if p.startswith(".agents/skills/") and p.endswith(".py")]
    py_paths += [Path(p) for p in tracked_files() if p.startswith("deployment/scripts/") and p.endswith(".py")]
    for rel in py_paths:
        found, dyn = py_env_reads(KIT_ROOT / rel)
        keys.update(found)
        dynamic.extend(dyn)
        if str(rel).startswith("src/"):
            runtime_keys.update(found)
    for rel in tracked_files():
        path = Path(rel)
        if rel.startswith("deployment/") and path.suffix in {"", ".sh", ".yml", ".yaml", ".env", ".example"}:
            keys.update(deployment_env_keys(KIT_ROOT / path))
    return keys, dynamic, runtime_keys


def test_env_registry_covers_literal_env_usage():
    keys, dynamic, _runtime_keys = discovered_env_keys()
    registered = set(registry_entries())
    assert not dynamic, f"dynamic env keys are not allowed: {dynamic}"
    assert keys <= registered, f"undocumented env vars: {sorted(keys - registered)}"


def test_registered_env_vars_use_approved_prefixes():
    offenders = []
    for name, entry in registry_entries().items():
        if not name.startswith(APPROVED_PREFIXES) and name not in APPROVED_SINGLETONS:
            offenders.append(name)
        assert entry["prefix_class"]
        assert entry["scope"] in {"runtime", "deployment", "ci"}
        assert entry["purpose"]
    assert not offenders, f"env vars outside approved prefixes/singletons: {offenders}"


def test_runtime_registry_entries_are_read_by_runtime_code():
    _keys, _dynamic, runtime_keys = discovered_env_keys()
    dead = sorted(name for name, entry in registry_entries().items() if entry["scope"] in RUNTIME_SCOPES and name not in runtime_keys)
    assert not dead, f"runtime env vars registered but not read by runtime code: {dead}"


def test_local_only_provider_policy():
    offenders = []
    for rel in tracked_files():
        if rel in SAAS_EXEMPT_PATHS:
            continue
        if not (rel.startswith(SAAS_SCAN_ROOTS) or rel == "pyproject.toml"):
            continue
        text = (KIT_ROOT / rel).read_text(errors="replace")
        lowered = text.lower()
        for term in SAAS_DENYLIST:
            if term.lower() in lowered:
                offenders.append(f"{rel}: {term}")
    assert not offenders, f"banned SaaS/provider references: {offenders}"
