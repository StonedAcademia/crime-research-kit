"""CLI entry point for consolidated case visual exports."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import shutil

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.command.context import AnalysisContext, load_analysis_context
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.visual_export.package import build_package, bundle_package
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.visual_export.products import build_products
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.visual_export.site import write_audit, write_github_static_site, write_html_package
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import reject_legacy_export_dir
from crime_research_kit._runtime.core.casefile import case_path


def export_case_visuals(args: argparse.Namespace) -> None:
    include_private = bool(args.include_private)
    cdir = case_path(args.case_dir)
    requested_out = Path(args.out_dir).expanduser().resolve() if args.out_dir else None
    out = requested_out or cdir / "exports" / "internal" / "visuals"
    reject_legacy_export_dir(out)
    if include_private:
        private_ctx = _load_visual_context(args, out, include_private=True)
        public_ctx = _load_visual_context(args, out, include_private=False, skip_public_gate=True)
        generated = dt.datetime.now(dt.timezone.utc).isoformat()
        public_package = build_package(public_ctx, build_products(public_ctx), generated=generated)
        private_package = build_package(private_ctx, build_products(private_ctx), generated=generated)
        package = bundle_package(public_package, private_package)
        ctx = private_ctx
    else:
        ctx = _load_visual_context(args, out, include_private=False)
        package = build_package(ctx, build_products(ctx))
    write_audit(ctx.out / "audit", package["audit"])
    private_package = package.get("private_package")
    if private_package:
        write_audit(ctx.out / "audit" / "private", private_package["audit"])
    else:
        shutil.rmtree(ctx.out / "audit" / "private", ignore_errors=True)
    write_html_package(ctx.out, package)
    github_dir = write_github_static_site(ctx)
    print(f"Exported case visuals to {ctx.out}")
    print(f"Prepared GitHub Pages static site at {github_dir}")


def _load_visual_context(args: argparse.Namespace, out: Path, *, include_private: bool, skip_public_gate: bool = False) -> AnalysisContext:
    return load_analysis_context(
        argparse.Namespace(
            case_dir=args.case_dir,
            out_dir=str(out),
            clusters_dir=getattr(args, "clusters_dir", None),
            include_private=include_private,
            gate_name="export-case-visuals",
            skip_public_gate=skip_public_gate,
        )
    )
