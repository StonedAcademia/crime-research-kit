"""Governance: tracked Markdown links and marked CLI help snippets stay current."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

from tests.helpers import KIT_ROOT


LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
HELP_MARKER_RE = re.compile(r"^\s*<!--\s*cli-help:\s*(.*?)\s*-->\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:")


def tracked_markdown_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=KIT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line and (KIT_ROOT / line).exists()]


def iter_doc_lines(path: Path):
    in_fence = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield lineno, re.sub(r"`[^`]*`", "", line)


def split_link_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split()[0]


def slug_heading(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("`", "").lower()
    text = re.sub(r"[^a-z0-9 _-]", "", text)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text


def heading_slugs(path: Path) -> set[str]:
    slugs: set[str] = set()
    seen: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = slug_heading(match.group(2))
        count = seen.get(base, 0)
        seen[base] = count + 1
        slugs.add(base if count == 0 else f"{base}-{count}")
    return slugs


def test_tracked_markdown_relative_links_and_anchors_resolve():
    failures: list[str] = []
    for rel in tracked_markdown_files():
        source = KIT_ROOT / rel
        for lineno, line in iter_doc_lines(source):
            for match in LINK_RE.finditer(line):
                target = split_link_target(match.group(1))
                if target.startswith(EXTERNAL_SCHEMES) or target.startswith("#"):
                    continue
                target_path, _, fragment = target.partition("#")
                if not target_path:
                    continue
                resolved = (source.parent / unquote(target_path)).resolve()
                try:
                    resolved.relative_to(KIT_ROOT)
                except ValueError:
                    failures.append(f"{rel}:{lineno} escapes repo: {target}")
                    continue
                if not resolved.exists():
                    failures.append(f"{rel}:{lineno} missing target: {target}")
                    continue
                if fragment and resolved.suffix == ".md" and unquote(fragment) not in heading_slugs(resolved):
                    failures.append(f"{rel}:{lineno} missing anchor: {target}")
    assert not failures, "broken Markdown links:\n" + "\n".join(failures)


def run_help_command(command: str) -> str:
    args = shlex.split(command)
    assert "--help" in args, f"cli-help marker must include --help: {command}"
    if args and args[0] == "python":
        args[0] = sys.executable
    env = {**os.environ, "PYTHONPATH": str(KIT_ROOT / "src")}
    return subprocess.run(args, cwd=KIT_ROOT, check=True, capture_output=True, text=True, env=env).stdout


def test_marked_cli_help_snippets_match_live_output():
    failures: list[str] = []
    for rel in tracked_markdown_files():
        lines = (KIT_ROOT / rel).read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines):
            marker = HELP_MARKER_RE.match(line)
            if not marker:
                continue
            fence_start = next((i for i in range(idx + 1, len(lines)) if lines[i].startswith("```")), None)
            fence_end = None if fence_start is None else next(
                (i for i in range(fence_start + 1, len(lines)) if lines[i].startswith("```")),
                None,
            )
            if fence_start is None or fence_end is None:
                failures.append(f"{rel}:{idx + 1} marker is not followed by a fenced help block")
                continue
            documented = "\n".join(lines[fence_start + 1 : fence_end]).rstrip()
            live = run_help_command(marker.group(1)).rstrip()
            if documented != live:
                failures.append(f"{rel}:{idx + 1} help snippet drift: {marker.group(1)}")
    assert not failures, "CLI help documentation drift:\n" + "\n".join(failures)
