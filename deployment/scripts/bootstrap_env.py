#!/usr/bin/env python3
"""Compatibility entrypoint for CRK bootstrap environment configuration."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deployment.scripts.bootstrap.cli import build_parser, configure, main
from deployment.scripts.bootstrap.core import (
    ConfigField,
    WriteResult,
    derive_values,
    ensure_writable,
    render_dotenv,
    schema_for,
    searxng_local_settings,
    validate_values,
    write_secure,
)

__all__ = [
    "ConfigField",
    "WriteResult",
    "build_parser",
    "configure",
    "derive_values",
    "ensure_writable",
    "main",
    "render_dotenv",
    "schema_for",
    "searxng_local_settings",
    "validate_values",
    "write_secure",
]


if __name__ == "__main__":
    raise SystemExit(main())
