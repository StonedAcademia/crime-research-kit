"""Bounded LLM agents and provider resolution for the case builder."""

from __future__ import annotations

from .provider import active_model_spec, get_chat_model, is_local_provider

__all__ = ["active_model_spec", "get_chat_model", "is_local_provider"]
