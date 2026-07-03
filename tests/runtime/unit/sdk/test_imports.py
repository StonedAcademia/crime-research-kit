from __future__ import annotations

import importlib
import sys


LEGACY_ROOTS = {"adapters", "core", "pipeline"}


def drop_imported_roots(*roots: str) -> None:
    for name in list(sys.modules):
        if name in roots or any(name.startswith(f"{root}.") for root in roots):
            sys.modules.pop(name, None)


def test_sdk_imports_without_legacy_runtime_packages():
    drop_imported_roots("crime_research_kit", *LEGACY_ROOTS)

    sdk = importlib.import_module("crime_research_kit.sdk")

    assert sdk.CrkContext().case_dir is None
    assert sdk.OperationResult(operation="case.info").ok is True
    assert sdk.OperationSpec("example").tags == ()
    assert sdk.SafetyTier.READ.value == "read"
    assert sdk.list_operations() == ()
    assert not (LEGACY_ROOTS & set(sys.modules))


def test_top_level_package_exports_only_sdk_namespace():
    drop_imported_roots("crime_research_kit", *LEGACY_ROOTS)

    package = importlib.import_module("crime_research_kit")

    assert package.__all__ == ["sdk"]
    assert package.sdk.CrkContext(dry_run=True).dry_run is True
    assert package.sdk.OperationResult(operation="case.info").operation == "case.info"
    assert not {"adapters", "core", "pipeline", "case_builder"} & set(package.__all__)
    assert not (LEGACY_ROOTS & set(sys.modules))
