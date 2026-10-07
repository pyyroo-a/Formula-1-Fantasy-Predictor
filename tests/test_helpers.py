"""
Small checks for the shared helpers. The backtest and measure_grid_error use these
too but aren't covered by the endpoint tests, so the helpers get their own.
"""
import pandas as pd

import src.fetch_practice as fp
import src.fetch_prices as fetch_prices_mod
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


# ---- price feed parsing ---------------------------------------------------------
#
# The feed keeps a driver's OLD team pairing around after a mid-season move, marked
# IsActive 0, and the stale one can come last. Lawson was on 15.1 at Red Bull and
# 9.3 back at Racing Bulls, and rounds 15-17 all stored 15.1 because the loop just
# overwrote on repeated TLAs. See src/fetch_prices.py.

def _feed_row(tla, value, active, team="Racing Bulls", kind="DRIVER"):
    return {
        "PositionName": kind,
        "DriverTLA": tla,
        "FUllName": team if kind == "CONSTRUCTOR" else f"{tla} driver",
        "TeamName": team,
        "Value": value,
        "IsActive": active,
    }


def test_price_feed_prefers_the_active_entry():
    # real round 17 ordering: the active Racing Bulls row first, stale Red Bull last
    items = [
        _feed_row("LAW", 9.3, "1", "Racing Bulls"),
        _feed_row("HAD", 15.7, "1", "Red Bull Racing"),
        _feed_row("LAW", 15.1, "0", "Red Bull Racing"),
    ]
    prices = fetch_prices_mod.parse_price_feed(items)
    assert prices["drivers"]["LAW"] == 9.3
    assert prices["drivers"]["HAD"] == 15.7


def test_price_feed_prefers_active_whatever_the_order():
    # same two rows the other way round, so we aren't just taking the first one
    items = [
        _feed_row("LAW", 15.1, "0", "Red Bull Racing"),
        _feed_row("LAW", 9.3, "1", "Racing Bulls"),
    ]
    assert fetch_prices_mod.parse_price_feed(items)["drivers"]["LAW"] == 9.3


def test_price_feed_keeps_a_driver_with_no_active_row():
    # IsActive describes the CURRENT roster, so in an old round's feed a driver who
    # has since moved has no active row at all. Hadjar is like this in round 12.
    # Dropping him would put holes in the history, so the inactive row still counts.
    items = [_feed_row("HAD", 14.5, "0", "Racing Bulls")]
    assert fetch_prices_mod.parse_price_feed(items)["drivers"]["HAD"] == 14.5


def test_price_feed_reads_constructors():
    items = [
        _feed_row("", 15.9, "1", "Racing Bulls", kind="CONSTRUCTOR"),
        _feed_row("LAW", 9.3, "1", "Racing Bulls"),
    ]
    prices = fetch_prices_mod.parse_price_feed(items)
    assert prices["constructors"]["Racing Bulls"] == 15.9
    assert "Racing Bulls" not in prices["drivers"]
