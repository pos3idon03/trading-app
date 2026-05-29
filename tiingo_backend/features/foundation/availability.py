from config import get_settings


def foundation_models_enabled() -> bool:
    return get_settings().foundation_models_enabled


def _missing_foundation_dependency() -> str | None:
    try:
        import torch  # noqa: F401
    except ImportError:
        return "torch"
    try:
        import timesfm  # noqa: F401
    except ImportError:
        return "timesfm"
    try:
        import chronos  # noqa: F401
    except ImportError:
        return "chronos-forecasting"
    return None


def foundation_models_available() -> bool:
    if not foundation_models_enabled():
        return False
    return _missing_foundation_dependency() is None


def require_foundation_models() -> None:
    if not foundation_models_enabled():
        raise RuntimeError(
            "Foundation models are disabled. Set FOUNDATION_MODELS_ENABLED=true to enable."
        )
    missing = _missing_foundation_dependency()
    if missing is not None:
        raise RuntimeError(
            "Foundation model dependencies are not installed. "
            f"Missing package: {missing}. "
            "Install tiingo_backend/requirements-foundation.txt "
            "(TimesFM must be installed from GitHub; see FOUNDATION_MANUAL.md)."
        )
