import json
from pathlib import Path

from adapters.ops import exports as export_ops
from adapters.ops import query as query_ops
from adapters.ops import review as review_ops
from adapters.ops.runner import CrkRunner
from tests.helpers import KIT_ROOT

REPO_ROOT = KIT_ROOT


def dry_runner() -> CrkRunner:
    return CrkRunner(repo_root=REPO_ROOT, dry_run=True)


def add_private_claim(case_dir: Path) -> None:
    claims = case_dir / "records" / "claims.jsonl"
    row = {
        "claim_id": "CPRIVATE",
        "claim": "Private claim.",
        "status": "unverified",
        "confidence": 0.1,
        "source_ids": ["SDEMO0001"],
        "public_export": False,
    }
    claims.write_text(claims.read_text(encoding="utf-8") + json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")


def test_get_records_excludes_private_by_default(synthetic_case_copy):
    add_private_claim(synthetic_case_copy)

    public = query_ops.get_records(str(synthetic_case_copy), "claims")
    internal = query_ops.get_records(str(synthetic_case_copy), "claims", include_private=True)

    assert all(row.get("claim_id") != "CPRIVATE" for row in public.data["records"])
    assert public.data["filtered"] == 1
    assert any(row.get("claim_id") == "CPRIVATE" for row in internal.data["records"])


def test_get_records_rejects_unknown_type(synthetic_case_copy):
    result = query_ops.get_records(str(synthetic_case_copy), "nonsense")

    assert result.ok is False
    assert "sources" in result.errors[0]


def test_link_names_repeats_name_flags():
    result = query_ops.link_names(dry_runner(), "data/cases/x", names=["Jane Doe|JD", "John Roe"])

    assert result.command[2] == "link-names"
    assert result.command.count("--name") == 2


def test_review_audits_plan_expected_subcommands():
    runner = dry_runner()
    expectations = {
        review_ops.audit_contradictions: "audit-contradictions",
        review_ops.review_narrative_readiness: "review-narrative-readiness",
        review_ops.audit_privacy_redactions: "audit-privacy-redactions",
        review_ops.audit_public_export: "audit-public-export",
        review_ops.audit_source_independence: "audit-source-independence",
    }

    for func, subcommand in expectations.items():
        assert func(runner, "data/cases/x").command[2] == subcommand


def test_exports_default_public_safe():
    runner = dry_runner()

    public = export_ops.export_manim(runner, "data/cases/x")
    internal = export_ops.export_manim(runner, "data/cases/x", include_private=True)

    assert "--include-private" not in public.command
    assert "--include-private" in internal.command


def test_export_timeline_accepts_out_dir():
    result = export_ops.export_timeline(
        dry_runner(),
        "data/cases",
        out_dir="data/exports/timeline_internal",
        include_private=True,
    )

    assert result.command[2] == "export-timeline"
    assert result.command[result.command.index("--out-dir") + 1] == "data/exports/timeline_internal"
