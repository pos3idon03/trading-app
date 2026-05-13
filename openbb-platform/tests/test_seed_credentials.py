"""Tests for the OpenBB credential seeding script."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import seed_credentials as sc


def test_collect_credentials_maps_known_env_vars():
    env = {"FMP_API_KEY": "fmp123", "FRED_API_KEY": "fred456", "UNRELATED": "x"}
    result = sc.collect_credentials(env)
    assert result == {"fmp_api_key": "fmp123", "fred_api_key": "fred456"}


def test_collect_credentials_ignores_blank_values():
    env = {"FMP_API_KEY": "", "FRED_API_KEY": "ok"}
    assert sc.collect_credentials(env) == {"fred_api_key": "ok"}


def test_collect_credentials_returns_empty_when_nothing_matches():
    assert sc.collect_credentials({"FOO": "bar"}) == {}


def test_load_existing_settings_returns_empty_when_missing(tmp_path: Path):
    assert sc.load_existing_settings(tmp_path / "missing.json") == {}


def test_load_existing_settings_returns_empty_on_bad_json(tmp_path: Path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    assert sc.load_existing_settings(path) == {}


def test_load_existing_settings_parses_valid_json(tmp_path: Path):
    path = tmp_path / "ok.json"
    path.write_text(json.dumps({"credentials": {"a": "1"}}), encoding="utf-8")
    assert sc.load_existing_settings(path) == {"credentials": {"a": "1"}}


def test_merge_credentials_preserves_other_top_level_keys():
    settings = {"preferences": {"theme": "dark"}, "credentials": {"old": "v"}}
    merged = sc.merge_credentials(settings, {"new": "n"})
    assert merged["preferences"] == {"theme": "dark"}
    assert merged["credentials"] == {"old": "v", "new": "n"}


def test_merge_credentials_overwrites_same_key():
    settings = {"credentials": {"fmp_api_key": "old"}}
    merged = sc.merge_credentials(settings, {"fmp_api_key": "new"})
    assert merged["credentials"]["fmp_api_key"] == "new"


def test_write_settings_creates_parent_directory(tmp_path: Path):
    target = tmp_path / "nested" / "user_settings.json"
    sc.write_settings(target, {"credentials": {"x": "y"}})
    assert json.loads(target.read_text(encoding="utf-8")) == {"credentials": {"x": "y"}}


def test_seed_writes_merged_file_end_to_end(tmp_path: Path):
    path = tmp_path / "user_settings.json"
    path.write_text(json.dumps({"preferences": {"theme": "dark"}}), encoding="utf-8")
    written = sc.seed({"FMP_API_KEY": "abc", "OPENAI_API_KEY": "key"}, path=path)
    result = json.loads(path.read_text(encoding="utf-8"))
    assert written == {"fmp_api_key": "abc", "openai_api_key": "key"}
    assert result["preferences"] == {"theme": "dark"}
    assert result["credentials"] == {"fmp_api_key": "abc", "openai_api_key": "key"}


def test_seed_is_noop_when_no_env_vars_present(tmp_path: Path):
    path = tmp_path / "user_settings.json"
    written = sc.seed({"FOO": "bar"}, path=path)
    assert written == {}
    assert not path.exists()


def test_env_mapping_only_uses_supported_openbb_fields():
    supported = {
        "alpaca_api_key", "benzinga_api_key", "bls_api_key", "cftc_app_token",
        "congress_gov_api_key", "econdb_api_key", "eia_api_key", "fmp_api_key",
        "fred_api_key", "gemini_api_key", "intrinio_api_key", "newsapi_key",
        "openai_api_key", "polygon_api_key", "tiingo_token",
        "tradingeconomics_api_key",
    }
    extras = set(sc.ENV_TO_OPENBB.values()) - supported
    assert not extras, f"Mapping points at unknown OpenBB fields: {extras}"
