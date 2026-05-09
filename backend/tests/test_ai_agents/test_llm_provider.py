"""Tests for the LLM provider fallback layer.

All external dependencies (litellm module, Settings) are mocked so tests run
without real API credentials or network access.
"""
from unittest.mock import MagicMock, patch

import litellm
import pytest

from features.ai_agents.llm_provider import (
    _FALLBACK_MAP,
    _build_global_fallbacks,
    _is_gemini_configured,
    configure_litellm,
    get_llm_for_crew,
    resolve_model_chain,
)


# ---------------------------------------------------------------------------
# resolve_model_chain
# ---------------------------------------------------------------------------


class TestResolveModelChain:
    def test_known_openai_slug_maps_to_openai_primary(self):
        primary, _ = resolve_model_chain("gpt-4o-mini")
        assert primary == "openai/gpt-4o-mini"

    def test_known_openai_slug_maps_to_gemini_fallback(self):
        _, fallback = resolve_model_chain("gpt-4o-mini")
        assert fallback == "gemini/gemini-3-flash-preview"

    def test_known_gemini_slug_maps_to_gemini_primary(self):
        primary, _ = resolve_model_chain("gemini-3-flash-preview")
        assert primary == "gemini/gemini-3-flash-preview"

    def test_known_gemini_slug_maps_to_openai_fallback(self):
        _, fallback = resolve_model_chain("gemini-3-flash-preview")
        assert fallback == "openai/gpt-4o-mini"

    def test_gpt4o_maps_to_gemini_pro_fallback(self):
        _, fallback = resolve_model_chain("gpt-4o")
        assert fallback == "gemini/gemini-3.1-pro-preview"

    def test_gemini_pro_maps_to_gpt4o_fallback(self):
        _, fallback = resolve_model_chain("gemini-3.1-pro-preview")
        assert fallback == "openai/gpt-4o"

    def test_unknown_slug_returns_slug_for_both(self):
        primary, fallback = resolve_model_chain("some-custom-model")
        assert primary == "some-custom-model"
        assert fallback == "some-custom-model"

    def test_all_configured_slugs_are_in_fallback_map(self):
        for slug in ("gpt-4o-mini", "gpt-4o", "gemini-3-flash-preview", "gemini-3.1-pro-preview"):
            assert slug in _FALLBACK_MAP

    def test_bidirectional_pairing_is_consistent(self):
        _, gpt_mini_fallback = resolve_model_chain("gpt-4o-mini")
        flash_primary, _ = resolve_model_chain("gemini-3-flash-preview")
        assert gpt_mini_fallback == flash_primary


# ---------------------------------------------------------------------------
# _is_gemini_configured
# ---------------------------------------------------------------------------


class TestIsGeminiConfigured:
    def _settings(self, api_key: str = "") -> MagicMock:
        s = MagicMock()
        s.gemini_api_key = api_key
        return s

    def test_returns_false_when_key_is_empty(self):
        assert _is_gemini_configured(self._settings("")) is False

    def test_returns_true_when_key_is_set(self):
        assert _is_gemini_configured(self._settings("AQ.somekey")) is True


# ---------------------------------------------------------------------------
# _build_global_fallbacks
# ---------------------------------------------------------------------------


class TestBuildGlobalFallbacks:
    def test_returns_one_entry_per_slug(self):
        fallbacks = _build_global_fallbacks()
        assert len(fallbacks) == len(_FALLBACK_MAP)

    def test_each_entry_is_dict_with_single_key_and_list_value(self):
        for entry in _build_global_fallbacks():
            assert len(entry) == 1
            key, val = next(iter(entry.items()))
            assert isinstance(key, str)
            assert isinstance(val, list)
            assert len(val) == 1

    def test_openai_primary_maps_to_gemini_fallback_list(self):
        fallbacks = _build_global_fallbacks()
        entry = next(e for e in fallbacks if "openai/gpt-4o-mini" in e)
        assert entry["openai/gpt-4o-mini"] == ["gemini/gemini-3-flash-preview"]

    def test_gemini_primary_maps_to_openai_fallback_list(self):
        fallbacks = _build_global_fallbacks()
        entry = next(e for e in fallbacks if "gemini/gemini-3-flash-preview" in e)
        assert entry["gemini/gemini-3-flash-preview"] == ["openai/gpt-4o-mini"]


# ---------------------------------------------------------------------------
# get_llm_for_crew
# ---------------------------------------------------------------------------


class TestGetLlmForCrew:
    def test_always_returns_string(self):
        assert isinstance(get_llm_for_crew("gpt-4o-mini"), str)

    def test_returns_primary_model_string_for_openai_slug(self):
        assert get_llm_for_crew("gpt-4o-mini") == "openai/gpt-4o-mini"

    def test_returns_primary_model_string_for_gemini_slug(self):
        assert get_llm_for_crew("gemini-3-flash-preview") == "gemini/gemini-3-flash-preview"

    def test_returns_primary_model_string_for_gpt4o(self):
        assert get_llm_for_crew("gpt-4o") == "openai/gpt-4o"

    def test_returns_primary_model_string_for_gemini_pro(self):
        assert get_llm_for_crew("gemini-3.1-pro-preview") == "gemini/gemini-3.1-pro-preview"

    def test_unknown_slug_passes_through_as_primary(self):
        assert get_llm_for_crew("some-other-model") == "some-other-model"


# ---------------------------------------------------------------------------
# configure_litellm
# ---------------------------------------------------------------------------


class TestConfigureLitellm:
    def _settings(self, gemini_api_key="", fallback_enabled=True, timeout=120) -> MagicMock:
        s = MagicMock()
        s.llm_request_timeout = timeout
        s.llm_fallback_enabled = fallback_enabled
        s.gemini_api_key = gemini_api_key
        return s

    def test_sets_drop_params_true(self):
        configure_litellm(self._settings())
        assert litellm.drop_params is True

    def test_sets_request_timeout(self):
        configure_litellm(self._settings(timeout=90))
        assert litellm.request_timeout == 90

    def test_sets_num_retries(self):
        configure_litellm(self._settings())
        assert litellm.num_retries == 2

    def test_fallbacks_empty_when_gemini_key_missing(self):
        configure_litellm(self._settings(gemini_api_key=""))
        assert litellm.fallbacks == []

    def test_fallbacks_empty_when_fallback_disabled(self):
        configure_litellm(self._settings(gemini_api_key="AQ.key", fallback_enabled=False))
        assert litellm.fallbacks == []

    def test_fallbacks_populated_when_key_present_and_enabled(self):
        configure_litellm(self._settings(gemini_api_key="AQ.key"))
        assert isinstance(litellm.fallbacks, list)
        assert len(litellm.fallbacks) == len(_FALLBACK_MAP)

    def test_fallbacks_contain_openai_to_gemini_chain(self):
        configure_litellm(self._settings(gemini_api_key="AQ.key"))
        entry = next((e for e in litellm.fallbacks if "openai/gpt-4o-mini" in e), None)
        assert entry is not None
        assert entry["openai/gpt-4o-mini"] == ["gemini/gemini-3-flash-preview"]

    def test_gemini_api_key_exported_to_env(self):
        import os
        configure_litellm(self._settings(gemini_api_key="AQ.testkey"))
        assert os.environ.get("GEMINI_API_KEY") == "AQ.testkey"
