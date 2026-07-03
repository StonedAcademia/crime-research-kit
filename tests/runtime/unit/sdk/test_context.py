from pathlib import Path
from types import MappingProxyType

from crime_research_kit.sdk.context import CrkContext, TransportMode


def test_context_coerces_roots_and_defaults_to_public_safe_reads():
    context = CrkContext(repo_root=".", cases_root="data/cases", case_dir="demo")

    assert context.repo_root == Path(".")
    assert context.cases_root == Path("data/cases")
    assert context.case_dir == Path("demo")
    assert context.include_private is False
    assert context.transport is TransportMode.AUTO


def test_context_resolves_case_slug_against_cases_root():
    context = CrkContext(cases_root="data/cases")

    assert context.resolve_case_ref("demo_case") == Path("data/cases/demo_case")
    assert context.resolve_case_ref("data/cases/demo_case") == Path("data/cases/demo_case")
    assert context.with_case_dir("demo_case").resolve_case_ref() == Path("data/cases/demo_case")


def test_context_freezes_settings_and_metadata():
    context = CrkContext(settings={"qdrant_url": "http://localhost:6333"}, metadata={"caller": "test"})

    assert isinstance(context.settings, MappingProxyType)
    assert isinstance(context.metadata, MappingProxyType)
    assert context.settings["qdrant_url"] == "http://localhost:6333"


def test_context_copy_helpers_preserve_immutability():
    context = CrkContext(case_dir="one", include_private=False, transport="auto")

    updated = (
        context.with_case_dir("two")
        .with_privacy(include_private=True)
        .with_transport(TransportMode.SUBPROCESS)
        .with_settings(embed_model="local")
    )

    assert context.case_dir == Path("one")
    assert context.include_private is False
    assert context.transport is TransportMode.AUTO
    assert context.settings == {}
    assert updated.case_dir == Path("two")
    assert updated.include_private is True
    assert updated.transport is TransportMode.SUBPROCESS
    assert updated.settings["embed_model"] == "local"
