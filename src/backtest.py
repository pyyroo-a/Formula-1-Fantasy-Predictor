"""
Replays completed races to measure whether the model's team picks would
actually have scored well.

The rule that makes this honest: when backtesting race N, the model is trained
only on races before N. It never sees the race it is predicting.
"""

import numpy as np
import pandas as pd

from src.data_loader import load_dataset
from src.features import build_features
from src.models import prepare_data, train_model, predict, shrink_to_grid
from src.fantasy import calculate_fantasy_score, build_budget_teams, RACE_POINTS
from src.circuit_profiles import get_blend_weights
from src.fetch_prices import fetch_prices

MIN_HISTORY_ROUNDS = 2  # need some 2026 form before predictions mean anything


def _predict_race(history_raw: pd.DataFrame, target_raw: pd.DataFrame, race_name: str) -> pd.DataFrame:
    """
    Trains on history_raw only, then predicts finishing positions for target_raw.

    Mirrors predict_upcoming_race(), except there is no practice data for a past
    race — so the FP3-pace and teammate-gap terms are dropped and the remaining
    blend weights are renormalised.
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

    # Merge onto the raw target rows so drivers who DNF'd are still included.
    # build_features() drops non-finishers, and excluding them here would hide
    # every -20 the optimiser walked into.
    upcoming = target_raw.merge(latest_form, on="Abbreviation", how="left")

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
    sample_weight = np.where(history["Year"] == 2026, 5.0, 1.0)
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
    total = w["model"] + w["circuit"]
    blended = (w["model"] * base_predictions + w["circuit"] * circuit_signal) / total
    blended = shrink_to_grid(blended, upcoming["GridPosition"])

    # Clip to the real field size (22 in 2026), not 20 — see pipeline.py
    field_size = max(len(upcoming), int(upcoming["GridPosition"].max()))

    upcoming["Position"] = actual_position
    upcoming["Predicted"] = np.clip(blended, 1, field_size).round(2)
    return upcoming


def _actual_driver_points(target_raw: pd.DataFrame) -> dict[str, float]:
    """True F1 Fantasy points each driver scored, from the real result."""
    scored = target_raw.copy()
    scored = scored.drop(columns=["Predicted"], errors="ignore")  # force actual Position
    scored = calculate_fantasy_score(scored, scale_by_circuit=False)
    return dict(zip(scored["Abbreviation"], scored["FantasyValue"]))


def _actual_constructor_points(target_raw: pd.DataFrame) -> dict[str, float]:
    """
    True constructor points: both drivers' race+overtake points, plus the
    qualifying bonus (+3 both in Q3, +1 both in Q2).
    """
    out = {}
    for team, rows in target_raw.groupby("TeamName"):
        pts = 0.0
        for _, r in rows.iterrows():
            finished = r["Status"] in ("Finished", "Lapped")
            if finished and not pd.isna(r["Position"]):
                pos = int(r["Position"])
                pts += RACE_POINTS.get(pos, 0)
                pts += int(r["GridPosition"]) - pos
            else:
                pts -= 20

        grids = [g for g in rows["GridPosition"] if not pd.isna(g)]
        if len(grids) >= 2:
            if all(g <= 10 for g in grids):
                pts += 3
            elif all(g <= 15 for g in grids):
                pts += 1
        out[team] = pts
    return out


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


def run_backtest(fallback_prices: dict | None = None) -> dict:
    """
    Replays every completed 2026 race and reports what the model would have scored.

    Each race is compared against a grid-order baseline — the same optimiser fed
    qualifying position instead of model predictions. That isolates whether the
    model adds anything over simply picking the front of the grid.
    """
    df_2025 = load_dataset("data/processed/race_results_2025.csv")
    df_2026 = load_dataset("data/processed/race_results_2026.csv")

    fallback_prices = fallback_prices or {"drivers": {}, "constructors": {}}
    price_cache: dict[int, dict] = {}

    rounds = sorted(df_2026["RoundNumber"].unique())
    races = []

    for rnd in rounds:
        if rnd <= MIN_HISTORY_ROUNDS:
            continue

        target_raw = df_2026[df_2026["RoundNumber"] == rnd].copy()
        race_name = target_raw["RaceName"].iloc[0]

        # Everything before this race — and nothing from it
        history_raw = pd.concat(
            [df_2025, df_2026[df_2026["RoundNumber"] < rnd]], ignore_index=True
        )

        prices = _prices_for_round(int(rnd), fallback_prices, price_cache)
        if not prices.get("drivers"):
            continue

        try:
            predicted = _predict_race(history_raw, target_raw, race_name)
        except Exception as e:
            races.append({"race_name": race_name, "round": int(rnd), "error": str(e)})
            continue

        driver_pts = _actual_driver_points(target_raw)
        constructor_pts = _actual_constructor_points(target_raw)

        model_teams = build_budget_teams(predicted, race_name, prices, budget=100.0)

        # Baseline: same optimiser, but "prediction" = qualifying position
        grid_table = predicted.copy()
        grid_table["Predicted"] = grid_table["GridPosition"].astype(float)
        baseline_teams = build_budget_teams(grid_table, race_name, prices, budget=100.0)

        model_scores = [_score_team(t, driver_pts, constructor_pts) for t in model_teams]
        baseline_score = (
            _score_team(baseline_teams[0], driver_pts, constructor_pts)
            if baseline_teams else 0.0
        )

        best_team = model_teams[0] if model_teams else None
        races.append({
            "race_name": race_name,
            "round": int(rnd),
            "model_score": model_scores[0] if model_scores else 0.0,
            "all_team_scores": model_scores,
            "best_of_three": max(model_scores) if model_scores else 0.0,
            "baseline_score": baseline_score,
            "delta": round((model_scores[0] if model_scores else 0.0) - baseline_score, 1),
            "drivers": [
                {
                    "Abbreviation": d["Abbreviation"],
                    "GridPosition": d["GridPosition"],
                    "Predicted": d["Predicted"],
                    "actual_points": round(driver_pts.get(d["Abbreviation"], 0.0), 1),
                    "is_boost": d["Abbreviation"] == (best_team.get("boost_pick") or {}).get("Abbreviation"),
                }
                for d in (best_team["drivers"] if best_team else [])
            ],
            "constructors": [
                {"name": c["name"], "actual_points": round(constructor_pts.get(c["name"], 0.0), 1)}
                for c in (best_team["constructors"] if best_team else [])
            ],
        })

    scored = [r for r in races if "error" not in r]
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

    return {"summary": summary, "races": races}
