from pathlib import Path

from crime_research_kit.sdk import CaseClient, CrkClient
from crime_research_kit.sdk.context import CrkContext
from crime_research_kit.sdk.operations import SafetyTier


def test_crk_client_uses_default_context():
    client = CrkClient()

    assert isinstance(client.context, CrkContext)
    assert client.context.include_private is False


def test_crk_client_returns_case_scoped_handle():
    client = CrkClient(CrkContext(cases_root="data/cases"))
    case = client.case("demo_case")

    assert isinstance(case, CaseClient)
    assert case.context.case_dir == Path("demo_case")
    assert case.case_dir == Path("data/cases/demo_case")


def test_case_client_preserves_explicit_case_path():
    client = CrkClient(CrkContext(cases_root="data/cases"))
    case = client.case("tmp/case")

    assert case.case_dir == Path("tmp/case")


def test_clients_expose_catalog_metadata_without_runtime_imports():
    client = CrkClient()
    case = client.case("demo_case")

    assert client.operation("cases.create").cli_command == "crk-ledger init-case"
    assert case.operation("records.list").safety_tier is SafetyTier.READ
    assert {spec.name for spec in case.operations("extractions")} >= {
        "extractions.draft",
        "extractions.import_reviewed",
    }


def test_case_client_privacy_copy_does_not_mutate_parent_context():
    client = CrkClient(CrkContext(include_private=False))
    public_case = client.case("demo_case")
    private_case = public_case.with_privacy(include_private=True)

    assert public_case.context.include_private is False
    assert private_case.context.include_private is True
    assert client.context.include_private is False
