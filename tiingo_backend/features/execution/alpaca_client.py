from typing import Any

import httpx

from config import get_settings

_ACCOUNT_PATH = "/v2/account"
_POSITIONS_PATH = "/v2/positions"
_ORDERS_PATH = "/v2/orders"


def _headers() -> dict[str, str]:
    settings = get_settings()
    if not settings.alpaca_configured:
        raise RuntimeError("Alpaca API credentials are not configured")
    return {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
    }


def _base_url() -> str:
    return get_settings().effective_alpaca_base_url


async def _request(method: str, path: str, *, json: dict | None = None) -> Any:
    url = f"{_base_url()}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, headers=_headers(), json=json)
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()


async def get_account() -> dict:
    data = await _request("GET", _ACCOUNT_PATH)
    return {
        "equity": float(data.get("equity") or 0),
        "cash": float(data.get("cash") or 0),
        "buying_power": float(data.get("buying_power") or 0),
        "portfolio_value": float(data.get("portfolio_value") or 0),
        "status": data.get("status"),
        "currency": data.get("currency"),
    }


async def get_positions() -> list[dict]:
    data = await _request("GET", _POSITIONS_PATH)
    if not isinstance(data, list):
        return []
    return [
        {
            "symbol": row.get("symbol"),
            "qty": float(row.get("qty") or 0),
            "side": row.get("side"),
            "market_value": float(row.get("market_value") or 0),
            "avg_entry_price": float(row.get("avg_entry_price") or 0),
            "unrealized_pl": float(row.get("unrealized_pl") or 0),
            "current_price": float(row.get("current_price") or 0),
        }
        for row in data
    ]


async def get_open_orders() -> list[dict]:
    data = await _request("GET", f"{_ORDERS_PATH}?status=open")
    if not isinstance(data, list):
        return []
    return [
        {
            "id": row.get("id"),
            "symbol": row.get("symbol"),
            "side": row.get("side"),
            "qty": float(row.get("qty") or 0),
            "status": row.get("status"),
            "submitted_at": row.get("submitted_at"),
        }
        for row in data
    ]


async def get_order(order_id: str) -> dict:
    data = await _request("GET", f"{_ORDERS_PATH}/{order_id}")
    return {
        "id": data.get("id"),
        "symbol": data.get("symbol"),
        "side": data.get("side"),
        "qty": float(data.get("qty") or 0),
        "status": data.get("status"),
        "filled_avg_price": float(data.get("filled_avg_price") or 0) or None,
        "filled_at": data.get("filled_at"),
        "submitted_at": data.get("submitted_at"),
    }


async def submit_market_order(symbol: str, qty: float, side: str) -> dict:
    payload = {
        "symbol": symbol.upper(),
        "qty": str(round(qty, 6)),
        "side": side.lower(),
        "type": "market",
        "time_in_force": "day",
    }
    data = await _request("POST", _ORDERS_PATH, json=payload)
    return {
        "id": data.get("id"),
        "symbol": data.get("symbol"),
        "side": data.get("side"),
        "qty": float(data.get("qty") or 0),
        "status": data.get("status"),
        "submitted_at": data.get("submitted_at"),
    }
