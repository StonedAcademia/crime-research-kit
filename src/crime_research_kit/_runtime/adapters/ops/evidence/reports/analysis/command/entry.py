"""Analysis chart export command entrypoint."""

from __future__ import annotations

import argparse


def export_analysis_charts(_args: argparse.Namespace) -> None:
    raise SystemExit("Standalone analysis chart exports are retired; use export-case-visuals.")
