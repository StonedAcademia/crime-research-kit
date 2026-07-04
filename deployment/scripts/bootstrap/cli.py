"""CLI flow for the CRK bootstrap environment helper."""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

from deployment.scripts.bootstrap.core import (
    DEFAULT_ENV_FILE,
    DEFAULT_SEARXNG_SETTINGS,
    WORKFLOWS,
    derive_values,
    ensure_writable,
    render_dotenv,
    schema_for,
    searxng_local_settings,
    validate_values,
    write_secure,
)


def parse_set(values: list[str]) -> dict[str, str]:
    parsed = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"--set must be KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        parsed[key] = value
    return parsed


def prompt_values(fields, base: dict[str, str], stdin, stdout) -> dict[str, str]:
    values = dict(base)
    for field in fields:
        for _ in range(3):
            stdout.write(f"{field.label} [{values[field.name]}]: ")
            stdout.flush()
            answer = stdin.readline()
            if answer == "":
                break
            answer = answer.strip()
            if answer:
                values[field.name] = answer
            candidate = derive_values(values)
            if not validate_values({field.name: candidate[field.name]}, "self-hosted"):
                values = candidate
                break
            stdout.write("Invalid value; try again.\n")
        else:
            raise ValueError(f"Too many invalid attempts for {field.name}")
    return derive_values(values)


def yes_no(prompt: str, default: bool, stdin, stdout) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    stdout.write(f"{prompt} {suffix}: ")
    stdout.flush()
    answer = stdin.readline().strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def configure(args: argparse.Namespace) -> int:
    if args.workflow == "core":
        print("Core workflow selected; no environment file written.")
        return 0
    fields = schema_for(args.workflow)
    values = {field.name: field.default for field in fields}
    values.update(parse_set(args.sets))
    if not args.non_interactive:
        values = prompt_values(fields, values, sys.stdin, sys.stdout)
    values = derive_values(values)
    expose = args.workflow == "exposed-searxng"
    if args.workflow == "self-hosted" and not args.non_interactive:
        expose = not yes_no("Keep SearXNG bound to localhost only?", True, sys.stdin, sys.stdout)
    errors = validate_values(values, args.workflow)
    if errors:
        raise ValueError("; ".join(errors))
    env_file = args.env_file.expanduser()
    settings_file = args.searxng_settings_file.expanduser()
    force = args.force
    if env_file.exists() and not force and not args.non_interactive and yes_no(f"Replace {env_file}?", False, sys.stdin, sys.stdout):
        force = True
    if expose:
        values["CRK_SEARXNG_SETTINGS_FILE"] = str(settings_file.resolve(strict=False))
    ensure_writable(env_file, force)
    if expose:
        ensure_writable(settings_file, force)
    if args.dry_run:
        print(f"Would write {env_file.resolve(strict=False)}")
        if expose:
            print(f"Would write {settings_file.resolve(strict=False)} with generated secret_key=[REDACTED]")
        return 0
    if expose:
        secret = secrets.token_urlsafe(32)
        write_secure(settings_file, searxng_local_settings(secret), force=force, sensitive=True)
        print(f"Wrote {settings_file.resolve(strict=False)} with generated secret_key=[REDACTED]")
    write_secure(env_file, render_dotenv(values), force=force)
    print(f"Wrote {env_file.resolve(strict=False)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    config = sub.add_parser("configure")
    config.add_argument("--workflow", choices=sorted(WORKFLOWS), default="self-hosted")
    config.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    config.add_argument("--searxng-settings-file", type=Path, default=DEFAULT_SEARXNG_SETTINGS)
    config.add_argument("--non-interactive", action="store_true")
    config.add_argument("--force", action="store_true")
    config.add_argument("--dry-run", action="store_true")
    config.add_argument("--set", dest="sets", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "configure":
            return configure(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
