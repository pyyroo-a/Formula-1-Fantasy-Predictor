"""
Checks for the points referee (src/official_points.py): the game's own points per
driver and constructor, read from the F1 Fantasy feed.

feed_r18.json is the real round 18 (US GP) feed, saved on 2026-10-27. No test here
touches the network.
"""
import json
from pathlib import Path

import src.official_points as official_points

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _row(tla, price, active="1", pts="0", team="Racing Bulls"):
    """A minimal driver row shaped like the feed's."""
    return {
        "PositionName": "DRIVER", "DriverTLA": tla, "FUllName": tla, "TeamName": team,
        "Value": price, "IsActive": active, "GamedayPoints": pts,
        "QualifyingPoints": "", "RacePoints": pts, "SprintPoints": "",
    }


def test_team_points_matches_the_app_for_ashens_us_gp_team():
    pts = official_points.parse_official_points(_fixture("feed_r18.json"))
    total = official_points.team_points(
        ["LEC", "ANT", "PER", "LIN", "HUL"], ["Ferrari", "Haas F1 Team"], "LEC", pts)
    assert total == 238.0   # my real score in the app


def test_points_split_into_qualifying_and_race():
    pts = official_points.parse_official_points(_fixture("feed_r18.json"))
    assert pts["drivers"]["LEC"] == {"points": 53.0, "qualifying": 7.0, "race": 46.0, "sprint": 0.0}
    assert pts["constructors"]["Ferrari"]["points"] == 81.0


def test_duplicate_driver_rows_use_the_active_one():
    # Lawson after his move: the old pairing stays in the feed with 0 points
    items = [_row("LAW", 15.1, active="0", pts="0", team="Red Bull Racing"),
             _row("LAW", 9.3, active="1", pts="12")]
    assert official_points.parse_official_points(items)["drivers"]["LAW"]["points"] == 12.0


def test_unraced_round_is_not_stored():
    zeros = {"drivers": {"LEC": {"points": 0.0, "qualifying": 0.0, "race": 0.0, "sprint": 0.0}},
             "constructors": {}}
    assert official_points.is_raced(zeros) is False
    assert official_points.is_raced(official_points.parse_official_points(_fixture("feed_r18.json"))) is True
