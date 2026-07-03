# CLI Interface Adapter

This package exposes command-line entrypoints that compose operation modules
without owning ledger behavior.

## Entrypoints

- `crk-ledger` is implemented by `entry.py` and `app.py`; ledger command
  wrappers live in `commands/`.
- `cr-kit` keeps the public `src/cli.py` shim, with the Typer app and Namespace
  bridge in `case_builder/`.

Both CLIs are Typer applications. Command functions only translate typed CLI
parameters into the same `argparse.Namespace` shape consumed by the existing
operation handlers.

## Surface Contract

`docs/guides/cli-surface.json` freezes every public command name, command alias,
positional argument, flag alias, default, required bit, boolean-flag bit, and
choice list. Governance compares the live Click/Typer command tree against that
snapshot.

Changing the public CLI surface requires deliberately regenerating the snapshot
and updating docs/tests that depend on the changed operator contract.
