"""
Small checks for the shared helpers. The backtest and measure_grid_error use these
too but aren't covered by the endpoint tests, so the helpers get their own.
"""
import pandas as pd
import pytest

import src.fantasy as fantasy
import src.fetch_practice as fp
import src.fetch_prices as fetch_prices_mod
from src.config import PREVIOUS_SEASON, SEASON, results_path, sprint_results_path


def test_fallback_sessions_order():
    # same orders the old copied loops used
    assert fp.fallback_sessions("FP3") == ["FP3", "FP2", "FP1"]
    assert fp.fallback_sessions("FP2") == ["FP2", "FP1"]
    assert fp.fallback_sessions("FP1") == ["FP1"]
    # anything else is just tried on its own, like the old upcoming-race-pool did
    assert fp.fallback_sessions("") == [""]


def test_first_available_takes_first_that_loads(monkeypatch):
    tried = []

    def fake_grid(year, race, sess):
        tried.append(sess)
        if sess == "FP3":
            raise ValueError("FP3 not out yet")
        return pd.DataFrame({"session": [sess]})

    monkeypatch.setattr(fp, "get_practice_grid", fake_grid)
    df, used, err = fp.first_available_practice(2026, "Test GP", ["FP3", "FP2", "FP1"])
    assert used == "FP2" and df["session"].iloc[0] == "FP2" and err is None
    assert tried == ["FP3", "FP2"]  # stops as soon as one loads


def test_first_available_when_nothing_loads(monkeypatch):
    def fake_grid(year, race, sess):
        raise ValueError(f"{sess} missing")

    monkeypatch.setattr(fp, "get_practice_grid", fake_grid)
    df, used, err = fp.first_available_practice(2026, "Test GP", ["FP3", "FP2", "FP1"])
    assert df is None and used is None
    assert err == "FP1 missing"  # the last error, like the old loops kept


def test_config(monkeypatch):
    # Render and the Monday job don't set PROCESSED_DIR, they must keep using the real data
    monkeypatch.delenv("PROCESSED_DIR", raising=False)
    assert PREVIOUS_SEASON == SEASON - 1
    assert results_path() == f"data/processed/race_results_{SEASON}.csv"
    assert results_path(2025) == "data/processed/race_results_2025.csv"
    assert sprint_results_path(2026) == "data/processed/sprint_results_2026.csv"


# ---- price feed parsing ---------------------------------------------------------
#
# The feed keeps a driver's OLD team pairing around after a mid-season move, marked
# IsActive 0, and the stale one can come last. Lawson was on 15.1 at Red Bull and
# 9.3 back at Racing Bulls, and rounds 15-17 all stored 15.1 because the loop just
# overwrote on repeated TLAs. See src/fetch_prices.py.

def _feed_row(tla, value, active, team="Racing Bulls", kind="DRIVER"):
    return {
        "PositionName": kind,
        "DriverTLA": tla,
        "FUllName": team if kind == "CONSTRUCTOR" else f"{tla} driver",
        "TeamName": team,
        "Value": value,
        "IsActive": active,
    }


def test_price_feed_prefers_the_active_entry():
    # real round 17 ordering: the active Racing Bulls row first, stale Red Bull last
    items = [
        _feed_row("LAW", 9.3, "1", "Racing Bulls"),
        _feed_row("HAD", 15.7, "1", "Red Bull Racing"),
        _feed_row("LAW", 15.1, "0", "Red Bull Racing"),
    ]
    prices = fetch_prices_mod.parse_price_feed(items)
    assert prices["drivers"]["LAW"] == 9.3
    assert prices["drivers"]["HAD"] == 15.7


def test_price_feed_prefers_active_whatever_the_order():
    # same two rows the other way round, so we aren't just taking the first one
    items = [
        _feed_row("LAW", 15.1, "0", "Red Bull Racing"),
        _feed_row("LAW", 9.3, "1", "Racing Bulls"),
    ]
    assert fetch_prices_mod.parse_price_feed(items)["drivers"]["LAW"] == 9.3


def test_price_feed_keeps_a_driver_with_no_active_row():
    # IsActive describes the CURRENT roster, so in an old round's feed a driver who
    # has since moved has no active row at all. Hadjar is like this in round 12.
    # Dropping him would put holes in the history, so the inactive row still counts.
    items = [_feed_row("HAD", 14.5, "0", "Racing Bulls")]
    assert fetch_prices_mod.parse_price_feed(items)["drivers"]["HAD"] == 14.5


def test_price_feed_reads_constructors():
    items = [
        _feed_row("", 15.9, "1", "Racing Bulls", kind="CONSTRUCTOR"),
        _feed_row("LAW", 9.3, "1", "Racing Bulls"),
    ]
    prices = fetch_prices_mod.parse_price_feed(items)
    assert prices["constructors"]["Racing Bulls"] == 15.9
    assert "Racing Bulls" not in prices["drivers"]


def test_results_path_follows_processed_dir(monkeypatch):
    # the tests point this at a frozen copy, so a new race landing can't change the goldens
    monkeypatch.setenv("PROCESSED_DIR", "somewhere/else")
    assert results_path(2026) == "somewhere/else/race_results_2026.csv"
    assert sprint_results_path(2026) == "somewhere/else/sprint_results_2026.csv"


def test_constructor_scores_keep_the_avoid_quirk_for_now():
    # the team builders drop Avoid drivers before adding up constructors, the pool
    # doesn't. project 2 fixes this with measurement, the cleanup must not move it
    df = pd.DataFrame({
        "TeamName": ["Cadillac", "Cadillac", "Ferrari", "Ferrari"],
        "Abbreviation": ["PER", "BOT", "LEC", "HAM"],
        "FantasyValue": [-5.1, -3.7, 38.0, 29.7],
        "PickCategory": ["Avoid", "Risk", "Safe", "Safe"],
        "GridPosition": [21, 22, 1, 2],
    })
    prices = {"Cadillac": 3.0, "Ferrari": 28.2}
    builder = fantasy._constructor_scores(df, prices, drop_avoid=True, with_bonus=True)
    pool = fantasy._constructor_scores(df, prices, drop_avoid=False, with_bonus=False)
    assert builder["Cadillac"] == pytest.approx(-3.7)   # Bottas only, one car so no Q bonus
    assert pool["Cadillac"] == pytest.approx(-8.8)
    assert builder["Ferrari"] == pytest.approx(70.7)    # both in Q3: +3, no TeamAvgPosition: +0
    assert pool["Ferrari"] == pytest.approx(67.7)


# ---- backtest graded with the game's own points ---------------------------------

def _one_round_backtest(monkeypatch):
    """
    run_backtest on a made up season: rounds 1 and 2 are history, 3 and 4 get graded.
    The model is stubbed out (the predicted order is just the grid) so the test is about
    how the teams get SCORED, not how they're picked.
    """
    import src.backtest as backtest

    teams = {"AAA": "Red", "BBB": "Red", "CCC": "Blue", "DDD": "Blue",
             "EEE": "Green", "FFF": "Green", "GGG": "Pink", "HHH": "Pink"}
    rows = []
    for rnd in (1, 2, 3, 4):
        for grid, (abbr, team) in enumerate(teams.items(), start=1):
            rows.append({"Abbreviation": abbr, "FullName": abbr, "TeamName": team,
                         "GridPosition": grid, "Position": grid, "Status": "Finished",
                         "RaceName": f"Race {rnd}", "RoundNumber": rnd, "Year": SEASON})
    current = pd.DataFrame(rows)
    monkeypatch.setattr(backtest, "load_dataset",
                        lambda path: current if str(SEASON) in path else current.iloc[0:0])

    def fake_predict(history_raw, target_raw, race_name, practice_df=None):
        # walk forward check while we're here: nothing from this race or later
        assert history_raw["RoundNumber"].max() < target_raw["RoundNumber"].iloc[0]
        out = target_raw.copy()
        out["Predicted"] = out["GridPosition"].astype(float)
        out["TeamAvgPosition"] = 10.0
        return out
    monkeypatch.setattr(backtest, "_predict_race", fake_predict)

    def no_network(rnd):
        raise AssertionError("the official file already has this round's prices")
    monkeypatch.setattr(backtest, "fetch_prices", no_network)

    prices = {"drivers": {a: 10.0 for a in teams},
              "constructors": {t: 15.0 for t in set(teams.values())}}
    # made up official points that our own rule maths would never give
    official = {3: {
        "drivers": {a: {"points": float(i * 7 % 23)} for i, a in enumerate(teams)},
        "constructors": {t: {"points": float(len(t) * 11)} for t in set(teams.values())},
        "prices": prices,
    }}
    return backtest.run_backtest(fallback_prices=prices, use_practice=False, official=official), official


def test_backtest_scores_with_official_points(monkeypatch):
    from src.official_points import team_points

    result, official = _one_round_backtest(monkeypatch)
    race = next(r for r in result["races"] if r["round"] == 3)
    drivers = [d["Abbreviation"] for d in race["drivers"]]
    boost = next(d["Abbreviation"] for d in race["drivers"] if d["is_boost"])
    constructors = [c["name"] for c in race["constructors"]]
    assert len(drivers) == 5 and len(constructors) == 2
    assert race["model_score"] == team_points(drivers, constructors, boost, official[3])
    assert race["official_missing"] is False


def test_backtest_marks_a_round_without_official_points_missing(monkeypatch):
    # round 4 isn't in the official file. it must show as missing, never as 0
    result, _ = _one_round_backtest(monkeypatch)
    race = next(r for r in result["races"] if r["round"] == 4)
    assert race["official_missing"] is True
    assert race["model_score"] is None and race["baseline_score"] is None
    assert result["summary"]["races_tested"] == 1   # only round 3 counts


# ---- the replay has to build what live builds -----------------------------------
#
# Found while making the scorecard (2026-10-27): the replay's locked rounds didn't match
# the real locked teams. Two reasons. The replay skipped the championship nudge the live
# pipeline adds, and the replay's table carried each driver's REAL race Status, so the
# scoring gave real retirements their -20 before the race had happened. At the US GP it
# dodged Bottas, Colapinto and Bearman, all three DNFs. Live can't know that.

US_GP = "United States Grand Prix"


def _live_and_replay(dnf: str | None = None):
    """
    The same made up US GP practice grid through the live pipeline and through the
    replay, with every frozen race so far as history. dnf: a driver who "retires" in
    the made up result the replay gets handed.
    """
    import src.backtest as backtest
    from src.data_loader import load_dataset
    from src.pipeline import predict_upcoming_race

    prev = load_dataset(results_path(PREVIOUS_SEASON))
    cur = load_dataset(results_path(SEASON))
    entry = cur[cur["RoundNumber"] == cur["RoundNumber"].max()].sort_values("GridPosition")
    n = len(entry)
    practice = pd.DataFrame({
        "Abbreviation": entry["Abbreviation"].values,
        "TeamName": entry["TeamName"].values,
        "GridPosition": list(range(1, n + 1)),
        "GapToPole": [i * 0.11 for i in range(n)],
        "GapToTeammate": [0.05 * (i % 3) for i in range(n)],
        "RaceName": US_GP,
    })
    result = pd.DataFrame({
        "Abbreviation": practice["Abbreviation"],
        "Position": list(range(1, n + 1)),
        "Status": ["DNF" if a == dnf else "Finished" for a in practice["Abbreviation"]],
    })
    live = predict_upcoming_race(practice.copy())
    replay = backtest._predict_race(pd.concat([prev, cur], ignore_index=True), result,
                                    US_GP, practice.copy())
    return live.set_index("Abbreviation"), replay.set_index("Abbreviation")


def test_replay_predicts_what_live_predicts():
    live, replay = _live_and_replay()
    for a in live.index:
        assert replay.loc[a, "Predicted"] == pytest.approx(live.loc[a, "Predicted"], abs=0.01), a


def test_replay_does_not_know_who_retires():
    live, replay = _live_and_replay(dnf="BOT")
    live_fv = fantasy.calculate_fantasy_score(live.reset_index(), race_name=US_GP).set_index("Abbreviation")
    replay_fv = fantasy.calculate_fantasy_score(replay.reset_index(), race_name=US_GP).set_index("Abbreviation")
    assert replay_fv.loc["BOT", "FantasyValue"] == pytest.approx(live_fv.loc["BOT", "FantasyValue"])


# ---- real game rules, behind switches that start OFF (project 2, Task 4) -------

def test_real_quali_rules_give_zero_from_p11(monkeypatch):
    # the game: P1 to P10 score +10 down to +1, P11 to P20 score 0. the -5 is only
    # for not setting a time, which we can't predict
    monkeypatch.setattr(fantasy, "REAL_QUALI_RULES", True)
    assert [fantasy.qualifying_score(p) for p in (1, 10, 11, 16, 22)] == [10, 1, 0, 0, 0]


def test_old_quali_rules_unchanged_while_switched_off():
    assert fantasy.REAL_QUALI_RULES is False
    assert fantasy.qualifying_score(16) == -5


def _two_car_frame(grids):
    rows = []
    for team, (g1, g2) in grids.items():
        rows += [{"TeamName": team, "Abbreviation": f"{team}1", "FantasyValue": 0.0,
                  "PickCategory": "Risk", "GridPosition": g1},
                 {"TeamName": team, "Abbreviation": f"{team}2", "FantasyValue": 0.0,
                  "PickCategory": "Risk", "GridPosition": g2}]
    return pd.DataFrame(rows)


GRIDS = {"BothQ3": (1, 2), "OneQ3": (3, 14), "BothQ2": (11, 12), "OneQ2": (12, 18), "NoneQ2": (17, 19)}


def test_real_constructor_bonus_values(monkeypatch):
    # the game: -1 neither in Q2, +1 one in Q2, +3 both in Q2, +5 one in Q3, +10 both in Q3
    monkeypatch.setattr(fantasy, "REAL_CONSTRUCTOR_QUALI_BONUS", True)
    scores = fantasy._constructor_scores(_two_car_frame(GRIDS), {t: 1.0 for t in GRIDS},
                                         drop_avoid=False, with_bonus=True)
    assert scores == {"BothQ3": 10, "OneQ3": 5, "BothQ2": 3, "OneQ2": 1, "NoneQ2": -1}


def test_old_constructor_bonus_unchanged_while_switched_off():
    assert fantasy.REAL_CONSTRUCTOR_QUALI_BONUS is False
    scores = fantasy._constructor_scores(_two_car_frame(GRIDS), {t: 1.0 for t in GRIDS},
                                         drop_avoid=False, with_bonus=True)
    assert scores == {"BothQ3": 3, "OneQ3": 1, "BothQ2": 1, "OneQ2": 0, "NoneQ2": 0}


def _chip_pool():
    drivers = [{"Abbreviation": a, "TeamName": t, "GridPosition": g, "FantasyValue": 5.0, "DNFProb": 0.0}
               for a, t, g in [("AAA", "Red", 3), ("BBB", "Red", 17), ("CCC", "Blue", 18),
                               ("DDD", "Blue", 5), ("EEE", "Green", 9)]]
    return {"drivers": drivers, "constructors": [{"name": "Red", "score": 1.0}, {"name": "Blue", "score": 1.0}]}


def test_no_negative_ignores_back_row_with_real_quali_rules(monkeypatch):
    from src.weekend import evaluate_team_chips
    team = (["AAA", "BBB", "CCC", "DDD", "EEE"], ["Red", "Blue"])
    old = evaluate_team_chips(*team, _chip_pool(), 0.0, 0.0, "Test GP")["no_negative"]
    assert old["points_at_risk"] == 10.0          # two P16+ drivers, -5 each, the old rule
    monkeypatch.setattr(fantasy, "REAL_QUALI_RULES", True)
    new = evaluate_team_chips(*team, _chip_pool(), 0.0, 0.0, "Test GP")["no_negative"]
    assert new["points_at_risk"] == 0.0           # P11 to P20 is 0 in the game, nothing at risk
    assert "P16" not in new["reason"]


def test_championship_nudge_keeps_p22_at_the_back_when_switched_on(monkeypatch):
    # 2026 has 22 cars. the nudge clipped everyone to P20, so a P22 starter was
    # "predicted" P20 and got a made up +2 overtake bonus
    from src.championship_form import apply_championship_signal
    table = pd.DataFrame({"Abbreviation": ["LEAD", "BACK"], "GridPosition": [1, 22],
                          "Predicted": [1.0, 22.0]})
    form = pd.DataFrame({"Abbreviation": ["LEAD", "BACK"], "FormSignal": [1.0, 0.0],
                         "ChampPoints": [300, 0], "ChampPosition": [1, 2]})
    assert fantasy.CLIP_TO_REAL_FIELD is False
    old = apply_championship_signal(table, form).set_index("Abbreviation")
    assert old.loc["BACK", "Predicted"] == 20.0    # the old behaviour, left alone while off
    monkeypatch.setattr(fantasy, "CLIP_TO_REAL_FIELD", True)
    new = apply_championship_signal(table, form).set_index("Abbreviation")
    # 22 plus the backmarker nudge (+0.225) is clipped to the real field, P22, so no
    # made up places gained
    assert new.loc["BACK", "Predicted"] == 22.0
    assert new.loc["LEAD", "Predicted"] == 1.0


# ---- constructor quirks and expected extras, switches OFF (project 2, Task 5) ---

def test_fixed_quirks_count_avoid_drivers_and_add_bonus(monkeypatch):
    # same frame as the quirk test above. with the fix on, every caller adds a
    # constructor up the same way: both drivers, Avoid or not, plus the bonus
    monkeypatch.setattr(fantasy, "FIX_CONSTRUCTOR_QUIRKS", True)
    df = pd.DataFrame({
        "TeamName": ["Cadillac", "Cadillac", "Ferrari", "Ferrari"],
        "Abbreviation": ["PER", "BOT", "LEC", "HAM"],
        "FantasyValue": [-5.1, -3.7, 38.0, 29.7],
        "PickCategory": ["Avoid", "Risk", "Safe", "Safe"],
        "GridPosition": [21, 22, 1, 2],
    })
    prices = {"Cadillac": 3.0, "Ferrari": 28.2}
    builder = fantasy._constructor_scores(df, prices, drop_avoid=True, with_bonus=True)
    pool = fantasy._constructor_scores(df, prices, drop_avoid=False, with_bonus=False)
    assert builder == pool
    assert builder["Cadillac"] == pytest.approx(-8.8)   # Perez counts now, no bonus at P21/P22
    assert pool["Ferrari"] == pytest.approx(70.7)       # the pool gets the +3 too


def _builder_table():
    """
    8 drivers on 4 teams, predicted order = grid, so the two slowest (Pink) are Avoid.
    Pink is the only constructor cheap enough to fit, so every team has to take it.
    """
    teams = {"AAA": "Red", "BBB": "Red", "CCC": "Blue", "DDD": "Blue",
             "EEE": "Green", "FFF": "Green", "GGG": "Pink", "HHH": "Pink"}
    table = pd.DataFrame({
        "Abbreviation": list(teams), "TeamName": list(teams.values()),
        "GridPosition": list(range(1, 9)), "Predicted": [float(g) for g in range(1, 9)],
        "RaceName": "Test GP", "TeamAvgPosition": 10.0,
    })
    prices = {"drivers": {a: 10.0 for a in teams},
              "constructors": {"Red": 30.0, "Blue": 30.0, "Green": 30.0, "Pink": 1.0}}
    return table, prices


def test_team_builder_counts_avoid_drivers_with_quirks_fixed(monkeypatch):
    table, prices = _builder_table()
    monkeypatch.setattr(fantasy, "FIX_CONSTRUCTOR_QUIRKS", True)
    pool = fantasy.get_race_pool(table, "Test GP", prices)
    assert {d["Abbreviation"] for d in pool["drivers"] if d["PickCategory"] == "Avoid"} == {"GGG", "HHH"}
    pink = next(c["score"] for c in pool["constructors"] if c["name"] == "Pink")

    # the builders used to drop Pink's Avoid drivers before adding Pink up. now the 3
    # teams, the one-team builder and the pool all agree on what Pink is worth
    for team in (fantasy.build_budget_teams(table, "Test GP", prices, n=1)[0],
                 fantasy.build_budget_team(table, "Test GP", prices)):
        assert next(c["score"] for c in team["constructors"] if c["name"] == "Pink") == pytest.approx(pink)


def test_constructor_extras_added_only_when_switched_on(monkeypatch):
    df = pd.DataFrame({
        "TeamName": ["Ferrari", "Ferrari"], "Abbreviation": ["LEC", "HAM"],
        "FantasyValue": [38.0, 29.7], "PickCategory": ["Safe", "Safe"], "GridPosition": [1, 2],
    })
    prices = {"Ferrari": 28.2, "Haas F1 Team": 12.0}
    extras = {"Ferrari": 6.5}
    off = fantasy._constructor_scores(df, prices, drop_avoid=False, with_bonus=True, extras=extras)
    monkeypatch.setattr(fantasy, "USE_CONSTRUCTOR_EXTRAS", True)
    on = fantasy._constructor_scores(df, prices, drop_avoid=False, with_bonus=True, extras=extras)
    assert on["Ferrari"] == pytest.approx(off["Ferrari"] + 6.5)
    assert on["Haas F1 Team"] == off["Haas F1 Team"]   # no history for a team, nothing added


def test_replay_hands_each_round_extras_from_earlier_rounds_only(monkeypatch):
    import src.backtest as backtest
    seen = {}
    real_build = backtest.build_budget_teams

    def spy(table, race_name, prices, **kw):
        if "constructor_extras" in kw:
            seen[race_name] = kw["constructor_extras"]
        return real_build(table, race_name, prices, **kw)
    monkeypatch.setattr(backtest, "build_budget_teams", spy)
    _one_round_backtest(monkeypatch)
    # round 3 is the first official round, so there's no history for it yet. round 4
    # only gets round 3's leftovers, never its own
    assert seen["Race 3"] == {}
    assert set(seen["Race 4"]) == {"Red", "Blue", "Green", "Pink"}
