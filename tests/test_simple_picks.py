"""
Checks for the model-free picks the scorecard grades PitWall against (src/simple_picks.py).

Small made up pools so the right answer can be worked out by hand. The pool for most
tests: 6 drivers on 3 teams, $100M budget.

    driver  team  price      constructor  price
    A       X     30         X            20
    B       X     25         Y            12
    C       Y     10         Z             6
    D       Y      8
    E       Z      6
    F       Z      5
"""
import pandas as pd

import src.simple_picks as simple_picks
from src.official_points import team_points

PRICES = {
    "drivers": {"A": 30.0, "B": 25.0, "C": 10.0, "D": 8.0, "E": 6.0, "F": 5.0},
    "constructors": {"X": 20.0, "Y": 12.0, "Z": 6.0},
}
TEAMS = {"A": "X", "B": "X", "C": "Y", "D": "Y", "E": "Z", "F": "Z"}


def _grid(order):
    """A practice grid in the shape the backtest has, fastest first."""
    return pd.DataFrame({
        "Abbreviation": order,
        "TeamName": [TEAMS[a] for a in order],
        "GridPosition": list(range(1, len(order) + 1)),
    })


def _picked(team):
    return (
        sorted(d["Abbreviation"] for d in team["drivers"]),
        sorted(c["name"] for c in team["constructors"]),
        team["boost_pick"]["Abbreviation"],
    )


def test_fp3_order_team_takes_the_fastest_that_fit():
    # grid C A E B D F, so best car per team: X P2, Y P1, Z P3.
    # leaving F out (P6) gives drivers 1+2+3+4+5 = 15, but costs 79, so only Y+Z (18)
    # fits, +1+3 = 19. every other legal team adds up to 20 or more
    team = simple_picks.fp3_order_team(_grid(["C", "A", "E", "B", "D", "F"]), PRICES)
    assert _picked(team) == (["A", "B", "C", "D", "E"], ["Y", "Z"], "C")


def test_fp3_order_team_never_reads_fantasy_value():
    # same grid with a nonsense FantasyValue column that loves the slow drivers.
    # the answer mustn't move, this column is the model and this pick is model-free
    grid = _grid(["C", "A", "E", "B", "D", "F"])
    grid["FantasyValue"] = [-50.0, -40.0, -30.0, 10.0, 90.0, 99.0]
    grid["Predicted"] = [22.0, 21.0, 20.0, 3.0, 2.0, 1.0]
    team = simple_picks.fp3_order_team(grid, PRICES)
    assert _picked(team) == (["A", "B", "C", "D", "E"], ["Y", "Z"], "C")


def test_fp3_order_team_breaks_a_tie_with_the_cheaper_team():
    # Y and Z both have their best car on P2 here, so X+Y and X+Z add up the same
    # and Z is the cheaper one. (two cars on P2 can't happen in real life, it's just
    # the easiest way to make a tie)
    grid = pd.DataFrame({
        "Abbreviation": ["A", "C", "E", "B", "D", "F"],
        "TeamName": ["X", "Y", "Z", "X", "Y", "Z"],
        "GridPosition": [1, 2, 2, 4, 5, 6],
    })
    prices = {"drivers": PRICES["drivers"], "constructors": {"X": 1.0, "Y": 12.0, "Z": 6.0}}
    team = simple_picks.fp3_order_team(grid, prices)
    # leave out F (P6): drivers 1+2+2+4+5 = 14, cost 79. X (P1) plus Y or Z (both P2),
    # 3 either way, Z is $6M cheaper
    assert _picked(team) == (["A", "B", "C", "D", "E"], ["X", "Z"], "A")


def test_most_expensive_team_spends_the_most_under_budget():
    # leaving out C costs 74 for the drivers, X+Z is 26, exactly 100. nothing else
    # gets there (leave out F is 79, the cheapest pair Y+Z only makes 97)
    team = simple_picks.most_expensive_team(PRICES)
    assert _picked(team) == (["A", "B", "D", "E", "F"], ["X", "Z"], "A")


def test_crowd_team_maximises_ownership_and_boosts_most_captained():
    # same shape the snapshot saves (src/official_points.py parse_ownership)
    def own(sel, cap=0.0):
        return {"selected_pct": sel, "captain_pct": cap}
    ownership = {
        "drivers": {"A": own(50, 30), "B": own(10, 5), "C": own(40, 45),
                    "D": own(30), "E": own(20), "F": own(35)},
        "constructors": {"X": own(60), "Y": own(30), "Z": own(40)},
    }
    # leaving out B (the least owned) is 175% and only costs 59, so X+Z (100%) fits:
    # 275. the most captained driver in that team is C, not the most owned A
    team = simple_picks.crowd_team(ownership, PRICES)
    assert _picked(team) == (["A", "C", "D", "E", "F"], ["X", "Z"], "C")


def test_hindsight_best_counts_the_boost():
    # P and Q score 20 each, S scores 35, the four fillers score 0. the drivers can
    # spend 45 (47 minus the cheapest pair), so it's P+Q+3 fillers or S+4 fillers.
    # without the 2x, P+Q wins 40 to 35. with it, S wins 35+35 = 70 to 20+20+20 = 60
    prices = {
        "drivers": {"P": 20.0, "Q": 20.0, "S": 35.0,
                    "F1": 1.0, "F2": 1.0, "F3": 1.0, "F4": 1.0},
        "constructors": {"X": 1.0, "Y": 1.0, "Z": 1.0},
    }

    def pts(p):
        return {"points": p}
    round_points = {
        "drivers": {"P": pts(20), "Q": pts(20), "S": pts(35),
                    "F1": pts(0), "F2": pts(0), "F3": pts(0), "F4": pts(0)},
        "constructors": {"X": pts(10), "Y": pts(5), "Z": pts(0)},
    }
    team = simple_picks.hindsight_best_team(round_points, prices, budget=47.0)
    assert _picked(team) == (["F1", "F2", "F3", "F4", "S"], ["X", "Y"], "S")
    assert team_points([d["Abbreviation"] for d in team["drivers"]],
                       [c["name"] for c in team["constructors"]],
                       team["boost_pick"]["Abbreviation"], round_points) == 85.0


def test_nothing_fits_returns_none():
    ownership = {"drivers": {a: {"selected_pct": 1.0, "captain_pct": 1.0} for a in TEAMS},
                 "constructors": {c: {"selected_pct": 1.0, "captain_pct": 1.0} for c in "XYZ"}}
    round_points = {"drivers": {a: {"points": 1.0} for a in TEAMS},
                    "constructors": {c: {"points": 1.0} for c in "XYZ"}}
    assert simple_picks.fp3_order_team(_grid(list("ABCDEF")), PRICES, budget=5.0) is None
    assert simple_picks.most_expensive_team(PRICES, budget=5.0) is None
    assert simple_picks.crowd_team(ownership, PRICES, budget=5.0) is None
    assert simple_picks.hindsight_best_team(round_points, PRICES, budget=5.0) is None
