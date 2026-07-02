"""Governance: frontend->ops import boundary, lazy optional imports, network ban (spec §5)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

from tests.helpers import KIT_ROOT


# Policy source: docs/superpowers/specs/2026-07-02-governance-hardening-spec.md §5.
SRC = KIT_ROOT / "src"
FRONTEND_ROOTS = [
    SRC / "cli.py",
    SRC / "adapters" / "interfaces" / "mcp",
    SRC / "pipeline" / "graph",
    SRC / "pipeline" / "app",
]
FORBIDDEN_FOR_FRONTENDS = {"core.casefile"}
OPTIONAL_PACKAGES = {
    "langgraph",
    "langchain",
    "langchain_ollama",
    "llama_index",
    "qdrant_client",
    "mem0",
    "docling",
    "ocrmypdf",
    "fitz",
    "playwright",
    "scrapy",
    "trafilatura",
    "mcp",
    "sentence_transformers",
    "diskcache",
}
NETWORK_MODULES = {"socket", "requests", "httpx", "aiohttp"}
NETWORK_ATTR_MODULES = {"urllib": {"request"}, "http": {"client"}}
NETWORK_ALLOWED = {SRC / "adapters" / "io" / "acquisition"}


def iter_py(root: Path):
    yield from ([root] if root.is_file() else sorted(root.rglob("*.py")))


def imports_of(path: Path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno, node
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if node.level:
                pkg = path.relative_to(SRC).parts[:-node.level]
                mod = ".".join((*pkg, node.module))
            yield mod, node.lineno, node


def test_frontends_never_touch_ledger_internals():
    offenders = []
    for root in FRONTEND_ROOTS:
        for path in iter_py(root):
            for mod, lineno, _node in imports_of(path):
                if any(mod == forbidden or mod.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_FOR_FRONTENDS):
                    offenders.append(f"{path.relative_to(KIT_ROOT)}:{lineno} imports {mod}")
    assert not offenders, offenders


def test_tcr_script_only_referenced_via_ops_runner():
    offenders = [
        str(path.relative_to(KIT_ROOT))
        for root in FRONTEND_ROOTS
        for path in iter_py(root)
        if "tcr.py" in path.read_text()
    ]
    assert not offenders, f"frontends reference tcr.py directly: {offenders}"


def test_optional_packages_import_lazily():
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text())
        body_ids = {id(node) for node in tree.body}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and id(node) in body_ids:
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and id(node) in body_ids:
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name.split(".")[0] in OPTIONAL_PACKAGES:
                    offenders.append(f"{path.relative_to(KIT_ROOT)}:{node.lineno} top-level {name}")
    assert not offenders, offenders


def test_base_cli_import_pulls_no_optional_packages():
    code = (
        "import sys, cli; "
        f"hits = sorted({{m.split('.')[0] for m in sys.modules}} & {OPTIONAL_PACKAGES!r}); "
        "print(','.join(hits)); sys.exit(1 if hits else 0)"
    )
    env = {"PYTHONPATH": str(KIT_ROOT / "src"), "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=KIT_ROOT, env=env)
    assert proc.returncode == 0, f"eager optional imports: {proc.stdout} {proc.stderr}"


def test_network_modules_confined_to_acquisition():
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if any(path.is_relative_to(allowed) for allowed in NETWORK_ALLOWED):
            continue
        for mod, lineno, _node in imports_of(path):
            head, *rest = mod.split(".")
            if head in NETWORK_MODULES or (
                head in NETWORK_ATTR_MODULES and rest and rest[0] in NETWORK_ATTR_MODULES[head]
            ):
                offenders.append(f"{path.relative_to(KIT_ROOT)}:{lineno} imports {mod}")
    assert not offenders, offenders
