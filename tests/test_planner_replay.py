"""
Checks for the planner replay (src/planner_replay.py): playing a season three ways
(keep, free transfers only, with hits) and grading it on real points.

Same made up pool as test_planner.py. Each "round" is that pool plus made up official
points, so the answers can be worked out by hand.
"""
import copy

import pytest

from src.official_points import team_points
from src.planner_replay import play_season
from test_planner import POOL, PRICES, TEAM


def _points(scale=1.0):
    """Official points shaped like data/official_points_2026.json, here just the forecast."""
    return {"drivers": {d["Abbreviation"]: {"points": d["FantasyValue"] * scale} for d in POOL["drivers"]},
            "constructors": {c["name"]: {"points": c["score"] * scale} for c in POOL["constructors"]}}


def _rounds(n, pool=POOL, prices=PRICES):
    return [{"round": r, "pool": pool, "prices": prices, "points": _points()} for r in range(3, 3 + n)]


def test_keep_never_changes_the_team():
    season = play_season(_rounds(3), TEAM, start_bank=958.0, strategy="keep")
    for r in season["per_round"]:
        assert r["transfers"] == 0 and r["paid"] == 0
        assert sorted(r["drivers"]) == sorted(TEAM["drivers"])
    assert season["hits"] == 0


def test_free_only_never_pays_a_hit():
    season = play_season(_rounds(3), TEAM, start_bank=958.0, strategy="free_only")
    assert all(r["paid"] == 0 for r in season["per_round"])
    assert season["per_round"][1]["transfers"] == 2   # with $999M both free ones are worth it


def test_with_hits_pays_when_the_paid_row_is_highest():
    # with $999M a 3rd transfer (P1 to R2) adds far more than 10
    season = play_season(_rounds(2), TEAM, start_bank=958.0, strategy="with_hits")
    second = season["per_round"][1]
    assert second["transfers"] == 3 and second["paid"] == 1
    real = team_points(second["drivers"], second["constructors"], second["boost"], _points())
    assert second["points"] == pytest.approx(real - 10)
    assert season["hits"] == 1


def test_rollover_gives_three_after_using_one():
    # $66M all in: Pink to Red fits and nothing with 2 transfers beats it, so 1 gets used
    season = play_season(_rounds(3), TEAM, start_bank=25.0, strategy="free_only")
    assert season["per_round"][0]["transfers"] == 0      # the first round is the start team
    assert season["per_round"][1]["free_before"] == 2
    assert season["per_round"][1]["transfers"] == 1
    assert season["per_round"][2]["free_before"] == 3


def test_budget_follows_team_value_plus_bank():
    # every price goes up 5 in the second round: the team is worth 35 more, the bank stays 25
    dearer = copy.deepcopy(PRICES)
    for group in dearer.values():
        for k in group:
            group[k] += 5.0
    rounds = _rounds(1) + [{"round": 4, "pool": POOL, "prices": dearer, "points": _points()}]
    season = play_season(rounds, TEAM, start_bank=25.0, strategy="keep")
    assert season["per_round"][0]["budget"] == pytest.approx(66.0)
    assert season["per_round"][1]["budget"] == pytest.approx(101.0)


def test_round_without_a_pool_keeps_the_team():
    rounds = _rounds(1) + [{"round": 4, "pool": None, "prices": PRICES, "points": _points(2.0)}]
    season = play_season(rounds, TEAM, start_bank=958.0, strategy="with_hits")
    first, second = season["per_round"]
    assert second["transfers"] == 0 and second["drivers"] == first["drivers"]
    assert second["boost"] == first["boost"] == "B2"
    assert second["points"] == pytest.approx(team_points(first["drivers"], first["constructors"], "B2", _points(2.0)))


def test_predicted_for_round_only_sees_earlier_races(monkeypatch):
    import pandas as pd
    import src.backtest as backtest

    rows = [{"Abbreviation": "AAA", "TeamName": "Red", "GridPosition": 1, "Position": 1,
             "Status": "Finished", "RaceName": f"Race {r}", "RoundNumber": r, "Year": 2026}
            for r in (1, 2, 3, 4)]
    current = pd.DataFrame(rows)
    seen = {}

    def fake_predict(history_raw, target_raw, race_name, practice_df=None):
        seen["history_rounds"] = sorted(history_raw[history_raw["Year"] == 2026]["RoundNumber"])
        seen["practice"] = practice_df
        return target_raw.assign(Predicted=1.0)

    monkeypatch.setattr(backtest, "_predict_race", fake_predict)
    monkeypatch.setattr(backtest, "deadline_grid", lambda race: (pd.DataFrame({"grid": [race]}), "FP3"))
    race, table, session = backtest.predicted_for_round(3, current.iloc[0:0], current)
    assert race == "Race 3" and session == "FP3" and table is not None
    assert seen["history_rounds"] == [1, 2]                 # never round 3 itself, never round 4
    assert seen["practice"]["grid"].iloc[0] == "Race 3"


def test_predicted_for_round_without_practice_gives_none(monkeypatch):
    import pandas as pd
    import src.backtest as backtest

    current = pd.DataFrame([{"Abbreviation": "AAA", "TeamName": "Red", "GridPosition": 1, "Position": 1,
                             "Status": "Finished", "RaceName": "Race 3", "RoundNumber": 3, "Year": 2026}])
    monkeypatch.setattr(backtest, "deadline_grid", lambda race: (None, None))
    assert backtest.predicted_for_round(3, current.iloc[0:0], current) == ("Race 3", None, None)
