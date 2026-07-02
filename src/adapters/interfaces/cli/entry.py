"""Ledger CLI executable entry."""

from __future__ import annotations

from core.casefile import CasefileError

from .parser import build_parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except CasefileError as exc:
        raise SystemExit(str(exc)) from exc
    return 0
