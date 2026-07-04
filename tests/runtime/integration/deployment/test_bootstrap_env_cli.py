from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

from tests.helpers import KIT_ROOT

HELPER = KIT_ROOT / "deployment" / "scripts" / "bootstrap_env.py"


def run_helper(*args: str, input_text: str | None = None):
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        cwd=KIT_ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def test_noninteractive_self_hosted_writes_defaults(tmp_path):
    env_file = tmp_path / ".env"
    result = run_helper("configure", "--workflow", "self-hosted", "--env-file", str(env_file), "--non-interactive")
    assert result.returncode == 0, result.stderr
    text = env_file.read_text(encoding="utf-8")
    assert "CRK_MODEL=ollama:llama3.1\n" in text
    assert "SEARXNG_BASE_URL=http://127.0.0.1:18080/\n" in text
    if os.name == "posix":
        assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


def test_set_port_derives_base_url_and_dry_run_does_not_write(tmp_path):
    env_file = tmp_path / ".env"
    result = run_helper(
        "configure",
        "--workflow",
        "self-hosted",
        "--env-file",
        str(env_file),
        "--non-interactive",
        "--dry-run",
        "--set",
        "CRK_SEARXNG_HOST_PORT=19080",
    )
    assert result.returncode == 0, result.stderr
    assert "Would write" in result.stdout
    assert not env_file.exists()
    result = run_helper(
        "configure",
        "--workflow",
        "self-hosted",
        "--env-file",
        str(env_file),
        "--non-interactive",
        "--set",
        "CRK_SEARXNG_HOST_PORT=19080",
    )
    assert result.returncode == 0, result.stderr
    assert "SEARXNG_BASE_URL=http://127.0.0.1:19080/\n" in env_file.read_text(encoding="utf-8")


def test_invalid_values_and_existing_file_are_safe(tmp_path):
    env_file = tmp_path / ".env"
    result = run_helper(
        "configure",
        "--workflow",
        "self-hosted",
        "--env-file",
        str(env_file),
        "--non-interactive",
        "--set",
        "CRK_MODEL=openai:gpt-test",
    )
    assert result.returncode != 0
    assert "CRK_MODEL must be an ollama" in result.stderr
    env_file.write_text("OLD=1\n", encoding="utf-8")
    result = run_helper("configure", "--workflow", "self-hosted", "--env-file", str(env_file), "--non-interactive")
    assert result.returncode != 0
    assert env_file.read_text(encoding="utf-8") == "OLD=1\n"
    result = run_helper("configure", "--workflow", "self-hosted", "--env-file", str(env_file), "--non-interactive", "--force")
    assert result.returncode == 0, result.stderr
    assert "OLD=1\n" not in env_file.read_text(encoding="utf-8")


def test_scripted_interactive_prompts_and_core_workflow(tmp_path):
    env_file = tmp_path / ".env"
    answers = "ollama:custom\nBAAI/bge-small-en-v1.5\n19081\n\nY\n"
    result = run_helper("configure", "--workflow", "self-hosted", "--env-file", str(env_file), input_text=answers)
    assert result.returncode == 0, result.stderr
    text = env_file.read_text(encoding="utf-8")
    assert "CRK_MODEL=ollama:custom\n" in text
    assert "SEARXNG_BASE_URL=http://127.0.0.1:19081/\n" in text
    result = run_helper("configure", "--workflow", "core", "--env-file", str(tmp_path / "core.env"), "--non-interactive")
    assert result.returncode == 0
    assert not (tmp_path / "core.env").exists()


def test_exposed_searxng_generates_secret_without_printing_it(tmp_path):
    env_file = tmp_path / ".env"
    settings_file = tmp_path / "settings.local.yml"
    result = run_helper(
        "configure",
        "--workflow",
        "exposed-searxng",
        "--env-file",
        str(env_file),
        "--searxng-settings-file",
        str(settings_file),
        "--non-interactive",
    )
    assert result.returncode == 0, result.stderr
    assert "secret_key=[REDACTED]" in result.stdout
    settings_text = settings_file.read_text(encoding="utf-8")
    assert "change-me-before-sharing" not in settings_text
    assert "CRK_SEARXNG_SETTINGS_FILE=" in env_file.read_text(encoding="utf-8")
    if os.name == "posix":
        assert stat.S_IMODE(settings_file.stat().st_mode) == 0o600
