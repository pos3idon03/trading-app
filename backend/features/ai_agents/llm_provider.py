"""LLM provider with OpenAI primary and Google AI Studio Gemini fallback.

Authentication:
  - OpenAI  → OPENAI_API_KEY
  - Gemini  → GEMINI_API_KEY  (Google AI Studio key, not a Vertex service account)

LiteLLM model prefixes:
  - ``openai/``  for OpenAI models
  - ``gemini/``  for Google AI Studio Gemini models

Fallback is configured once at startup via ``litellm.fallbacks`` (module-level
list read automatically on every completion call). ``get_llm_for_crew`` returns
a plain model string — CrewAI passes it directly to ``litellm.completion``.
"""
import os
from typing import Optional

import litellm

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)

# Maps a user-facing slug to (primary_litellm_model, fallback_litellm_model).
_FALLBACK_MAP: dict[str, tuple[str, str]] = {
    "gpt-4o-mini": ("openai/gpt-4o-mini", "gemini/gemini-3-flash-preview"),
    "gpt-4o": ("openai/gpt-4o", "gemini/gemini-3.1-pro-preview"),
    "gemini-3-flash-preview": ("gemini/gemini-3-flash-preview", "openai/gpt-4o-mini"),
    "gemini-3.1-pro-preview": ("gemini/gemini-3.1-pro-preview", "openai/gpt-4o"),
}


def resolve_model_chain(slug: str) -> tuple[str, str]:
    """Return ``(primary, fallback)`` LiteLLM model IDs for the given slug.

    Unknown slugs are passed through as-is with no fallback pairing.
    """
    if slug in _FALLBACK_MAP:
        return _FALLBACK_MAP[slug]
    logger.warning("unknown_llm_slug_no_fallback_map", slug=slug)
    return (slug, slug)


def get_llm_for_crew(slug: str) -> str:
    """Return the primary LiteLLM model string to pass to CrewAI agents.

    CrewAI forwards this string to ``litellm.completion(model=...)``.
    The global ``litellm.fallbacks`` list handles automatic failover.
    """
    primary, fallback = resolve_model_chain(slug)
    logger.info("llm_resolved", slug=slug, primary=primary, fallback=fallback)
    return primary


def _is_gemini_configured(settings) -> bool:
    return bool(settings.gemini_api_key)


def _build_global_fallbacks() -> list[dict]:
    """Build the litellm.fallbacks list from the full fallback map."""
    return [{primary: [fallback]} for primary, fallback in _FALLBACK_MAP.values()]


def _configure_gemini_env(settings) -> None:
    """Export GEMINI_API_KEY so LiteLLM's gemini/ provider picks it up."""
    if settings.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key


def configure_litellm(settings: Optional[object] = None) -> None:
    """Apply global LiteLLM settings. Call once at app startup."""
    if settings is None:
        settings = get_settings()

    litellm.drop_params = True
    litellm.request_timeout = settings.llm_request_timeout
    litellm.num_retries = 2

    _configure_gemini_env(settings)

    if settings.llm_fallback_enabled and _is_gemini_configured(settings):
        litellm.fallbacks = _build_global_fallbacks()
        logger.info(
            "litellm_fallback_enabled",
            chains=len(litellm.fallbacks),
            timeout=settings.llm_request_timeout,
        )
    else:
        litellm.fallbacks = []
        logger.info(
            "litellm_fallback_disabled",
            gemini_configured=_is_gemini_configured(settings),
            timeout=settings.llm_request_timeout,
        )
