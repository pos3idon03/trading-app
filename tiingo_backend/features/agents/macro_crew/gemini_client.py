import asyncio

from config import get_settings


def _generate_sync(prompt: str, model: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "Macro brief requires google-genai. Install with: pip install -r requirements-llm.txt"
        ) from exc

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    text = response.text or ""
    if not text.strip():
        raise RuntimeError("Gemini returned an empty response")
    return text.strip()


async def generate_text(prompt: str, *, model: str | None = None) -> str:
    settings = get_settings()
    resolved_model = model or settings.macro_brief_model
    timeout = settings.macro_brief_timeout_seconds
    return await asyncio.wait_for(
        asyncio.to_thread(_generate_sync, prompt, resolved_model),
        timeout=timeout,
    )
