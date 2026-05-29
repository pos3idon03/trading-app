import builtins

import pytest

from features.foundation import availability


def test_missing_dependency_reports_package_name(monkeypatch):
    monkeypatch.setenv("FOUNDATION_MODELS_ENABLED", "true")
    from config import get_settings

    get_settings.cache_clear()

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "timesfm":
            raise ImportError("No module named 'timesfm'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert availability._missing_foundation_dependency() == "timesfm"
    get_settings.cache_clear()


def test_foundation_models_available_when_all_deps_present(monkeypatch):
    monkeypatch.setenv("FOUNDATION_MODELS_ENABLED", "true")
    from config import get_settings

    get_settings.cache_clear()
    try:
        import torch  # noqa: F401
        import timesfm  # noqa: F401
        import chronos  # noqa: F401
    except ImportError:
        pytest.skip("Foundation dependencies not installed in test environment")
    assert availability.foundation_models_available() is True
    get_settings.cache_clear()
