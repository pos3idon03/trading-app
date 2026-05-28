from config import get_settings


def foundation_models_enabled() -> bool:
    return get_settings().foundation_models_enabled


def foundation_models_available() -> bool:
    if not foundation_models_enabled():
        return False
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def require_foundation_models() -> None:
    if not foundation_models_enabled():
        raise RuntimeError(
            "Foundation models are disabled. Set FOUNDATION_MODELS_ENABLED=true to enable."
        )
    if not foundation_models_available():
        raise RuntimeError(
            "Foundation model dependencies are not installed. "
            "Install requirements-foundation.txt (torch, timesfm, chronos-forecasting)."
        )
