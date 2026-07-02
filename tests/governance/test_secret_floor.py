"""Governance: stdlib secret-pattern floor before external gitleaks audit."""

from __future__ import annotations

import re
import subprocess

from tests.helpers import KIT_ROOT


# Policy source: docs/superpowers/specs/2026-07-02-governance-hardening-spec.md §5.
SECRET_PATTERNS = {
    "aws_access_key_id": re.compile(r"AKIA[0-9A-Z]{16}"),
    "pem_private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_classic_token": re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "github_pat": re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    "slack_token": re.compile(r"xox[bpars]-[A-Za-z0-9-]{10,}"),
    "literal_secret_assignment": re.compile(
        r"""(?ix)
        \b(api_key|apikey|secret|token|password)\b
        \s*[=:]\s*
        ["']([A-Za-z0-9+/_-]{20,})["']
        """
    ),
}
ALLOWLIST_PATHS = {
    ".gitleaks.toml",
    "tests/governance/test_secret_floor.py",
}
PLACEHOLDER_MARKERS = ("<", ">", "change", "changeme", "example", "synthetic", "placeholder")


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=KIT_ROOT, check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]


def read_text(path: str) -> str | None:
    try:
        return (KIT_ROOT / path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def is_placeholder(match: re.Match[str]) -> bool:
    text = match.group(0).lower()
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def test_tracked_text_files_do_not_contain_secret_floor_patterns():
    offenders = []
    for path in tracked_files():
        if path in ALLOWLIST_PATHS:
            continue
        text = read_text(path)
        if text is None:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                if is_placeholder(match):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{path}:{line} {name}")
    assert not offenders, f"secret-pattern floor hits: {offenders}"
