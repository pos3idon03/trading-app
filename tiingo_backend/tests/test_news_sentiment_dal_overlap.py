from sqlalchemy.dialects import postgresql

from dal.news_sentiment_dal import _normalize_watchlist_tickers, _watchlist_tickers_overlap


def test_normalize_watchlist_tickers_lowercase():
    assert _normalize_watchlist_tickers(["GOOG", " NVDA "]) == ["goog", "nvda"]


def test_watchlist_tickers_overlap_uses_any_operator():
    condition = _watchlist_tickers_overlap(["goog", "nvda"])
    compiled = str(
        condition.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "= ANY (news_articles.tickers)" in compiled
    assert "&&" not in compiled
