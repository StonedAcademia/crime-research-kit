"""Provider-pluggable chat-model resolution with a local default."""

from __future__ import annotations

import os

DEFAULT_MODEL_SPEC = "ollama:llama3.1"
LOCAL_PROVIDERS = frozenset({"ollama"})


def parse_model_spec(spec: str) -> tuple[str, str]:
    """Split 'provider:model' into its parts, validating both are present."""
    provider, separator, model = (spec or "").partition(":")
    if not separator or not provider.strip() or not model.strip():
        raise ValueError(
            "TRCR_MODEL must look like 'provider:model' "
            f"(e.g. '{DEFAULT_MODEL_SPEC}'), got: {spec!r}"
        )
    return provider.strip(), model.strip()


def active_model_spec() -> tuple[str, str]:
    return parse_model_spec(os.environ.get("TRCR_MODEL") or DEFAULT_MODEL_SPEC)


def is_local_provider(provider: str) -> bool:
    return provider in LOCAL_PROVIDERS


def get_chat_model(spec: str | None = None):
    """Return a langchain chat model for the requested or configured spec."""
    provider, model = parse_model_spec(spec) if spec else active_model_spec()
    try:
        from langchain.chat_models import init_chat_model
    except ImportError as exc:
        raise RuntimeError(
            "LLM support requires the llm extra. Install with `pip install -e '.[llm]'` "
            "(plus the provider package, e.g. langchain-ollama or langchain-anthropic)."
        ) from exc
    return init_chat_model(model, model_provider=provider)
