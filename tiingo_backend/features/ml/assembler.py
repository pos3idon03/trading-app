from typing import Optional


def _row_set_is_active(rows: list[Optional[list[float]]]) -> bool:
    """Skip empty blocks and placeholder all-None rows from omitted optional features."""
    return bool(rows) and any(row is not None for row in rows)


def _merge_rows(*row_sets: list[Optional[list[float]]]) -> list[Optional[list[float]]]:
    active_sets = [rows for rows in row_sets if _row_set_is_active(rows)]
    if not active_sets:
        return []

    row_count = len(active_sets[0])
    merged: list[Optional[list[float]]] = []
    for row_index in range(row_count):
        combined: list[float] = []
        row_complete = True
        for row_set in active_sets:
            row = row_set[row_index]
            if row is None:
                row_complete = False
                break
            combined.extend(row)
        merged.append(combined if row_complete else None)
    return merged


def assemble_feature_matrix(
    feature_mode: str,
    price_names: list[str],
    price_rows: list[Optional[list[float]]],
    macro_names: list[str] | None = None,
    macro_rows: list[Optional[list[float]]] | None = None,
    fundamental_names: list[str] | None = None,
    fundamental_rows: list[Optional[list[float]]] | None = None,
    news_names: list[str] | None = None,
    news_rows: list[Optional[list[float]]] | None = None,
    context_names: list[str] | None = None,
    context_rows: list[Optional[list[float]]] | None = None,
    strategy_names: list[str] | None = None,
    strategy_rows: list[Optional[list[float]]] | None = None,
) -> tuple[list[str], list[Optional[list[float]]]]:
    macro_names = macro_names or []
    macro_rows = macro_rows or []
    fundamental_names = fundamental_names or []
    fundamental_rows = fundamental_rows or []
    news_names = news_names or []
    news_rows = news_rows or []
    context_names = context_names or []
    context_rows = context_rows or []
    strategy_names = strategy_names or []
    strategy_rows = strategy_rows or []

    base_names: list[str] = []
    base_row_sets: list[list[Optional[list[float]]]] = []

    if feature_mode == "prices_only":
        base_names = list(price_names)
        base_row_sets = [price_rows]
    elif feature_mode == "prices_macro":
        base_names = [*price_names, *macro_names]
        base_row_sets = [price_rows, macro_rows]
    elif feature_mode == "prices_macro_fundamentals":
        base_names = [*price_names, *macro_names, *fundamental_names]
        base_row_sets = [price_rows, macro_rows, fundamental_rows]
    else:
        raise ValueError(f"Unsupported feature_mode: {feature_mode}")

    merged_names = [*base_names, *news_names, *context_names, *strategy_names]
    merged_rows = _merge_rows(*base_row_sets, news_rows, context_rows, strategy_rows)
    return merged_names, merged_rows
