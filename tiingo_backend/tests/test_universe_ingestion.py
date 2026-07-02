from features.ingestion.universe_orchestrator import _fallback_sp500


def test_fallback_sp500_non_empty():
    assert len(_fallback_sp500()) >= 10
