import asyncio
from typing import Any, Optional

import httpx

from utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.5


async def fetch_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    retries: int = DEFAULT_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    attempt = 0
    last_exc: Exception = RuntimeError("No attempts made")

    async with httpx.AsyncClient(timeout=timeout) as client:
        while attempt < retries:
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                wait = DEFAULT_BACKOFF ** attempt
                logger.warning(
                    "api_request_failed",
                    url=url,
                    attempt=attempt + 1,
                    retries=retries,
                    wait_s=wait,
                    error=str(exc),
                )
                await asyncio.sleep(wait)
                attempt += 1

    raise last_exc


def fetch_json_sync(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    retries: int = DEFAULT_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=DEFAULT_BACKOFF, status_forcelist=[429, 500, 502, 503])
    session.mount("https://", HTTPAdapter(max_retries=retry))

    response = session.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()
