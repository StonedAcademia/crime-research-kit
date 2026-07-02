"""Repository-wide governance for directory shape and file size."""

from __future__ import annotations

import ast
import subprocess
import tokenize
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from tests.helpers import KIT_ROOT

MIN_FILES_PER_DIR = 1
MAX_FILES_PER_DIR = 4
MIN_DIRS_PER_DIR = 0
MAX_DIRS_PER_DIR = 3
MAX_NON_COMMENT_LOC = 200
SKIPPED_ROOTS = (Path("data"), Path("docs/superpowers"))

HASH_COMMENT_SUFFIXES = {".py", ".sh", ".yml", ".yaml", ".toml"}
HASH_COMMENT_NAMES = {"Dockerfile", "Makefile", ".dockerignore", ".gitignore", ".prototools"}
SLASH_COMMENT_SUFFIXES = {".css", ".js", ".mjs", ".ts", ".tsx"}


def is_skipped(path: Path) -> bool:
    return any(path == root or root in path.parents for root in SKIPPED_ROOTS)


def governed_paths() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files"], cwd=KIT_ROOT, text=True)
    return [Path(line) for line in output.splitlines() if line and not is_skipped(Path(line))]


def repo_shape(paths: list[Path]) -> tuple[set[Path], dict[Path, int], dict[Path, set[str]]]:
    dirs: set[Path] = {Path(".")}
    file_counts: dict[Path, int] = defaultdict(int)
    child_dirs: dict[Path, set[str]] = defaultdict(set)
    for path in paths:
        parent = path.parent
        dirs.add(parent)
        file_counts[parent] += 1
        while parent != Path("."):
            dirs.add(parent.parent)
            child_dirs[parent.parent].add(parent.name)
            parent = parent.parent
    return dirs, file_counts, child_dirs


def test_directories_keep_small_bounded_shape():
    dirs, file_counts, child_dirs = repo_shape(governed_paths())
    offenders = []
    for directory in sorted(dirs):
        files = file_counts.get(directory, 0)
        children = len(child_dirs.get(directory, set()))
        if not MIN_FILES_PER_DIR <= files <= MAX_FILES_PER_DIR or not MIN_DIRS_PER_DIR <= children <= MAX_DIRS_PER_DIR:
            offenders.append(f"{directory.as_posix()} files={files} dirs={children}")

    assert offenders == []


def comment_ranges_for_python(path: Path) -> set[int]:
    ignored: set[int] = set()
    source = path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
                value = getattr(body[0], "value", None)
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    ignored.update(range(body[0].lineno, body[0].end_lineno + 1))
    for token in tokenize.tokenize(BytesIO(source.encode("utf-8")).readline):
        prefix = source_lines[token.start[0] - 1][: token.start[1]] if token.start[0] <= len(source_lines) else ""
        if token.type == tokenize.COMMENT and not prefix.strip():
            ignored.update(range(token.start[0], token.end[0] + 1))
    return ignored


def count_slash_comment_loc(lines: list[str]) -> int:
    count = 0
    in_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if in_block:
            in_block = "*/" not in stripped
            continue
        if stripped.startswith("/*"):
            in_block = "*/" not in stripped
            continue
        if stripped.startswith("//"):
            continue
        count += 1
    return count


def non_comment_loc(path: Path) -> int:
    absolute = KIT_ROOT / path
    try:
        text = absolute.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 0
    if path.suffix == ".py":
        ignored = comment_ranges_for_python(absolute)
        return sum(
            1
            for line_no, line in enumerate(text.splitlines(), start=1)
            if line_no not in ignored and line.strip()
        )
    if path.suffix in SLASH_COMMENT_SUFFIXES:
        return count_slash_comment_loc(text.splitlines())
    if path.suffix in HASH_COMMENT_SUFFIXES or path.name in HASH_COMMENT_NAMES:
        return sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))
    return sum(1 for line in text.splitlines() if line.strip())


def test_governed_files_stay_under_200_non_comment_loc():
    offenders = [
        f"{path.as_posix()} loc={non_comment_loc(path)}"
        for path in governed_paths()
        if non_comment_loc(path) > MAX_NON_COMMENT_LOC
    ]

    assert offenders == []
