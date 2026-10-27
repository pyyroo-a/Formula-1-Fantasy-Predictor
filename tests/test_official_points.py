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


# ---- who owns what, saved at every lock from Mexico on ---------------------------

def test_ownership_parsed_from_feed():
    own = official_points.parse_ownership(_fixture("feed_r18.json"))
    assert own["drivers"]["LEC"] == {"selected_pct": 26.0, "captain_pct": 14.0}
    assert "Ferrari" in own["constructors"]


def test_ownership_duplicate_rows_use_the_active_one():
    old = {**_row("LAW", 15.1, active="0", team="Red Bull Racing"), "SelectedPercentage": 1, "CaptainSelectedPercentage": 0}
    new = {**_row("LAW", 9.3, active="1"), "SelectedPercentage": 7, "CaptainSelectedPercentage": 2}
    assert official_points.parse_ownership([old, new])["drivers"]["LAW"] == {"selected_pct": 7.0, "captain_pct": 2.0}


# ---- the Monday job adds each new round ------------------------------------------

def _update_data_module():
    import importlib.util
    path = Path(__file__).resolve().parent.parent / "scripts" / "update_data.py"
    spec = importlib.util.spec_from_file_location("update_data_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _quiet_update_data(monkeypatch, mod):
    # nothing in this test may touch the network or the real data files
    monkeypatch.setattr(mod, "update_season_results", lambda year, path: ["United States Grand Prix"])
    monkeypatch.setattr(mod, "update_sprint_results", lambda year, path: [])
    monkeypatch.setattr(mod, "save_prices", lambda rnd: None)
    monkeypatch.setattr(mod, "save_price_history", lambda rnd: None)


def test_update_data_saves_the_rounds_official_points(monkeypatch, capsys):
    mod = _update_data_module()
    _quiet_update_data(monkeypatch, mod)
    raced = official_points.parse_official_points(_fixture("feed_r18.json"))
    monkeypatch.setattr(official_points, "fetch_official_points", lambda rnd: raced)
    saved = []
    monkeypatch.setattr(official_points, "save_official_round", lambda rnd, pts: saved.append(rnd))
    mod.main()
    import pandas as pd
    from src.config import results_path
    newest = int(pd.read_csv(results_path())["RoundNumber"].max())
    assert saved == [newest]   # the round that just finished


def test_update_data_survives_official_points_failure(monkeypatch, capsys):
    mod = _update_data_module()
    _quiet_update_data(monkeypatch, mod)   # conftest already makes the feed unreachable
    saved = []
    monkeypatch.setattr(official_points, "save_official_round", lambda rnd, pts: saved.append(rnd))
    mod.main()
    out = capsys.readouterr().out
    assert "Added 1 new race" in out
    assert "::warning::Could not save official points" in out
    assert saved == []
