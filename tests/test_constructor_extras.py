"""
Checks for expected constructor extras (src/constructor_extras.py): what a constructor
scores on top of its two drivers and its qualifying bonus, which is mostly pit stops.
Made up rounds, no network.
"""
import pandas as pd

from src.constructor_extras import constructor_extras


def _round(ferrari, lec, ham):
    return {"drivers": {"LEC": {"points": lec}, "HAM": {"points": ham}},
            "constructors": {"Ferrari": {"points": ferrari}}}


def _results(rounds, grids=(1, 2)):
    rows = []
    for rnd in rounds:
        rows += [{"RoundNumber": rnd, "Abbreviation": "LEC", "TeamName": "Ferrari", "GridPosition": grids[0]},
                 {"RoundNumber": rnd, "Abbreviation": "HAM", "TeamName": "Ferrari", "GridPosition": grids[1]}]
    return pd.DataFrame(rows)


def test_constructor_extras_subtract_drivers_and_quali_bonus():
    # Ferrari 81, Leclerc 53 + Hamilton 20, both in Q3 (+10): 81 - 73 - 10 = -2
    official = {3: _round(81, 53, 20)}
    assert constructor_extras(official, _results([3]), before_round=4) == {"Ferrari": -2.0}


def test_constructor_extras_only_use_earlier_rounds():
    # round 5 is the race being predicted, it must not count
    official = {3: _round(81, 53, 20), 4: _round(95, 53, 20), 5: _round(500, 0, 0)}
    # round 3 leaves -2, round 4 leaves 12, so the average is 5
    assert constructor_extras(official, _results([3, 4, 5]), before_round=5) == {"Ferrari": 5.0}


def test_constructor_extras_empty_before_any_history():
    official = {1: _round(81, 53, 20)}
    assert constructor_extras(official, _results([1]), before_round=1) == {}


def test_constructor_extras_use_the_real_bonus_from_the_real_grid():
    # one car in Q3 (P4), one knocked out in Q1 (P18): +5. 60 - 30 - 20 - 5 = 5
    official = {2: _round(60, 30, 20)}
    assert constructor_extras(official, _results([2], grids=(4, 18)), before_round=3) == {"Ferrari": 5.0}
