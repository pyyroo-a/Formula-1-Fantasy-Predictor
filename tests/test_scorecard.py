"""
Checks for the season scorecard (scripts/scorecard.py): every column graded with the
game's own points, and anything we don't have shown as missing, never as 0.

Same made up 6 driver pool as test_simple_picks.py. No network, no real season.
"""
import importlib.util
from pathlib import Path

import pandas as pd

import src.simple_picks as simple_picks
from src.official_points import team_points

ROOT = Path(__file__).resolve().parent.parent

PRICES = {
    "drivers": {"A": 30.0, "B": 25.0, "C": 10.0, "D": 8.0, "E": 6.0, "F": 5.0},
    "constructors": {"X": 20.0, "Y": 12.0, "Z": 6.0},
}
TEAMS = {"A": "X", "B": "X", "C": "Y", "D": "Y", "E": "Z", "F": "Z"}
GRID = pd.DataFrame({
    "Abbreviation": ["C", "A", "E", "B", "D", "F"],
    "TeamName": ["Y", "X", "Z", "X", "Y", "Z"],
    "GridPosition": [1, 2, 3, 4, 5, 6],
})
POINTS = {
    "drivers": {a: {"points": p} for a, p in
                {"A": 30.0, "B": 12.0, "C": 25.0, "D": -3.0, "E": 8.0, "F": 2.0}.items()},
    "constructors": {"X": {"points": 40.0}, "Y": {"points": 35.0}, "Z": {"points": 5.0}},
}
LOCKED_TEAM = {
    "drivers": [{"Abbreviation": a} for a in ["A", "C", "D", "E", "F"]],
    "constructors": [{"name": "X"}, {"name": "Z"}],
    "boost_pick": {"Abbreviation": "A"},
}


def _own(sel, cap=0.0):
    return {"selected_pct": sel, "captain_pct": cap}


OWNERSHIP = {
    "drivers": {"A": _own(50, 30), "B": _own(10), "C": _own(40, 45),
                "D": _own(30), "E": _own(20), "F": _own(35)},
    "constructors": {"X": _own(60), "Y": _own(30), "Z": _own(40)},
}


def _scorecard():
    spec = importlib.util.spec_from_file_location("scorecard_under_test", ROOT / "scripts" / "scorecard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _score(team, pts=POINTS):
    return team_points([d["Abbreviation"] for d in team["drivers"]],
                       [c["name"] for c in team["constructors"]],
                       team["boost_pick"]["Abbreviation"], pts)


def test_every_column_is_graded_with_official_points():
    sc = _scorecard()
    snap = {"teams": [LOCKED_TEAM], "ownership": OWNERSHIP}
    row = sc.grade_round(18, "Test GP", POINTS, PRICES, GRID, snap, {"model_score": 77.0})
    cells = row["cells"]
    assert cells["Locked"] == _score(LOCKED_TEAM)
    assert cells["PitWall replay"] == 77.0
    assert cells["FP3 order"] == _score(simple_picks.fp3_order_team(GRID, PRICES))
    assert cells["Most expensive"] == _score(simple_picks.most_expensive_team(PRICES))
    assert cells["Crowd"] == _score(simple_picks.crowd_team(OWNERSHIP, PRICES))
    assert cells["Hindsight best"] == _score(simple_picks.hindsight_best_team(POINTS, PRICES))
    # the ceiling really is the ceiling
    assert cells["Hindsight best"] >= max(v for v in cells.values() if v is not None)


def test_old_snapshot_without_ownership_still_grades():
    # R13 to R18 were locked before we saved ownership. the locked team still counts,
    # the crowd column is just missing for that race
    sc = _scorecard()
    row = sc.grade_round(18, "Test GP", POINTS, PRICES, GRID, {"teams": [LOCKED_TEAM]}, None)
    assert row["cells"]["Locked"] == _score(LOCKED_TEAM)
    assert row["cells"]["Crowd"] is None
    assert "ownership" in row["why"]["Crowd"]
    assert row["cells"]["PitWall replay"] is None


def test_round_without_official_points_is_missing_not_zero():
    sc = _scorecard()
    row = sc.grade_round(19, "Test GP", None, PRICES, GRID,
                         {"teams": [LOCKED_TEAM], "ownership": OWNERSHIP}, {"model_score": None})
    assert all(v is None for v in row["cells"].values())
    assert all("official points" in row["why"][c] for c in sc.COLUMNS)


def test_simple_picks_only_get_drivers_who_were_there():
    # the price list keeps drivers who've left the grid (Tsunoda sat in it at 9.7 for
    # weeks). nobody could have picked them, so they're out of every simple column
    sc = _scorecard()
    prices = {"drivers": {**PRICES["drivers"], "GONE": 40.0}, "constructors": PRICES["constructors"]}
    points = {"drivers": {**POINTS["drivers"], "GONE": {"points": 99.0}},
              "constructors": POINTS["constructors"]}
    row = sc.grade_round(18, "Test GP", points, prices, GRID, None, None)
    for col in ("FP3 order", "Most expensive", "Hindsight best"):
        assert "GONE" not in row["teams"][col]


def test_summary_averages_only_where_a_column_exists():
    sc = _scorecard()
    rows = [
        {"round": 1, "race": "One", "cells": {"Locked": None, "PitWall replay": None,
         "FP3 order": 50.0, "Most expensive": 40.0, "Crowd": None, "Hindsight best": 200.0}},
        {"round": 2, "race": "Two", "cells": {"Locked": 90.0, "PitWall replay": 100.0,
         "FP3 order": 80.0, "Most expensive": 120.0, "Crowd": None, "Hindsight best": 210.0}},
        {"round": 3, "race": "Three", "cells": {"Locked": 70.0, "PitWall replay": 60.0,
         "FP3 order": 60.0, "Most expensive": 30.0, "Crowd": None, "Hindsight best": 190.0}},
    ]
    s = sc.summarise(rows)
    assert s["average"]["FP3 order"] == (63.3, 3)
    assert s["average"]["Locked"] == (80.0, 2)
    assert s["average"]["Crowd"] == (None, 0)
    # same races as the replay (2 and 3), so the averages compare like with like
    assert s["average_on_replay_races"]["FP3 order"] == (70.0, 2)
    # replay vs each simple column, only where both exist. a tie isn't a win
    assert s["replay_beat"]["FP3 order"] == (1, 2)       # won R2, tied R3
    assert s["replay_beat"]["Most expensive"] == (1, 2)  # lost R2, won R3
    assert s["replay_beat"]["Crowd"] == (0, 0)


def test_report_shows_missing_as_a_dash_with_the_reason():
    sc = _scorecard()
    row = sc.grade_round(18, "Test GP", POINTS, PRICES, GRID, {"teams": [LOCKED_TEAM]}, None)
    text = sc.render([row], rules_name="current", today="2026-10-27")
    assert "all points are official F1 Fantasy points" in text
    assert "current" in text and "2026-10-27" in text
    line = next(l for l in text.splitlines() if l.startswith("| R18"))
    assert " - |" in line
    assert "ownership" in text   # the footnote says why the crowd is missing


def _replay_row(drivers, constructors, boost, score):
    """A race row the way run_backtest returns it."""
    return {"model_score": score,
            "drivers": [{"Abbreviation": a, "is_boost": a == boost} for a in drivers],
            "constructors": [{"name": c} for c in constructors]}


def test_scorecard_checks_the_replay_rebuilds_the_locked_team():
    # the replay is only worth trusting if it rebuilds what PitWall really locked.
    # it didn't once (it skipped the standings nudge and knew who'd retire), so the
    # scorecard says it out loud every time
    sc = _scorecard()
    snap = {"teams": [LOCKED_TEAM]}
    same = sc.grade_round(17, "Same GP", POINTS, PRICES, GRID, snap,
                          _replay_row(["F", "E", "D", "C", "A"], ["Z", "X"], "A", 1.0))
    other = sc.grade_round(18, "Other GP", POINTS, PRICES, GRID, snap,
                           _replay_row(["F", "E", "D", "C", "A"], ["Z", "X"], "C", 1.0))
    unlocked = sc.grade_round(5, "Old GP", POINTS, PRICES, GRID, None,
                              _replay_row(["F", "E", "D", "C", "A"], ["Z", "X"], "A", 1.0))
    assert same["replay_matches_lock"] is True
    assert other["replay_matches_lock"] is False      # same team, different 2x
    assert unlocked["replay_matches_lock"] is None
    text = sc.render([same, other, unlocked], rules_name="current", today="2026-10-27")
    assert "rebuilt the exact locked team on 1 of 2 locked weekends" in text
    assert "R18" in text.split("rebuilt the exact locked team")[1].splitlines()[0]


def test_rules_names_turn_on_the_right_switches():
    sc = _scorecard()
    assert sc.switches_for("current") == {}
    assert sc.switches_for("quali") == {"REAL_QUALI_RULES": True}
    assert sc.switches_for("quali+bonus") == {"REAL_QUALI_RULES": True,
                                              "REAL_CONSTRUCTOR_QUALI_BONUS": True}
    assert sc.switches_for("clip") == {"CLIP_TO_REAL_FIELD": True}
    try:
        sc.switches_for("quali+nonsense")
        assert False, "an unknown rule name should be refused"
    except ValueError:
        pass


def test_rules_helper_puts_the_switches_back():
    import src.fantasy as fantasy
    sc = _scorecard()
    with sc.rules(**sc.switches_for("quali+bonus+clip")):
        assert fantasy.REAL_QUALI_RULES and fantasy.REAL_CONSTRUCTOR_QUALI_BONUS
        assert fantasy.CLIP_TO_REAL_FIELD
    assert not (fantasy.REAL_QUALI_RULES or fantasy.REAL_CONSTRUCTOR_QUALI_BONUS
                or fantasy.CLIP_TO_REAL_FIELD)


def test_all_rules_turns_on_every_switch():
    sc = _scorecard()
    assert sc.switches_for("quirks") == {"FIX_CONSTRUCTOR_QUIRKS": True}
    assert sc.switches_for("extras") == {"USE_CONSTRUCTOR_EXTRAS": True}
    assert sc.switches_for("all") == {
        "REAL_QUALI_RULES": True, "REAL_CONSTRUCTOR_QUALI_BONUS": True, "CLIP_TO_REAL_FIELD": True,
        "FIX_CONSTRUCTOR_QUIRKS": True, "USE_CONSTRUCTOR_EXTRAS": True}
