"""
Small checks for the shared helpers. The backtest and measure_grid_error use these
too but aren't covered by the endpoint tests, so the helpers get their own.
"""
import pandas as pd

import src.fetch_practice as fp
from src.config import PREVIOUS_SEASON, SEASON, results_path


def test_fallback_sessions_order():
    # same orders the old copied loops used
    assert fp.fallback_sessions("FP3") == ["FP3", "FP2", "FP1"]
    assert fp.fallback_sessions("FP2") == ["FP2", "FP1"]
    assert fp.fallback_sessions("FP1") == ["FP1"]
    # anything else is just tried on its own, like the old upcoming-race-pool did
    assert fp.fallback_sessions("") == [""]


def test_first_available_takes_first_that_loads(monkeypatch):
    tried = []

    def fake_grid(year, race, sess):
        tried.append(sess)
        if sess == "FP3":
            raise ValueError("FP3 not out yet")
        return pd.DataFrame({"session": [sess]})

    monkeypatch.setattr(fp, "get_practice_grid", fake_grid)
    df, used, err = fp.first_available_practice(2026, "Test GP", ["FP3", "FP2", "FP1"])
    assert used == "FP2" and df["session"].iloc[0] == "FP2" and err is None
    assert tried == ["FP3", "FP2"]  # stops as soon as one loads


def test_first_available_when_nothing_loads(monkeypatch):
    def fake_grid(year, race, sess):
        raise ValueError(f"{sess} missing")

    monkeypatch.setattr(fp, "get_practice_grid", fake_grid)
    df, used, err = fp.first_available_practice(2026, "Test GP", ["FP3", "FP2", "FP1"])
    assert df is None and used is None
    assert err == "FP1 missing"  # the last error, like the old loops kept


def test_config():
    assert PREVIOUS_SEASON == SEASON - 1
    assert results_path() == f"data/processed/race_results_{SEASON}.csv"
    assert results_path(2025) == "data/processed/race_results_2025.csv"
