"""
Replays completed races to measure whether the model's team picks would
actually have scored well.

The rule that makes this honest: when backtesting race N, the model is trained
only on races before N. It never sees the race it is predicting.
"""

import numpy as np
import pandas as pd

from src.data_loader import load_dataset
from src.config import SEASON, PREVIOUS_SEASON, results_path, sprint_results_path
from src.features import build_features
from src.models import prepare_data, train_model, predict, shrink_to_grid
from src.fantasy import calculate_fantasy_score, build_budget_teams, RACE_POINTS, sprint_score
# these two live in fantasy.py now so the chip history can use them without the model
from src.fantasy import actual_driver_points as _actual_driver_points
from src.fantasy import actual_constructor_points as _actual_constructor_points
from src.circuit_profiles import get_blend_weights
from src.fetch_prices import fetch_prices
from src.fetch_practice import deadline_grid  # noqa: F401 (scorecard imports it from here)
from src.dnf import DNFModel
from src.championship_form import (
    CHAMPIONSHIP_WEIGHT,
    apply_championship_signal,
    compute_championship_form,
)
from src.official_points import team_points
from src.constructor_extras import constructor_extras

MIN_HISTORY_ROUNDS = 2  # need some 2026 form before predictions mean anything


def _predict_race(
    history_raw: pd.DataFrame,
    target_raw: pd.DataFrame,
    race_name: str,
    practice_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Trains on history_raw only, then predicts finishing positions.

    With practice_df, this reproduces production exactly: grid is *estimated*
    from practice pace (the real grid does not exist at the fantasy deadline),
    and the full model/practice/teammate/circuit blend is used.

    Without it, there is no practice signal: the FP3-pace and teammate-gap
    terms are dropped and the remaining weights renormalised. That variant
    hands the model the real grid, which production never has.
    """
    history = build_features(history_raw)

    # Latest rolling form per driver, taken strictly from races before this one
    latest_form = (
        history.sort_values(["Abbreviation", "Year", "RoundNumber"])
        .groupby("Abbreviation")
        .last()
        .reset_index()[[
            "Abbreviation", "PreviousPosition", "AveragePositionChange",
            "Consistency", "Rolling3Average", "WinRate", "PodiumRate", "TeamAvgPosition",
        ]]
    )

    if practice_df is not None:
        # Production path: practice pace supplies the estimated grid and the
        # driver pool. Actual finishing positions are attached only so the
        # caller can score afterwards, they never reach the model.
        actuals = target_raw[["Abbreviation", "Position"]]
        upcoming = practice_df.merge(actuals, on="Abbreviation", how="left")
        upcoming["Position"] = upcoming["Position"].fillna(20.0)
        upcoming = upcoming.merge(latest_form, on="Abbreviation", how="left")
    else:
        # Merge onto the raw target rows so drivers who DNF'd are still included.
        # build_features() drops non-finishers, and excluding them here would hide
        # every -20 the optimiser walked into.
        upcoming = target_raw.merge(latest_form, on="Abbreviation", how="left")

    # nobody has retired yet at the deadline, same as live. this used to carry the
    # REAL race Status, so the scoring handed real retirements their -20 before the
    # race and the replay dodged them (US GP: Bottas, Colapinto, Bearman)
    upcoming["Status"] = "Finished"

    upcoming["PreviousPosition"] = upcoming["PreviousPosition"].fillna(10.0)
    upcoming["AveragePositionChange"] = upcoming["AveragePositionChange"].fillna(0.0)
    upcoming["Consistency"] = upcoming["Consistency"].fillna(0.0)
    upcoming["Rolling3Average"] = upcoming["Rolling3Average"].fillna(10.0)
    upcoming["WinRate"] = upcoming["WinRate"].fillna(0.0)
    upcoming["PodiumRate"] = upcoming["PodiumRate"].fillna(0.0)
    upcoming["TeamAvgPosition"] = upcoming["TeamAvgPosition"].fillna(10.0)

    upcoming["GridvsForm"] = upcoming["GridPosition"] - upcoming["Rolling3Average"]
    upcoming["FormTrend"] = upcoming["Rolling3Average"] - upcoming["PreviousPosition"]

    # prepare_data needs the target column present; the values are never used.
    actual_position = upcoming["Position"].copy()
    upcoming["Position"] = 10.0

    X_train, y_train, X_test, _ = prepare_data(history, upcoming)
    sample_weight = np.where(history["Year"] == SEASON, 5.0, 1.0)
    model = train_model(X_train, y_train, sample_weight=sample_weight)
    base_predictions = predict(model, X_test)

    # Circuit history: how these drivers have done at this track before
    circuit_history = (
        history[history["RaceName"] == race_name]
        .groupby("Abbreviation")["Position"]
        .mean()
    )
    circuit_signal = (
        upcoming["Abbreviation"].map(circuit_history)
        .fillna(pd.Series(base_predictions, index=upcoming.index))
        .values
    )

    w = get_blend_weights(race_name)

    if practice_df is not None:
        # Full production blend, including the practice signals
        max_gap = upcoming["GapToPole"].max()
        practice_pace = (
            1 + (upcoming["GapToPole"].values / max_gap) * 19
            if max_gap > 0 else upcoming["GridPosition"].values.astype(float)
        )

        max_team_gap = upcoming["GapToTeammate"].max()
        teammate_penalty = (
            (upcoming["GapToTeammate"].values / max_team_gap) * 3
            if max_team_gap > 0 else np.zeros(len(upcoming))
        )

        blended = (
            w["model"] * base_predictions
            + w["practice"] * practice_pace
            + w["teammate"] * teammate_penalty
            + w["circuit"] * circuit_signal
        )
    else:
        total = w["model"] + w["circuit"]
        blended = (w["model"] * base_predictions + w["circuit"] * circuit_signal) / total

    blended = shrink_to_grid(blended, upcoming["GridPosition"])

    # Clip to the real field size (22 in 2026), not 20, see pipeline.py
    field_size = max(len(upcoming), int(upcoming["GridPosition"].max()))

    upcoming["Position"] = actual_position
    upcoming["Predicted"] = np.clip(blended, 1, field_size).round(2)

    # the same standings nudge live adds on top, from this season's races before this one
    form = compute_championship_form(history[history["Year"] == history["Year"].max()])
    return apply_championship_signal(upcoming, form, weight=CHAMPIONSHIP_WEIGHT)


def _score_team(team: dict, driver_pts: dict, constructor_pts: dict) -> float:
    """
    Actual points a proposed lineup would have scored.
    The 2x boost driver counts twice.
    """
    if not team:
        return 0.0

    total = sum(driver_pts.get(d["Abbreviation"], 0.0) for d in team["drivers"])

    boost = (team.get("boost_pick") or {}).get("Abbreviation")
    if boost:
        total += driver_pts.get(boost, 0.0)

    total += sum(constructor_pts.get(c["name"], 0.0) for c in team["constructors"])
    return round(total, 1)


def _graded_by_referee(team: dict, round_points: dict) -> float:
    """What a lineup really scored, the game's own points (src/official_points.py)."""
    if not team:
        return 0.0
    return team_points(
        [d["Abbreviation"] for d in team["drivers"]],
        [c["name"] for c in team["constructors"]],
        (team.get("boost_pick") or {}).get("Abbreviation"),
        round_points,
    )


def predicted_for_round(rnd: int, df_previous: pd.DataFrame, df_current: pd.DataFrame):
    """
    One round of the replay on its own: (race name, the walk forward predicted table,
    session used). Trained only on races before rnd, grid from the deadline session,
    the same steps run_backtest does per round. The table is None if no practice loads.
    The planner grade (scripts/planner_grade.py) uses this.
    """
    target_raw = df_current[df_current["RoundNumber"] == rnd].copy()
    race_name = target_raw["RaceName"].iloc[0]
    practice_df, session_used = deadline_grid(race_name)
    if practice_df is None:
        return race_name, None, None
    history_raw = pd.concat([df_previous, df_current[df_current["RoundNumber"] < rnd]], ignore_index=True)
    return race_name, _predict_race(history_raw, target_raw, race_name, practice_df), session_used


def _prices_for_round(round_number: int, fallback: dict, cache: dict) -> dict:
    if round_number in cache:
        return cache[round_number]
    try:
        p = fetch_prices(round_number)
        if not p.get("drivers"):
            raise ValueError("empty price feed")
    except Exception:
        p = fallback
    cache[round_number] = p
    return p


def run_backtest(
    fallback_prices: dict | None = None,
    use_practice: bool = True,
    use_dnf_risk: bool = False,
    dnf_weight: float = 1.0,
    official: dict[int, dict] | None = None,
) -> dict:
    """
    Replays every completed 2026 race and reports what the model would have scored.

    use_practice=True is the honest test: grid is estimated from FP3 pace exactly
    as production does, and the baseline is "pick by FP3 order", a strategy you
    could actually have played, since the fantasy deadline falls before qualifying.

    use_practice=False hands the model the real qualifying grid and benchmarks it
    against grid order. Both sides get information unavailable at the deadline, so
    treat it as an upper bound rather than a verdict.

    use_dnf_risk=True prices each driver's retirement probability into his expected
    points instead of assuming everyone finishes. The DNF model is refit on only
    the races before the one being graded, so this stays walk-forward. dnf_weight
    is how much of the expected penalty to charge; this defaults to the full 1.0
    here rather than to the shipped DNF_WEIGHT, because the point of the flag is
    to measure the effect rather than to reproduce production.

    official is the game's own points per round (load_official_points). When it's
    given, every score is the real one from the feed instead of our own version of the
    rules, and the round's prices come from the same saved feed. A round that isn't in
    it gets official_missing and no scores at all, never a 0.
    """
    df_previous = load_dataset(results_path(PREVIOUS_SEASON))
    df_current = load_dataset(results_path(SEASON))

    fallback_prices = fallback_prices or {"drivers": {}, "constructors": {}}
    price_cache: dict[int, dict] = {}

    # sprint results live in their own file, see src/fetch_results.py
    try:
        sprint_results = load_dataset(sprint_results_path())
    except Exception:
        sprint_results = None

    rounds = sorted(df_current["RoundNumber"].unique())
    races = []

    for rnd in rounds:
        if rnd <= MIN_HISTORY_ROUNDS:
            continue

        target_raw = df_current[df_current["RoundNumber"] == rnd].copy()
        race_name = target_raw["RaceName"].iloc[0]

        # Everything before this race, and nothing from it
        history_raw = pd.concat(
            [df_previous, df_current[df_current["RoundNumber"] < rnd]], ignore_index=True
        )

        official_round = official.get(int(rnd)) if official is not None else None
        if official_round and official_round.get("prices", {}).get("drivers"):
            prices = official_round["prices"]
        else:
            prices = _prices_for_round(int(rnd), fallback_prices, price_cache)
        if not prices.get("drivers"):
            continue

        practice_df = None
        session_used = None
        if use_practice:
            practice_df, session_used = deadline_grid(race_name)
            if practice_df is None:
                races.append({
                    "race_name": race_name, "round": int(rnd),
                    "error": "no practice data available",
                })
                continue

        try:
            predicted = _predict_race(history_raw, target_raw, race_name, practice_df)
        except Exception as e:
            races.append({"race_name": race_name, "round": int(rnd), "error": str(e)})
            continue

        if official is not None:
            # the referee: real points from the feed, or nothing if we don't have them
            if official_round is None:
                driver_pts = constructor_pts = None
            else:
                driver_pts = {a: v["points"] for a, v in official_round["drivers"].items()}
                constructor_pts = {c: v["points"] for c, v in official_round["constructors"].items()}
        else:
            sprint_raw = sprint_results[sprint_results["RoundNumber"] == rnd] if sprint_results is not None else None
            driver_pts = _actual_driver_points(target_raw, sprint_raw)
            constructor_pts = _actual_constructor_points(target_raw, sprint_raw)
        missing = official is not None and official_round is None

        def _grade(team):
            if missing:
                return None
            if official is not None:
                return _graded_by_referee(team, official_round)
            return _score_team(team, driver_pts, constructor_pts)

        def _actual(pts, name):
            return None if pts is None else round(pts.get(name, 0.0), 1)

        # Retirement risk, fit on history only so no future information leaks in.
        dnf_probs = None
        if use_dnf_risk:
            try:
                dnf_model = DNFModel.fit(history_raw)
                dnf_probs = dict(zip(
                    predicted["Abbreviation"],
                    dnf_model.predict(predicted["Abbreviation"],
                                      predicted["GridPosition"], race_name),
                ))
            except Exception:
                dnf_probs = None

        # expected constructor extras (pit stops mostly) from the official rounds before
        # this one. only used when USE_CONSTRUCTOR_EXTRAS is on, see src/fantasy.py
        extra_kw = ({"constructor_extras": constructor_extras(official, df_current, int(rnd))}
                    if official is not None else {})
        model_teams = build_budget_teams(predicted, race_name, prices, budget=100.0,
                                         dnf_probs=dnf_probs, dnf_weight=dnf_weight, **extra_kw)

        # Baseline: same optimiser, same information, no model. In practice mode
        # that means "pick by FP3 order", genuinely playable before the deadline.
        grid_table = predicted.copy()
        grid_table["Predicted"] = grid_table["GridPosition"].astype(float)
        baseline_teams = build_budget_teams(grid_table, race_name, prices, budget=100.0)

        model_scores = [_grade(t) for t in model_teams]
        baseline_score = _grade(baseline_teams[0]) if baseline_teams else (None if missing else 0.0)
        model_score = model_scores[0] if model_scores else (None if missing else 0.0)

        best_team = model_teams[0] if model_teams else None
        races.append({
            "race_name": race_name,
            "round": int(rnd),
            "session_used": session_used,
            "official_missing": missing,
            "model_score": model_score,
            "all_team_scores": model_scores,
            "best_of_three": None if missing else (max(model_scores) if model_scores else 0.0),
            "baseline_score": baseline_score,
            "delta": None if missing else round(model_score - baseline_score, 1),
            "drivers": [
                {
                    "Abbreviation": d["Abbreviation"],
                    "GridPosition": d["GridPosition"],
                    "Predicted": d["Predicted"],
                    "actual_points": _actual(driver_pts, d["Abbreviation"]),
                    "is_boost": d["Abbreviation"] == (best_team.get("boost_pick") or {}).get("Abbreviation"),
                }
                for d in (best_team["drivers"] if best_team else [])
            ],
            "constructors": [
                {"name": c["name"], "actual_points": _actual(constructor_pts, c["name"])}
                for c in (best_team["constructors"] if best_team else [])
            ],
        })

    # a round without official points has no score at all, so it can't count
    scored = [r for r in races if "error" not in r and not r.get("official_missing")]
    n = len(scored)
    summary = {
        "races_tested": n,
        "avg_model_score": round(sum(r["model_score"] for r in scored) / n, 1) if n else 0.0,
        "avg_baseline_score": round(sum(r["baseline_score"] for r in scored) / n, 1) if n else 0.0,
        "avg_best_of_three": round(sum(r["best_of_three"] for r in scored) / n, 1) if n else 0.0,
        "races_beating_baseline": sum(1 for r in scored if r["delta"] > 0),
        "total_model_score": round(sum(r["model_score"] for r in scored), 1),
        "total_baseline_score": round(sum(r["baseline_score"] for r in scored), 1),
    }
    summary["avg_delta"] = round(summary["avg_model_score"] - summary["avg_baseline_score"], 1)
    summary["mode"] = "practice" if use_practice else "actual-grid"

    return {"summary": summary, "races": races}
