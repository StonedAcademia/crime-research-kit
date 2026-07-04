from __future__ import annotations

import subprocess
import sys

from tests.helpers import KIT_ROOT

HELPER = KIT_ROOT / "deployment" / "scripts" / "bootstrap_env.py"
COMPOSE = KIT_ROOT / "deployment" / "scripts" / "local" / "compose.py"


def test_generated_env_can_feed_compose_config(tmp_path):
    env_file = KIT_ROOT / "deployment" / ".env"
    local_settings = tmp_path / "settings.local.yml"
    original = env_file.read_text(encoding="utf-8") if env_file.exists() else None
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(HELPER),
                "configure",
                "--workflow",
                "exposed-searxng",
                "--env-file",
                str(env_file),
                "--searxng-settings-file",
                str(local_settings),
                "--non-interactive",
                "--force",
            ],
            cwd=KIT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        config = subprocess.run(
            [sys.executable, str(COMPOSE), "config"],
            cwd=KIT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if config.returncode != 0 and "docker" in config.stderr.lower():
            return
        assert config.returncode == 0, config.stderr
        assert str(local_settings) in config.stdout
    finally:
        if original is None:
            env_file.unlink(missing_ok=True)
        else:
            env_file.write_text(original, encoding="utf-8")
