import re
from typing import Iterable

import httpx

_SECRET_QUERY_PATTERN = re.compile(
    r"(api_key|apikey|token|secret|password)=[^&\s\"']+",
    re.IGNORECASE,
)


def redact_secrets(text: str, secret_values: Iterable[str] | None = None) -> str:
    if not text:
        return text
    redacted = _SECRET_QUERY_PATTERN.sub(r"\1=[REDACTED]", text)
    if not secret_values:
        return redacted
    for secret in secret_values:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def format_external_api_error(
    exc: BaseException,
    *,
    context: str | None = None,
    secret_values: Iterable[str] | None = None,
) -> str:
    prefix = f"{context}: " if context else ""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code if exc.response is not None else "unknown"
        resource = _resource_from_request(exc.request)
        return f"{prefix}External API error (HTTP {status}) for {resource}".strip()

    message = redact_secrets(str(exc), secret_values)
    if prefix:
        return f"{prefix}{message}"
    return message


def _resource_from_request(request: httpx.Request | None) -> str:
    if request is None:
        return "request"
    path = request.url.path.strip("/")
    if path:
        return path.split("/")[-1] or "request"
    return "request"
