"""Seed OpenBB user_settings.json from environment variables.

Credentials are sourced exclusively from process environment (populated by
docker compose `env_file: .env`). Never commit secrets to this file.

Runs at container start via entrypoint.sh, merging into any pre-existing
settings file on the persistent volume so manually-added keys are preserved.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

ENV_TO_OPENBB: Dict[str, str] = {
    "FMP_API_KEY": "fmp_api_key",
    "FRED_API_KEY": "fred_api_key",
    "POLYGON_API_KEY": "polygon_api_key",
    "ALPACA_API_KEY": "alpaca_api_key",
    "OPENAI_API_KEY": "openai_api_key",
    "GEMINI_API_KEY": "gemini_api_key",
    "NEWSAPI_KEY": "newsapi_key",
    "BENZINGA_API_KEY": "benzinga_api_key",
    "BLS_API_KEY": "bls_api_key",
    "EIA_API_KEY": "eia_api_key",
    "INTRINIO_API_KEY": "intrinio_api_key",
    "TIINGO_TOKEN": "tiingo_token",
    "TRADINGECONOMICS_API_KEY": "tradingeconomics_api_key",
    "CFTC_APP_TOKEN": "cftc_app_token",
    "CONGRESS_GOV_API_KEY": "congress_gov_api_key",
    "ECONDB_API_KEY": "econdb_api_key",
}

DEFAULT_SETTINGS_PATH = Path("/root/.openbb_platform/user_settings.json")


def collect_credentials(env: Dict[str, str]) -> Dict[str, str]:
    """Return OpenBB credentials present (non-empty) in the given env."""
    return {
        openbb_key: env[env_var]
        for env_var, openbb_key in ENV_TO_OPENBB.items()
        if env.get(env_var)
    }


def load_existing_settings(path: Path) -> dict:
    """Read existing user_settings.json or return an empty dict on error."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def merge_credentials(settings: dict, new_creds: Dict[str, str]) -> dict:
    """Merge new credentials into the credentials sub-dict, preserving extras."""
    existing = dict(settings.get("credentials") or {})
    existing.update(new_creds)
    settings["credentials"] = existing
    return settings


def write_settings(path: Path, settings: dict) -> None:
    """Atomically write settings to disk, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    tmp.replace(path)


def seed(env: Dict[str, str], path: Path = DEFAULT_SETTINGS_PATH) -> Dict[str, str]:
    """Seed credentials from env into user_settings.json. Returns mapping written."""
    creds = collect_credentials(env)
    if not creds:
        return {}
    settings = load_existing_settings(path)
    merged = merge_credentials(settings, creds)
    write_settings(path, merged)
    return creds


def main() -> None:
    written = seed(dict(os.environ))
    if written:
        names = ", ".join(sorted(written))
        print(f"[openbb] Seeded {len(written)} credential(s): {names}")
    else:
        print("[openbb] No OpenBB-mappable credentials in env; starting without keys.")


if __name__ == "__main__":
    main()
