"""Classify and surface actionable messages for LLM provider errors.

LiteLLM raises its own exception hierarchy. This module inspects the
exception type and message to produce a user-facing string that explains
what went wrong and how to resolve it, without leaking raw stack traces.
"""
from utils.logging import get_logger

logger = get_logger(__name__)

_GEMINI_BLOCKED_HINTS = (
    "API_KEY_SERVICE_BLOCKED",
    "generativelanguage.googleapis.com",
    "PERMISSION_DENIED",
)

_OPENAI_AUTH_HINTS = (
    "Incorrect API key",
    "invalid_api_key",
    "No API key provided",
)


def _is_gemini_permission_error(msg: str) -> bool:
    return any(hint in msg for hint in _GEMINI_BLOCKED_HINTS)


def _is_openai_auth_error(msg: str) -> bool:
    return any(hint in msg for hint in _OPENAI_AUTH_HINTS)


def classify_llm_error(exc: Exception) -> str:
    """Return a concise, actionable error message for a LiteLLM exception.

    Falls back to ``str(exc)`` for unrecognised errors so nothing is swallowed.
    """
    msg = str(exc)
    exc_type = type(exc).__name__

    if _is_gemini_permission_error(msg):
        logger.warning("gemini_api_key_blocked", exc_type=exc_type)
        return (
            "Gemini API key is blocked for the Generative Language API. "
            "To fix: go to Google Cloud Console → APIs & Services → Credentials, "
            "edit the key, and either remove API restrictions or add "
            "'Generative Language API' to the allowed list. "
            "Also ensure the API is enabled in your GCP project."
        )

    if _is_openai_auth_error(msg):
        logger.warning("openai_api_key_invalid", exc_type=exc_type)
        return (
            "OpenAI API key is invalid or missing. "
            "Set a valid key in OPENAI_API_KEY and restart the backend."
        )

    logger.error("unclassified_llm_error", exc_type=exc_type, detail=msg[:200])
    return msg
