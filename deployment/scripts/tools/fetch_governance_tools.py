#!/usr/bin/env python3
"""Fetch pinned governance tools and run audit-lane helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "deployment" / "tooling" / "manifest.json"
BIN_DIR = ROOT / "deployment" / "tooling" / "bin"
OFFLINE = ("connection", "network", "timed out", "temporary failure", "name or service", "no route", "ssl")


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def platform_key() -> str:
    machine = platform.machine().lower()
    if sys.platform.startswith("linux") and machine in {"x86_64", "amd64"}:
        return "linux_x64"
    if sys.platform.startswith("linux") and machine in {"aarch64", "arm64"}:
        return "linux_arm64"
    raise SystemExit(f"Unsupported governance tool platform: {sys.platform}/{machine}")


def tool_path(name: str, manifest: dict | None = None) -> Path:
    data = manifest or load_manifest()
    suffix = ".exe" if sys.platform == "win32" else ""
    return BIN_DIR / f"{data['tools'][name]['binary']}{suffix}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=60) as response, dest.open("wb") as out:
            shutil.copyfileobj(response, out)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not download {url}: {exc}") from exc


def extract_binary(archive: Path, binary: str, dest: Path) -> None:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            member = next(name for name in bundle.namelist() if Path(name).name in {binary, f"{binary}.exe"})
            with bundle.open(member) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
    elif archive.suffix == ".exe":
        shutil.copy2(archive, dest)
    else:
        with tarfile.open(archive) as bundle:
            member = next(item for item in bundle.getmembers() if Path(item.name).name == binary)
            src = bundle.extractfile(member)
            if src is None:
                raise SystemExit(f"{binary} not found in {archive}")
            with src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
    dest.chmod(dest.stat().st_mode | 0o755)


def fetch_tool(name: str, manifest: dict, offline: bool) -> Path:
    key = platform_key()
    tool = manifest["tools"][name]
    dest = tool_path(name, manifest)
    if dest.exists():
        return dest
    if offline:
        raise SystemExit(f"SKIP (offline): {name} is not cached at {dest}")
    asset = tool["assets"][key]
    url = tool["url_template"].format(version=tool["version"], asset=asset)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / asset
        print(f"Fetching {name} {tool['version']} for {key}")
        download(url, archive)
        actual = sha256(archive)
        expected = tool["sha256"][key]
        if actual != expected:
            raise SystemExit(f"{name} checksum mismatch: got {actual}, expected {expected}")
        extract_binary(archive, tool["binary"], dest)
    return dest


def fetch_all(names: list[str], offline: bool) -> int:
    manifest = load_manifest()
    for name in names or sorted(manifest["tools"]):
        path = fetch_tool(name, manifest, offline)
        print(f"{name}: {path}")
    return 0


def venv_bin(name: str) -> Path:
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    suffix = ".exe" if sys.platform == "win32" else ""
    return ROOT / ".venv" / scripts / f"{name}{suffix}"


def venv_python() -> Path:
    return venv_bin("python")


def python_tool(name: str) -> Path | str:
    found = shutil.which(name)
    if found:
        return found
    return venv_bin(name)


def run_checked(command: list[str], skip_missing: bool = True) -> int:
    if skip_missing and not Path(command[0]).exists():
        print(f"SKIP (missing tool): {command[0]}")
        return 0
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    output = f"{proc.stdout}\n{proc.stderr}".lower()
    if proc.returncode and any(marker in output for marker in OFFLINE):
        print("SKIP (offline): advisory or link network unavailable")
        return 0
    return proc.returncode


def run_binary(name: str, args: list[str], offline: bool) -> int:
    manifest = load_manifest()
    path = fetch_tool(name, manifest, offline)
    return subprocess.run([str(path), *args], cwd=ROOT).returncode


def audit_deps() -> int:
    return run_checked([sys.executable, "-m", "pip_audit", "--progress-spinner", "off"])


def audit_licenses() -> int:
    return run_checked([str(python_tool("pip-licenses")), "--format=json", "--with-system"])


def sbom() -> int:
    (ROOT / "dist").mkdir(exist_ok=True)
    return run_checked([str(python_tool("cyclonedx-py")), "environment", "--output-file", "dist/sbom.json"])


def build_dist() -> int:
    env = {**os.environ, "SOURCE_DATE_EPOCH": os.environ.get("SOURCE_DATE_EPOCH", "1735689600")}
    return subprocess.run([sys.executable, "-m", "build"], cwd=ROOT, env=env).returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    sub = parser.add_subparsers(dest="command")
    fetch = sub.add_parser("fetch")
    fetch.add_argument("tools", nargs="*")
    run = sub.add_parser("run")
    run.add_argument("tool")
    run.add_argument("args", nargs=argparse.REMAINDER)
    sub.add_parser("audit-deps")
    sub.add_parser("audit-licenses")
    sub.add_parser("sbom")
    sub.add_parser("build-dist")
    args = parser.parse_args(argv)
    if args.command in {None, "fetch"}:
        return fetch_all(getattr(args, "tools", []), args.offline)
    if args.command == "run":
        return run_binary(args.tool, args.args, args.offline)
    return globals()[args.command.replace("-", "_")]()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
