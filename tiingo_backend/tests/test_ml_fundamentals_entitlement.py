import inspect

from features.ml import orchestrator as ml_orchestrator


def test_ml_orchestrator_has_no_fundamentals_entitlement_gate():
    assert not hasattr(ml_orchestrator, "_validate_fundamentals_entitlement")
    source = inspect.getsource(ml_orchestrator)
    assert "not entitled for fundamentals" not in source
