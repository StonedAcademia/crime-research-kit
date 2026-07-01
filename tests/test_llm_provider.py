import pytest

from case_builder.llm.provider import (
    DEFAULT_MODEL_SPEC,
    active_model_spec,
    is_local_provider,
    parse_model_spec,
)


def test_parse_model_spec_splits_provider_and_model():
    assert parse_model_spec("ollama:llama3.1") == ("ollama", "llama3.1")
    assert parse_model_spec("anthropic:claude-sonnet-5") == ("anthropic", "claude-sonnet-5")


def test_parse_model_spec_rejects_malformed_specs():
    for bad in ("", "ollama", ":model", "provider:"):
        with pytest.raises(ValueError):
            parse_model_spec(bad)


def test_active_model_spec_defaults_local(monkeypatch):
    monkeypatch.delenv("TRCR_MODEL", raising=False)

    assert active_model_spec() == parse_model_spec(DEFAULT_MODEL_SPEC)
    assert is_local_provider(active_model_spec()[0]) is True


def test_active_model_spec_reads_env(monkeypatch):
    monkeypatch.setenv("TRCR_MODEL", "anthropic:claude-sonnet-5")

    provider, model = active_model_spec()

    assert provider == "anthropic"
    assert is_local_provider(provider) is False


def test_get_chat_model_hints_at_llm_extra_when_langchain_missing(monkeypatch):
    import builtins

    from case_builder.llm import provider as provider_module

    real_import = builtins.__import__

    def block_langchain(name, *args, **kwargs):
        if name.startswith("langchain"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_langchain)

    with pytest.raises(RuntimeError, match=r"\[llm\]"):
        provider_module.get_chat_model("ollama:llama3.1")
