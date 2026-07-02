#!/usr/bin/env python3
"""Validate release tag, changelog, reproducible artifacts, and SBOM output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_EPOCH = "1735689600"


class ReleaseError(RuntimeError):
    """Release readiness failure with a user-facing message."""


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def venv_bin(root: Path, name: str) -> Path:
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    suffix = ".exe" if sys.platform == "win32" else ""
    return root / ".venv" / scripts / f"{name}{suffix}"


def project_metadata(root: Path) -> dict:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def current_tag(root: Path) -> str:
    value = os.environ.get("CRK_RELEASE_TAG")
    if value:
        return value
    proc = subprocess.run(["git", "describe", "--tags", "--exact-match", "HEAD"], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ReleaseError("HEAD is not exactly tagged; set CRK_RELEASE_TAG or create a local v<version> tag.")
    return proc.stdout.strip()


def check_tag_matches_version(tag: str, version: str) -> None:
    expected = f"v{version}"
    if tag != expected:
        raise ReleaseError(f"Release tag {tag!r} does not match pyproject version {version!r}; expected {expected!r}.")


def changelog_sections(text: str) -> dict[str, str | None]:
    sections: dict[str, str | None] = {}
    pattern = re.compile(r"^## \[([^\]]+)\](?: - (\d{4}-\d{2}-\d{2}))?\s*$", re.MULTILINE)
    for match in pattern.finditer(text):
        sections[match.group(1)] = match.group(2)
    return sections


def check_changelog(text: str, version: str) -> None:
    sections = changelog_sections(text)
    if "Unreleased" not in sections:
        raise ReleaseError("CHANGELOG.md must contain a ## [Unreleased] section.")
    date = sections.get(version)
    if date is None:
        raise ReleaseError(f"CHANGELOG.md must contain a dated ## [{version}] - YYYY-MM-DD section.")


def archive_checkout(root: Path, dest: Path) -> Path:
    dest.mkdir(parents=True)
    archive = dest / "head.tar"
    source = dest / "source"
    source.mkdir()
    run(["git", "archive", "--format=tar", "-o", str(archive), "HEAD"], cwd=root)
    with tarfile.open(archive) as bundle:
        bundle.extractall(source)
    return source


def build_once(root: Path, dest: Path) -> Path:
    source = archive_checkout(root, dest)
    out_dir = dest / "dist"
    out_dir.mkdir()
    env = {**os.environ, "SOURCE_DATE_EPOCH": os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_EPOCH)}
    run([str(venv_bin(root, "python")), "-m", "build", "--outdir", str(out_dir)], cwd=source, env=env)
    return out_dir


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wheel_signature(path: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(path) as bundle:
        return [(name, digest(bundle.read(name))) for name in sorted(bundle.namelist()) if not name.endswith("/")]


def sdist_signature(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with tarfile.open(path) as bundle:
        for member in sorted(bundle.getmembers(), key=lambda item: item.name):
            if not member.isfile():
                continue
            extracted = bundle.extractfile(member)
            if extracted is None:
                continue
            rows.append((member.name, digest(extracted.read())))
    return rows


def artifact_signature(path: Path) -> list[tuple[str, str]]:
    if path.suffix == ".whl":
        return wheel_signature(path)
    if path.name.endswith(".tar.gz"):
        return sdist_signature(path)
    raise ReleaseError(f"Unexpected release artifact: {path.name}")


def compare_builds(first: Path, second: Path) -> None:
    first_artifacts = {path.name: artifact_signature(path) for path in first.iterdir() if path.is_file()}
    second_artifacts = {path.name: artifact_signature(path) for path in second.iterdir() if path.is_file()}
    if first_artifacts != second_artifacts:
        raise ReleaseError("Reproducible build check failed: artifact content signatures differ.")


def copy_artifacts(source: Path, out_dir: Path) -> None:
    out_dir.mkdir(exist_ok=True)
    for artifact in source.iterdir():
        if artifact.is_file():
            shutil.copy2(artifact, out_dir / artifact.name)


def write_extra_requirements(metadata: dict, tmp: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for extra, requirements in metadata.get("optional-dependencies", {}).items():
        path = tmp / f"{extra}.requirements.txt"
        path.write_text("\n".join(requirements) + "\n", encoding="utf-8")
        files[extra] = path
    return files


def emit_sboms(root: Path, out_dir: Path, metadata: dict, tmp: Path) -> None:
    cyclonedx = venv_bin(root, "cyclonedx-py")
    if not cyclonedx.exists():
        raise ReleaseError("cyclonedx-py is missing. Run `make install-governance` first.")
    run([str(cyclonedx), "environment", "--output-file", str(out_dir / "sbom.json")], cwd=root)
    for extra, req_file in write_extra_requirements(metadata, tmp).items():
        run([str(cyclonedx), "requirements", str(req_file), "--output-file", str(out_dir / f"sbom-{extra}.json")], cwd=root)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    metadata = project_metadata(root)
    version = metadata["version"]

    check_tag_matches_version(current_tag(root), version)
    check_changelog((root / "CHANGELOG.md").read_text(encoding="utf-8"), version)

    with tempfile.TemporaryDirectory(prefix="crk-release-") as tmp_name:
        tmp = Path(tmp_name)
        first = build_once(root, tmp / "first")
        second = build_once(root, tmp / "second")
        compare_builds(first, second)
        out_dir = root / "dist"
        copy_artifacts(first, out_dir)
        emit_sboms(root, out_dir, metadata, tmp)
    print(f"Release readiness passed for v{version}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ReleaseError as exc:
        print(f"release readiness failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
