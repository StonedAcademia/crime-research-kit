#!/usr/bin/env python3
"""Build the package from a git archive of HEAD and import-check the wheel."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EPOCH = "1735689600"


def venv_python(path: Path) -> Path:
    if sys.platform == "win32":
        return path / "Scripts" / "python.exe"
    return path / "bin" / "python"


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def create_archive_checkout(dest: Path) -> Path:
    archive = dest / "head.tar"
    source = dest / "source"
    source.mkdir()
    run(["git", "archive", "--format=tar", "-o", str(archive), "HEAD"], cwd=ROOT)
    with tarfile.open(archive) as bundle:
        bundle.extractall(source)
    return source


def build_from_archive(source: Path, python: Path, dist_dir: Path) -> None:
    run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "build"], cwd=source)
    env = {**os.environ, "SOURCE_DATE_EPOCH": os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_EPOCH)}
    run([str(python), "-m", "build", "--outdir", str(dist_dir)], cwd=source, env=env)


def import_check_wheel(python: Path, wheel: Path) -> None:
    run([str(python), "-m", "pip", "install", "--disable-pip-version-check", str(wheel)], cwd=ROOT)
    code = "import case_builder; import case_builder.cli; import case_builder.mcp.server"
    run([str(python), "-c", code], cwd=ROOT)


def main() -> int:
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="crk-build-") as tmp_name:
        tmp = Path(tmp_name)
        source = create_archive_checkout(tmp)
        build_env = tmp / "venv"
        venv.EnvBuilder(with_pip=True).create(build_env)
        python = venv_python(build_env)
        temp_dist = tmp / "dist"
        temp_dist.mkdir()
        build_from_archive(source, python, temp_dist)
        wheels = sorted(temp_dist.glob("*.whl"))
        if not wheels:
            raise SystemExit("Build did not produce a wheel.")
        import_check_wheel(python, wheels[0])
        for artifact in temp_dist.iterdir():
            shutil.copy2(artifact, out_dir / artifact.name)
            print(f"wrote {out_dir / artifact.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
