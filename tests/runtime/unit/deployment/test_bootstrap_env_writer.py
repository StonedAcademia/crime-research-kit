from __future__ import annotations

import os
import stat

import pytest

from deployment.scripts import bootstrap_env


def test_render_dotenv_sorts_quotes_and_rejects_newlines():
    text = bootstrap_env.render_dotenv({"B": "two words", "A": "plain"})
    assert text == 'A=plain\nB="two words"\n'
    with pytest.raises(ValueError):
        bootstrap_env.render_dotenv({"A": "bad\nvalue"})


def test_write_secure_creates_restricted_file(tmp_path):
    path = tmp_path / ".env"
    result = bootstrap_env.write_secure(path, "A=1\n")
    assert result.written
    assert path.read_text(encoding="utf-8") == "A=1\n"
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_write_secure_refuses_existing_file_without_force(tmp_path):
    path = tmp_path / ".env"
    path.write_text("OLD=1\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        bootstrap_env.write_secure(path, "NEW=1\n")
    assert path.read_text(encoding="utf-8") == "OLD=1\n"
    bootstrap_env.write_secure(path, "NEW=1\n", force=True)
    assert path.read_text(encoding="utf-8") == "NEW=1\n"


def test_write_secure_refuses_symlink(tmp_path):
    target = tmp_path / "target"
    path = tmp_path / ".env"
    target.write_text("OLD=1\n", encoding="utf-8")
    path.symlink_to(target)
    with pytest.raises(ValueError):
        bootstrap_env.write_secure(path, "NEW=1\n", force=True)


def test_atomic_write_cleans_temp_files(tmp_path):
    path = tmp_path / ".env"
    bootstrap_env.write_secure(path, "A=1\n")
    assert sorted(p.name for p in tmp_path.iterdir()) == [".env"]
