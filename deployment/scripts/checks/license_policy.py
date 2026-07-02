#!/usr/bin/env python3
"""Apply the CRK dependency license policy to pip-licenses JSON output."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ALLOW_MARKERS = (
    "mit",
    "bsd",
    "apache",
    "python software foundation",
    "psf",
    "isc",
    "mozilla public license",
    "mpl-1.1",
    "mpl-2.0",
    "agpl",
    "affero general public license",
    "gpl",
    "general public license",
    "lgpl",
    "lesser general public license",
)
DENY_MARKERS = ("sspl", "server side public license")
# Some core packaging tools publish sparse license metadata in installed wheels.
# Keep this list small and source-specific so genuinely unknown licenses still surface.
LICENSE_METADATA_GAPS = {
    "setuptools": "MIT",
}


def venv_bin(name: str) -> Path:
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    suffix = ".exe" if sys.platform == "win32" else ""
    return ROOT / ".venv" / scripts / f"{name}{suffix}"


def pip_licenses_command() -> list[str] | None:
    venv_tool = venv_bin("pip-licenses")
    if venv_tool.exists():
        return [str(venv_tool)]
    found = shutil.which("pip-licenses")
    return [found] if found else None


def load_records(input_path: Path | None) -> list[dict]:
    if input_path is not None:
        return json.loads(input_path.read_text(encoding="utf-8"))
    command = pip_licenses_command()
    if command is None:
        print("SKIP (missing tool): pip-licenses is not installed; install the governance extra.")
        raise SystemExit(0)
    proc = subprocess.run([*command, "--format=json", "--with-system"], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def classify(license_text: str) -> str:
    text = license_text.lower()
    if any(marker in text for marker in DENY_MARKERS):
        return "denied"
    if any(marker in text for marker in ALLOW_MARKERS):
        return "allowed"
    return "unknown"


def normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def effective_license(name: str, license_text: str) -> str:
    if classify(license_text) != "unknown":
        return license_text
    return LICENSE_METADATA_GAPS.get(normalize_package_name(name), license_text)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Read pip-licenses JSON from a file instead of invoking pip-licenses.")
    args = parser.parse_args(argv)

    denied: list[str] = []
    unknown: list[str] = []
    for row in load_records(args.input):
        name = row.get("Name", "<unknown>")
        version = row.get("Version", "")
        license_text = effective_license(name, row.get("License", "UNKNOWN"))
        label = f"{name} {version}: {license_text}".strip()
        outcome = classify(license_text)
        if outcome == "denied":
            denied.append(label)
        elif outcome == "unknown":
            unknown.append(label)

    if denied:
        print("DENY: packages with SSPL-family licenses:")
        print("\n".join(f"- {item}" for item in denied))
        return 1
    if unknown:
        print("REVIEW: packages with licenses outside the allowlist:")
        print("\n".join(f"- {item}" for item in unknown))
    else:
        print("License policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
