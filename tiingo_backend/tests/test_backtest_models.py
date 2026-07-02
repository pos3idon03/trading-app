from models.backtest import BacktestRun
from db import Base


def test_backtest_run_registers_universe_foreign_key_target():
    assert "universe_definitions" in Base.metadata.tables
    assert "backtest_runs" in Base.metadata.tables

    universe_fks = [
        fk
        for fk in BacktestRun.__table__.foreign_keys
        if fk.column.table.name == "universe_definitions"
    ]
    assert len(universe_fks) == 1
