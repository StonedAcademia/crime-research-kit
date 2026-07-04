from __future__ import annotations

from deployment.scripts import bootstrap_env


def test_core_schema_has_no_fields():
    assert bootstrap_env.schema_for("core") == []


def test_self_hosted_schema_contains_prompted_values():
    fields = {field.name: field for field in bootstrap_env.schema_for("self-hosted")}
    assert {"CRK_MODEL", "CRK_EMBED_MODEL", "CRK_SEARXNG_HOST_PORT", "SEARXNG_BASE_URL"} <= set(fields)
    assert fields["CRK_MODEL"].default == "ollama:llama3.1"
    assert fields["SEARXNG_BASE_URL"].default == "http://127.0.0.1:18080/"
    assert not any(field.sensitive for field in fields.values())


def test_derived_searxng_base_url_tracks_port():
    values = bootstrap_env.derive_values({"CRK_SEARXNG_HOST_PORT": "19080"})
    assert values["SEARXNG_BASE_URL"] == "http://127.0.0.1:19080/"
    assert bootstrap_env.derive_values({"SEARXNG_BASE_URL": "http://example.test"})["SEARXNG_BASE_URL"].endswith("/")


def test_model_port_and_url_validation():
    assert not bootstrap_env.validate_values({"CRK_MODEL": "ollama:llama3.1"}, "self-hosted")
    assert bootstrap_env.validate_values({"CRK_MODEL": "openai:gpt-test"}, "self-hosted")
    for value in ("", "abc", "0", "65536"):
        assert bootstrap_env.validate_values({"CRK_SEARXNG_HOST_PORT": value}, "self-hosted")
    assert bootstrap_env.validate_values({"SEARXNG_BASE_URL": "not-a-url"}, "self-hosted")


def test_live_test_fields_are_not_default_self_hosted_fields():
    self_hosted = {field.name for field in bootstrap_env.schema_for("self-hosted")}
    live = {field.name for field in bootstrap_env.schema_for("live-tests")}
    assert "CRK_LIVE_MKULTRA" in live
    assert "CRK_LIVE_MKULTRA" not in self_hosted
