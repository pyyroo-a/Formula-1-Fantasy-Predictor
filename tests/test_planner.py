"""
Checks for the transfer ladder (src/planner.py), on a small made up pool so every
answer can be worked out by hand. No network, no model.

    driver  team  grid  points  price      constructor  points  price
    R1      Red     1     40     30         Red            70     30
    R2      Red     2     30     28         Blue           30     20
    B1      Blue    3     20     15         Green           2     10
    B2      Blue    9     10      8         Pink          -11      5
    G1      Green  14      4      6
    G2      Green  17     -2      5
    P1      Pink   19     -5      4
    P2      Pink   20     -6      3

The team: B2 G1 G2 P1 P2 + Green Pink, costs 41. Expected: drivers 1, constructors -9,
and the 2x on B2 (the only one in Q3) adds 10, so 2.
"""
import pytest

import src.planner as planner

DRIVERS = [("R1", "Red", 1, 40.0, 30.0), ("R2", "Red", 2, 30.0, 28.0),
           ("B1", "Blue", 3, 20.0, 15.0), ("B2", "Blue", 9, 10.0, 8.0),
           ("G1", "Green", 14, 4.0, 6.0), ("G2", "Green", 17, -2.0, 5.0),
           ("P1", "Pink", 19, -5.0, 4.0), ("P2", "Pink", 20, -6.0, 3.0)]
CONSTRUCTORS = [("Red", 70.0, 30.0), ("Blue", 30.0, 20.0), ("Green", 2.0, 10.0), ("Pink", -11.0, 5.0)]

POOL = {
    "drivers": [{"Abbreviation": a, "TeamName": t, "GridPosition": g, "Predicted": float(g),
                 "FantasyValue": fv, "Price": p, "PickCategory": "Risk"}
                for a, t, g, fv, p in DRIVERS],
    "constructors": [{"name": n, "score": s, "price": p} for n, s, p in CONSTRUCTORS],
}
PRICES = {"drivers": {a: p for a, _, _, _, p in DRIVERS},
          "constructors": {n: p for n, _, p in CONSTRUCTORS}}
TEAM = {"drivers": ["B2", "G1", "G2", "P1", "P2"], "constructors": ["Green", "Pink"]}


def _swaps(row):
    return sorted((s["kind"], s["out"], s["in"]) for s in row["swaps"])


def test_next_free_transfers_rolls_one_over():
    assert planner.next_free_transfers(2, 1) == 3   # my case: use 1 of 2, get 3 next week
    assert planner.next_free_transfers(2, 0) == 3   # capped at 3
    assert planner.next_free_transfers(2, 2) == 2
    assert planner.next_free_transfers(2, 3) == 2   # a paid one doesn't make it worse


def test_keep_row_is_your_team_with_its_2x():
    ladder = planner.transfer_ladder(TEAM, POOL, PRICES, budget=70.0, free_transfers=2)
    keep = ladder["rows"][0]
    assert keep["transfers"] == 0 and keep["paid"] == 0 and keep["swaps"] == []
    assert keep["boost"] == "B2"
    assert keep["expected"] == pytest.approx(2.0)
    assert keep["vs_keep"] == 0


def test_best_with_transfers_takes_the_best_swap():
    # with $70M, Pink to Red (66 all in) is worth 1 + (2 + 70) + 10 = 83. the best driver
    # swap, P2 to R1, makes 78
    best = planner.best_with_transfers(TEAM, POOL, PRICES, budget=70.0, k=1)
    assert _swaps(best) == [("constructor", "Pink", "Red")]
    assert best["expected"] == pytest.approx(83.0)
    assert best["cost"] == pytest.approx(66.0)


def test_rows_are_independent_not_nested():
    # the best single swap is Pink to Red, but the best PAIR drops Green for Red instead
    # and puts B1 in for G1, exactly $70M: drivers 17 + Red 70 and Pink -11 + 2x on B1 20
    ladder = planner.transfer_ladder(TEAM, POOL, PRICES, budget=70.0, free_transfers=2)
    two = ladder["rows"][2]
    assert _swaps(two) == [("constructor", "Green", "Red"), ("driver", "G1", "B1")]
    assert two["expected"] == pytest.approx(96.0)
    assert two["boost"] == "B1"


def test_paid_row_has_the_hit_taken_off():
    ladder = planner.transfer_ladder(TEAM, POOL, PRICES, budget=999.0, free_transfers=2)
    assert [r["transfers"] for r in ladder["rows"]] == [0, 1, 2, 3]
    paid = ladder["rows"][3]
    three = planner.best_with_transfers(TEAM, POOL, PRICES, budget=999.0, k=3)
    assert paid["paid"] == 1
    assert paid["expected"] == pytest.approx(three["expected"] - 10)
    assert paid["vs_keep"] == pytest.approx(three["expected"] - 10 - 2.0)


def test_no_paid_row_when_switched_off(monkeypatch):
    monkeypatch.setattr(planner, "SHOW_PAID_ROW", False)
    ladder = planner.transfer_ladder(TEAM, POOL, PRICES, budget=999.0, free_transfers=2)
    assert [r["transfers"] for r in ladder["rows"]] == [0, 1, 2]
    assert "Transfer 3 costs -10." in ladder["facts"]
    # the replay still needs it, so it can be asked for
    forced = planner.transfer_ladder(TEAM, POOL, PRICES, budget=999.0, free_transfers=2, paid_row=True)
    assert [r["transfers"] for r in forced["rows"]] == [0, 1, 2, 3]


def test_ladder_rows_stay_within_budget_even_if_keep_does_not():
    # $30M is less than the team costs (41). keep still shows, nothing else can break it
    ladder = planner.transfer_ladder(TEAM, POOL, PRICES, budget=30.0, free_transfers=2)
    assert ladder["rows"][0]["transfers"] == 0
    for row in ladder["rows"][1:]:
        assert row.get("none") or row["cost"] <= 30.0


def test_best_with_transfers_never_repeats_a_pick():
    for k in range(1, 5):
        best = planner.best_with_transfers(TEAM, POOL, PRICES, budget=999.0, k=k)
        assert len(set(best["drivers"])) == 5 and len(set(best["constructors"])) == 2
        assert len(best["swaps"]) == k


def test_ladder_flags_a_driver_not_in_this_weekends_field():
    team = {"drivers": ["B2", "G1", "G2", "P1", "GONE"], "constructors": ["Green", "Pink"]}
    ladder = planner.transfer_ladder(team, POOL, PRICES, budget=70.0, free_transfers=2)
    assert ladder["missing"] == ["GONE"]
    assert ladder["rows"][0]["expected"] == pytest.approx(8.0)   # P2's -6 is gone, GONE scores 0
    assert any("GONE" in f for f in ladder["facts"])


def test_swaps_say_why_in_practice_positions():
    ladder = planner.transfer_ladder(TEAM, POOL, PRICES, budget=70.0, free_transfers=2)
    reasons = sorted(s["reason"] for s in ladder["rows"][2]["swaps"])
    assert reasons == ["G1 P14 to B1 P3 in FP3", "Green P14 and P17 to Red P1 and P2 in FP3"]


def test_facts_are_facts_not_orders():
    ladder = planner.transfer_ladder(TEAM, POOL, PRICES, budget=70.0, free_transfers=2)
    facts = ladder["facts"]
    assert "The highest expected total is with 2 transfers (96)." in facts
    assert "Transfer 1 adds +81." in facts
    assert "Transfer 2 adds +13." in facts
    assert "Skip transfer 2 and you'd have 3 free transfers next week." in facts
    # no 3 transfer team fits in $70M, so the paid fact is just the cost
    assert ladder["rows"][3].get("none")
    assert "Transfer 3 costs -10." in facts
    rich = planner.transfer_ladder(TEAM, POOL, PRICES, budget=999.0, free_transfers=2)["facts"]
    paid = [f for f in rich if f.startswith("Transfer 3 adds")]
    assert len(paid) == 1 and paid[0].endswith("but costs -10.")
    for f in facts + rich:
        assert not any(w in f.lower() for w in ("should", "do this", "recommend"))
