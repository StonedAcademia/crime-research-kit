"""Self-hosted chat-model resolution with an Ollama default."""

from __future__ import annotations

from case_builder.core.config import DEFAULT_MODEL_SPEC, model_spec

SUPPORTED_PROVIDERS = frozenset({"ollama"})


def parse_model_spec(spec: str, *, validate_provider: bool = True) -> tuple[str, str]:
    """Split 'provider:model' into its parts, validating both are present."""
    provider, separator, model = (spec or "").partition(":")
    if not separator or not provider.strip() or not model.strip():
        raise ValueError(
            "CRK_MODEL must look like 'provider:model' "
            f"(e.g. '{DEFAULT_MODEL_SPEC}'), got: {spec!r}"
        )
    provider = provider.strip()
    if validate_provider and provider not in SUPPORTED_PROVIDERS:
        allowed = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise ValueError(f"CRK_MODEL provider must be self-hosted. Supported providers: {allowed}.")
    return provider, model.strip()


def active_model_spec() -> tuple[str, str]:
    return parse_model_spec(model_spec())


def is_local_provider(provider: str) -> bool:
    return provider in SUPPORTED_PROVIDERS


def get_chat_model(spec: str | None = None):
    """Return a langchain chat model for the requested or configured spec."""
    provider, model = parse_model_spec(spec) if spec else active_model_spec()
    try:
        from langchain.chat_models import init_chat_model
    except ImportError as exc:
        raise RuntimeError(
            "LLM support requires the llm extra. Install with `pip install -e '.[llm]'` "
            "(including the local Ollama provider package)."
        ) from exc
    return init_chat_model(model, model_provider=provider)
