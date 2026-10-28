"""
Checks for the chip history (src/chip_history.py) on hand made weekends, so every
number can be worked out on paper.
"""
import pytest

import src.chip_history as ch

DRIVERS = {"A": 30.0, "B": 50.0, "C": -20.0, "D": -5.0, "E": 10.0, "F": 2.0}
CONSTRUCTORS = {"X": 10.0, "Y": -15.0, "Z": 4.0}
STARTS = {"A": 2, "B": 19, "C": 5, "D": 9, "E": 3, "F": 12}
FINISHES = {"A": 3, "B": 1, "C": 20, "D": 15, "E": 4, "F": 10}


def test_three_x_is_the_top_driver_with_who():
    v = ch.weekend_values(DRIVERS, CONSTRUCTORS, None, STARTS, FINISHES)
    assert v["3x"] == {"value": 50.0, "who": "B P19 to P1"}


def test_no_negative_is_what_an_average_team_gets_back():
    # 9 assets, negatives 20 + 5 + 15 = 40, mean 4.44, an average 7 pick team gets 31.1 back
    v = ch.weekend_values(DRIVERS, CONSTRUCTORS, None, STARTS, FINISHES)
    assert v["No Negative"] == 31.1


def test_limitless_needs_prices():
    assert ch.weekend_values(DRIVERS, CONSTRUCTORS, None, STARTS, FINISHES)["Limitless"] is None
    cheap = {"drivers": {a: 1.0 for a in DRIVERS}, "constructors": {c: 1.0 for c in CONSTRUCTORS}}
    # everything fits under $100M, so no cap costs nothing
    assert ch.weekend_values(DRIVERS, CONSTRUCTORS, cheap, STARTS, FINISHES)["Limitless"] == 0.0
    pricey = {"drivers": {**cheap["drivers"], "B": 95.0}, "constructors": cheap["constructors"]}
    # B no longer fits, unlimited keeps B (and the 2x on B), the $100M best can't
    assert ch.weekend_values(DRIVERS, CONSTRUCTORS, pricey, STARTS, FINISHES)["Limitless"] > 0


def test_weekend_missing_its_sprint_is_marked_not_faked():
    v = ch.weekend_values(DRIVERS, CONSTRUCTORS, None, STARTS, FINISHES, sprint_missing=True)
    assert v == {"3x": None, "No Negative": None, "Limitless": None}


def test_monte_carlo_is_monaco_and_kuala_lumpur_is_its_own():
    assert ch.track_key("Monte Carlo") == ch.track_key("Monaco") == "Monaco"
    assert ch.track_key("Kuala Lumpur") != ch.track_key("Sakhir")


def _weekend(season, track, three_x, nn=10.0, lim=None, sprint=False):
    return {"season": season, "round": 1, "track": track, "name": f"{track} GP", "sprint": sprint,
            "values": {"3x": {"value": three_x, "who": "X P1 to P1"}, "No Negative": nn, "Limitless": lim}}


def test_one_season_track_says_so():
    table = ch.track_table([_weekend(2025, "Sakhir", 40.0), _weekend(2025, "Monza", 50.0),
                            _weekend(2026, "Monza", 93.0)])
    rows = {r["track"]: r for r in table}
    assert rows["Sakhir"]["chips"]["3x"]["seasons"] == 1
    assert rows["Monza"]["chips"]["3x"]["seasons"] == 2
    assert rows["Monza"]["chips"]["3x"]["median"] == 71.5
    assert [v["season"] for v in rows["Monza"]["chips"]["3x"]["values"]] == [2025, 2026]
    assert rows["Monza"]["chips"]["Limitless"]["median"] is None


def test_best_tracks_ties_are_stable():
    table = ch.track_table([_weekend(2026, t, v) for t, v in
                            [("Baku", 50.0), ("Austin", 50.0), ("Monza", 60.0), ("Suzuka", 10.0)]])
    best = ch.best_tracks(table, "3x", n=3)
    assert [b["track"] for b in best["top"]] == ["Monza", "Austin", "Baku"]
    assert best["worst"]["track"] == "Suzuka"


def test_rank_check_uses_tracks_in_both_seasons():
    weekends = [_weekend(2025, t, v) for t, v in [("A", 10.0), ("B", 20.0), ("C", 30.0), ("Only25", 99.0)]]
    weekends += [_weekend(2026, t, v) for t, v in [("A", 11.0), ("B", 25.0), ("C", 35.0), ("Only26", 1.0)]]
    check = ch.rank_check(weekends, "3x")
    assert check["tracks"] == 3
    assert check["spearman"] == pytest.approx(1.0)
    assert check["top5_hits"] == 3


def test_official_seasons_finds_every_points_file(tmp_path):
    # final review: "grows every season" has to happen by itself, so the script reads
    # every season that has the game's official points, not just 2026
    for name in ["official_points_2026.json", "official_points_2027.json", "prices.json"]:
        (tmp_path / name).write_text("{}")
    assert ch.official_seasons(str(tmp_path)) == [2026, 2027]


def test_sprint_rounds_come_from_the_schedule():
    # final review: the sprint results file was missing Singapore, the calendar isn't
    import pandas as pd
    schedule = pd.DataFrame({"RoundNumber": [16, 17, 18],
                             "EventFormat": ["conventional", "sprint_qualifying", "conventional"]})
    assert ch.sprint_rounds(schedule) == {17}
