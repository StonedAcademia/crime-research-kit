"""CrkSettings is the single env reader; core stays env-free."""

from __future__ import annotations

import subprocess
from pathlib import Path

from core.config import (
    DEFAULT_MODEL_SPEC,
    DEFAULT_QDRANT_PORT,
    DEFAULT_SEARXNG_URL,
    CrkSettings,
)

SRC = Path(__file__).resolve().parents[4] / "src"


def test_defaults_match_constants(monkeypatch):
    for var in ("CRK_MODEL", "CRK_SEARXNG_URL", "CRK_QDRANT_PORT"):
        monkeypatch.delenv(var, raising=False)
    settings = CrkSettings()
    assert settings.model_spec == DEFAULT_MODEL_SPEC
    assert settings.searxng_url == DEFAULT_SEARXNG_URL
    assert settings.qdrant_port == DEFAULT_QDRANT_PORT


def test_env_names_are_preserved(monkeypatch):
    monkeypatch.setenv("CRK_MODEL", "ollama:test-model")
    monkeypatch.setenv("CRK_QDRANT_PORT", "7777")
    settings = CrkSettings()
    assert settings.model_spec == "ollama:test-model"
    assert settings.qdrant_port == 7777
    assert CrkSettings(qdrant_port=1).qdrant_port == 1  # populate_by_name allows explicit field kwargs


def test_settings_stay_at_process_boundaries():
    hits = subprocess.run(
        [
            "grep",
            "-rln",
            "CrkSettings(",
            str(SRC / "core"),
            str(SRC / "pipeline"),
            str(SRC / "adapters" / "ops"),
            str(SRC / "adapters" / "io"),
        ],
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    allowed = {str(SRC / "core" / "config.py")}
    assert set(hits) <= allowed, f"Settings() constructed deep in core: {hits}"
