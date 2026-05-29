import hashlib
import re


def build_article_text(title: str, description: str | None) -> str:
    title = (title or "").strip()
    description = (description or "").strip()
    if title and description:
        return f"{title}. {description}"
    return title or description


def normalize_text(text: str, max_chars: int) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[:max_chars].rstrip()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def title_fingerprint(title: str) -> str:
    return hash_text(normalize_title(title))
