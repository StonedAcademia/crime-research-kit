"""Filesystem writers for case visual export packages."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import write_csv
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.render import _environment, write_html
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.visual_export.assets import write_visual_assets
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.visual_export.package import (
    CONSOLE_SLUGS,
    RETIRED_VISUAL_ARTIFACTS,
    manifest,
)
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext


def write_audit(out: Path, audit: dict[str, list[dict[str, object]]]) -> None:
    for name, rows in audit.items():
        columns = sorted({column for row in rows for column in row}) or ["empty"]
        write_csv(out / f"{name}.csv", rows, columns)


def write_html_package(out: Path, package: dict[str, object]) -> None:
    _remove_retired_visual_artifacts(out)
    artifacts = ["index.html", *(f"consoles/{slug}.html" for slug in CONSOLE_SLUGS)]
    asset_artifacts = write_visual_assets(out, package)
    audit = package["audit"]
    assert isinstance(audit, dict)
    audit_artifacts = [f"audit/{name}.csv" for name in sorted(audit)]
    private_package = package.get("private_package")
    if isinstance(private_package, dict):
        private_audit = private_package["audit"]
        assert isinstance(private_audit, dict)
        audit_artifacts.extend(f"audit/private/{name}.csv" for name in sorted(private_audit))
    package["artifacts"] = artifacts + asset_artifacts + audit_artifacts
    write_html(out / "index.html", _render("layouts/visual.html.j2", package=package, console=None, asset_prefix=""))
    for slug, console in package["consoles"].items():
        write_html(out / "consoles" / f"{slug}.html", _render("layouts/visual.html.j2", package=package, console=console, asset_prefix="../"))
    (out / "manifest.json").write_text(json.dumps(manifest(package), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_github_static_site(ctx: AnalysisContext) -> Path:
    github_dir = ctx.cdir / "github_export"
    if ctx.out.resolve() != github_dir.resolve():
        shutil.rmtree(github_dir, ignore_errors=True)
        shutil.copytree(ctx.out, github_dir)
    github_dir.mkdir(parents=True, exist_ok=True)
    (github_dir / ".nojekyll").write_text("", encoding="utf-8")
    return github_dir


def _remove_retired_visual_artifacts(out: Path) -> None:
    for relative in RETIRED_VISUAL_ARTIFACTS:
        (out / relative).unlink(missing_ok=True)


def _render(template: str, **data: object) -> str:
    return _environment().get_template(template).render(**data)
