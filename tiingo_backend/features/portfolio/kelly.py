"""Fractional Kelly position sizing."""


def kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
) -> float:
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    b = avg_win / avg_loss
    return win_rate - (1.0 - win_rate) / b


def capped_kelly_budget(
    equity: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    *,
    kelly_cap: float = 0.25,
    max_position_pct: float = 100.0,
) -> float:
    raw = kelly_fraction(win_rate, avg_win, avg_loss)
    if raw <= 0:
        return 0.0
    fraction = min(raw * kelly_cap, max_position_pct / 100.0)
    return equity * fraction


def kelly_from_trade_pnls(pnls: list[float]) -> tuple[float, float, float]:
    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p < 0]
    if not wins or not losses:
        return 0.0, 0.0, 0.0
    win_rate = len(wins) / len(pnls)
    return win_rate, sum(wins) / len(wins), sum(losses) / len(losses)
