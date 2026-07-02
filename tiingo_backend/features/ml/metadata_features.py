"""Static instrument metadata features (sector/industry)."""

from typing import Optional

_SECTOR_VOCAB: list[str] = []
_INDUSTRY_VOCAB: list[str] = []


def _encode_categorical(value: str | None, vocab: list[str]) -> list[float]:
    if value and value not in vocab:
        vocab.append(value)
    if not vocab:
        return []
    vec = [0.0] * len(vocab)
    if value and value in vocab:
        vec[vocab.index(value)] = 1.0
    return vec


def metadata_from_instrument(instrument: dict) -> tuple[str | None, str | None]:
    meta = instrument.get("metadata") or {}
    sector = meta.get("sector")
    industry = meta.get("industry")
    return sector, industry


def build_metadata_feature_vector(
    instrument: dict,
) -> tuple[list[str], list[float]]:
    global _SECTOR_VOCAB, _INDUSTRY_VOCAB
    sector, industry = metadata_from_instrument(instrument)
    sector_vec = _encode_categorical(sector, _SECTOR_VOCAB)
    industry_vec = _encode_categorical(industry, _INDUSTRY_VOCAB)
    names = [f"sector_{s}" for s in _SECTOR_VOCAB] + [
        f"industry_{i}" for i in _INDUSTRY_VOCAB
    ]
    return names, sector_vec + industry_vec


def build_metadata_rows_for_bars(
    instrument: dict,
    bar_count: int,
) -> tuple[list[str], list[Optional[list[float]]]]:
    names, vec = build_metadata_feature_vector(instrument)
    if not names:
        return [], []
    row = [float(v) for v in vec]
    return names, [row for _ in range(bar_count)]
