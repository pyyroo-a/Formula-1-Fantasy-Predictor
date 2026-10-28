"""
Checks for the track record (src/track_record.py) on a tiny made up field, the same
one the scorecard tests use, so the brute force is instant and the answers are known.
"""
import importlib.util
from pathlib import Path

import pandas as pd

import src.track_record as tr

ROOT = Path(__file__).resolve().parent.parent

PRICES = {
    "drivers": {"A": 30.0, "B": 25.0, "C": 10.0, "D": 8.0, "E": 6.0, "F": 5.0},
    "constructors": {"X": 20.0, "Y": 12.0, "Z": 6.0},
}
GRID = pd.DataFrame({
    "Abbreviation": ["C", "A", "E", "B", "D", "F"],
    "TeamName": ["Y", "X", "Z", "X", "Y", "Z"],
    "GridPosition": [1, 2, 3, 4, 5, 6],
})
POINTS = {
    "drivers": {a: {"points": p} for a, p in
                {"A": 30.0, "B": 12.0, "C": 25.0, "D": -3.0, "E": 8.0, "F": 2.0}.items()},
    "constructors": {"X": {"points": 40.0}, "Y": {"points": 35.0}, "Z": {"points": 5.0}},
    "prices": PRICES,
}
LOCKED = {"teams": [{
    "drivers": [{"Abbreviation": a} for a in ["A", "C", "D", "E", "F"]],
    "constructors": [{"name": "X"}, {"name": "Z"}],
    "boost_pick": {"Abbreviation": "A"},
}]}
ENTRY = list(PRICES["drivers"])


def _build(official, snaps, grid=GRID):
    return tr.build_rows(official, [(18, "Test GP", ENTRY)],
                         lambda race: (grid, "FP3" if grid is not None else None),
                         lambda race: snaps.get(race))


def test_rows_use_the_same_numbers_as_the_scorecard():
    spec = importlib.util.spec_from_file_location("sc", ROOT / "scripts" / "scorecard.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    row = _build({18: POINTS}, {"Test GP": LOCKED})[0]
    card = sc.grade_round(18, "Test GP", POINTS, PRICES, GRID, LOCKED, None, entry=ENTRY)
    for col in tr.SIMPLE_COLUMNS:
        assert row["cells"][col] == card["cells"][col], col
    assert row["cells"]["Locked"] == 137.0   # A x2 60 + C 25 - D 3 + E 8 + F 2 + X 40 + Z 5


def test_round_without_a_grid_still_grades_the_rest():
    row = _build({18: POINTS}, {"Test GP": LOCKED}, grid=None)[0]
    assert row["cells"]["FP3 order"] is None and row["why"]["FP3 order"]
    assert row["cells"]["Locked"] == 137.0
    assert row["cells"]["Most expensive"] is not None and row["cells"]["Hindsight best"] is not None


def test_unraced_locked_round_is_left_out():
    assert _build({}, {"Test GP": LOCKED}) == []


def test_unlocked_round_is_left_out():
    assert _build({18: POINTS}, {}) == []


def _row(rnd, locked, fp3):
    return {"round": rnd, "race": f"R{rnd}", "cells": {"Locked": locked, "FP3 order": fp3,
            "Most expensive": None, "Crowd": None, "Hindsight best": 200.0}, "why": {}}


def test_summary_counts_wins_not_ties():
    s = tr.summarise([_row(1, 100.0, 90.0), _row(2, 80.0, 80.0)])
    assert s["FP3 order"]["beaten"] == 1 and s["FP3 order"]["of"] == 2


def test_summary_averages_only_races_with_a_number():
    s = tr.summarise([_row(1, 100.0, 90.0), _row(2, 80.0, 80.0), _row(3, 70.0, None)])
    assert s["Locked"] == {"avg": 83.3, "races": 3}
    assert s["FP3 order"] == {"avg": 85.0, "races": 2, "beaten": 1, "of": 2}
    assert s["Crowd"] == {"avg": None, "races": 0, "beaten": 0, "of": 0}


def test_failed_grid_keeps_the_previous_row():
    # final review: a network blip on a Monday must not quietly turn an old weekend's
    # FP3 order into "-" and shift the averages, so the last good row stays
    good = _build({18: POINTS}, {"Test GP": LOCKED})[0]
    again = tr.build_rows({18: POINTS}, [(18, "Test GP", ENTRY)], lambda race: (None, None),
                          lambda race: LOCKED, previous={18: good})
    assert again == [good]


def test_failed_grid_with_nothing_before_still_shows_the_rest():
    rows = tr.build_rows({18: POINTS}, [(18, "Test GP", ENTRY)], lambda race: (None, None),
                         lambda race: LOCKED, previous={})
    assert rows[0]["cells"]["FP3 order"] is None and rows[0]["cells"]["Locked"] == 137.0
