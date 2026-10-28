"""
Checks for the confidence grade (scripts/confidence_grade.py) on tiny made up rounds,
so the places off can be worked out by hand. The real run needs the network.
"""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def grade():
    spec = importlib.util.spec_from_file_location("confidence_grade_under_test",
                                                  ROOT / "scripts" / "confidence_grade.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rows(rounds):
    """rounds: {round: [(rank, level, grid, finish, status, fpts), ...]}"""
    return pd.DataFrame([{"round": r, "kind": "normal", "rank": rank, "level": lvl, "grid": g,
                          "finish": f, "status": st, "fpts": p}
                         for r, rows in rounds.items() for rank, lvl, g, f, st, p in rows])


def test_places_off_reranks_within_each_round(grade):
    rows = _rows({
        # fantasy points 10, 30, 20 rank them 3rd, 1st, 2nd
        1: [(1, "high", 1, 1, "Finished", 10), (2, "low", 2, 2, "Finished", 30),
            (3, "low", 3, 3, "Finished", 20)],
        # no points for the 2nd driver, so the other two get re-ranked 1st and 2nd
        2: [(1, "high", 1, 1, "Finished", 30), (2, "low", 2, 2, "Finished", None),
            (3, "low", 3, 3, "Finished", 20)],
    })
    off = grade.places_off(rows, "fpts", ascending=False)
    assert off.tolist()[:3] == [2, 1, 1]
    assert off.iloc[3] == 0 and pd.isna(off.iloc[4]) and off.iloc[5] == 0


def test_places_off_can_skip_non_finishers(grade):
    rows = _rows({1: [(1, "high", 1, 3, "Retired", 0), (2, "low", 2, 1, "Finished", 0),
                      (3, "low", 3, 2, "+1 Lap", 0)]})
    off = grade.places_off(rows, "finish", ascending=True, finishers_only=True)
    assert pd.isna(off.iloc[0])
    assert off.iloc[1:].tolist() == [0, 0]


def test_summarise_counts_rounds_where_high_beat_low(grade):
    rows = _rows({
        1: [(1, "high", 1, 1, "Finished", 30), (2, "low", 2, 2, "Finished", 10),
            (3, "low", 3, 3, "Finished", 20)],
        2: [(1, "high", 1, 1, "Finished", 10), (2, "medium", 2, 2, "Finished", 20),
            (3, "low", 3, 3, "Finished", 30)],
    })
    s = grade.summarise(rows)
    # round 1: high 0 off, low 1 and 1. round 2: high 2 off, low 2 off, a tie
    assert s["high"]["n"] == 2 and s["low"]["n"] == 3 and s["medium"]["n"] == 1
    assert s["high"]["fpts_off"] == pytest.approx(1.0)
    assert s["high"]["within2"] == pytest.approx(1.0)
    assert s["high_beat_low"] == 1 and s["rounds"] == 2
