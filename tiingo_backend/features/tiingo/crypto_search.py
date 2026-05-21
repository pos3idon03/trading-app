"""Local search over Tiingo crypto meta catalog."""
import re

from dtos.market_data_dto import TickerSearchResultDTO
from features.tiingo.common import normalize_crypto_symbol


def _query_tokens(query: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", query.lower())


def _compile_query_pattern(query: str) -> re.Pattern[str] | None:
    tokens = _query_tokens(query)
    if not tokens:
        return None
    body = "|".join(re.escape(token) for token in tokens)
    return re.compile(body, re.IGNORECASE)


def _display_name(item: dict) -> str:
    name = (item.get("name") or "").strip()
    if name:
        return name
    base = (item.get("baseCurrency") or "").upper()
    quote = (item.get("quoteCurrency") or "").upper()
    if base and quote:
        return f"{base}/{quote}"
    return (item.get("ticker") or "").upper()


def _matches(item: dict, pattern: re.Pattern[str] | None, tokens: list[str]) -> bool:
    if not tokens:
        return False
    haystack = " ".join(
        filter(
            None,
            [
                item.get("ticker"),
                item.get("name"),
                item.get("baseCurrency"),
                item.get("quoteCurrency"),
                item.get("description"),
            ],
        )
    )
    if pattern and pattern.search(haystack):
        return True
    ticker = (item.get("ticker") or "").lower()
    base = (item.get("baseCurrency") or "").lower()
    return any(token == base or ticker.startswith(token) for token in tokens)


def _rank(item: dict, tokens: list[str]) -> tuple[int, str]:
    ticker = (item.get("ticker") or "").lower()
    base = (item.get("baseCurrency") or "").lower()
    quote = (item.get("quoteCurrency") or "").lower()
    joined = "".join(tokens)
    exact_ticker = 0 if ticker == joined else 1
    base_usd = 0 if len(tokens) == 1 and base == tokens[0] and quote == "usd" else 1
    prefix = 0 if tokens and ticker.startswith(tokens[0]) else 1
    return (exact_ticker, base_usd, prefix, ticker)


def _to_result(item: dict) -> TickerSearchResultDTO:
    ticker = (item.get("ticker") or "").strip()
    return TickerSearchResultDTO(
        symbol=normalize_crypto_symbol(ticker),
        name=_display_name(item),
        asset_type="crypto",
        exchange=None,
        tiingo_ticker=ticker,
    )


def search_crypto_meta(
    query: str,
    meta: list[dict],
    limit: int = 5,
) -> list[TickerSearchResultDTO]:
    tokens = _query_tokens(query)
    if not tokens or limit <= 0:
        return []

    pattern = _compile_query_pattern(query)
    matched = [item for item in meta if _matches(item, pattern, tokens)]
    matched.sort(key=lambda item: _rank(item, tokens))
    results: list[TickerSearchResultDTO] = []
    for item in matched[:limit]:
        try:
            results.append(_to_result(item))
        except ValueError:
            continue
    return results
