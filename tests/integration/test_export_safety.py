"""Integration: public exports run aggregate privacy and provenance gates."""

from __future__ import annotations

import csv
import importlib.util
import shutil

import pytest

from tests.helpers import KIT_ROOT, TCR_PATH


def load_tcr():
    spec = importlib.util.spec_from_file_location("tcr", TCR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_fixture(tmp_path, name: str):
    dest = tmp_path / name
    shutil.copytree(KIT_ROOT / "data" / "examples" / name, dest)
    return dest


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_public_export_filters_private_rows_and_keeps_provenance(tmp_path):
    tcr = load_tcr()
    case_dir = copy_fixture(tmp_path, "synthetic_case")

    tcr.main(["export-manim", str(case_dir)])

    people = read_csv(case_dir / "exports" / "manim" / "people.csv")
    claims = read_csv(case_dir / "exports" / "manim" / "claims.csv")
    assert all(row["public_export"] != "False" for row in people + claims)
    assert all(row["source_ids"] for row in claims)
    assert "123 Main Street" not in (case_dir / "exports" / "manim" / "people.csv").read_text(encoding="utf-8")


def test_unsafe_fixture_public_export_fails_with_named_blockers(tmp_path, capsys):
    tcr = load_tcr()
    case_dir = copy_fixture(tmp_path, "unsafe_case_fixture")

    with pytest.raises(SystemExit) as exc:
        tcr.main(["export-manim", str(case_dir)])

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert exc.value.code == 1
    assert "public export blocked" in output
    assert "unsupported_claim" in output
    assert "minor_public" in output
    assert "contact_or_address_pattern" in output or "address_or_contact_info" in output
    assert "lead_relationship_public" in output


def test_include_private_export_skips_public_gate_for_internal_review(tmp_path, capsys):
    tcr = load_tcr()
    case_dir = copy_fixture(tmp_path, "unsafe_case_fixture")

    tcr.main(["export-manim", str(case_dir), "--include-private"])

    captured = capsys.readouterr()
    people = read_csv(case_dir / "exports" / "manim" / "people.csv")
    assert "internal export requested" in captured.out
    assert {row["entity_id"] for row in people} >= {"EUNSAFE_PRIVATE", "EUNSAFE_MINOR"}
