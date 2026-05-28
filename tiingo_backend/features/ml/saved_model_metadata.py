def extract_saved_model_metadata(row: dict) -> dict[str, str | None]:
    metrics = row.get("train_metrics") or {}
    symbol = metrics.get("training_symbol")
    if not symbol and row.get("name"):
        symbol = row["name"].split()[0] if row["name"] else None
    return {
        "symbol": symbol,
        "timeframe": metrics.get("timeframe"),
    }
