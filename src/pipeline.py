import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from src.data_loader import load_dataset
from src.features import build_features
from src.models import prepare_data, train_model, predict, build_fantasy_table
from src.championship_form import compute_championship_form, apply_championship_signal


def build_trained_model() -> tuple[RandomForestRegressor, pd.DataFrame]:
    """Train on 2025 + 2026 data, with 2026 weighted 3x to reflect current car pace."""
    df_2025 = load_dataset("data/processed/race_results_2025.csv")
    df_2026 = load_dataset("data/processed/race_results_2026.csv")

    df_train = pd.concat([df_2025, df_2026], ignore_index=True)
    df_train = build_features(df_train)

    features = [
        "TeamName", "GridPosition", "PreviousPosition",
        "AveragePositionChange", "Consistency", "GridvsForm", "FormTrend", "Position"
    ]
    df_train = df_train.dropna(subset=features)

    sample_weight = np.where(df_train["Year"] == 2026, 3.0, 1.0)

    X_train = pd.get_dummies(df_train[features].drop("Position", axis=1), columns=["TeamName"])
    y_train = df_train["Position"]

    model = train_model(X_train, y_train, sample_weight=sample_weight)

    return model, df_train, X_train.columns.tolist()


def run_pipeline() -> pd.DataFrame:
    """Returns fantasy table for all completed 2026 races (for the race selector)."""
    df_2025 = load_dataset("data/processed/race_results_2025.csv")
    df_2026 = load_dataset("data/processed/race_results_2026.csv")

    df_train = df_2025.copy()
    df_train = build_features(df_train)
    df_2026 = build_features(df_2026)

    X_train, y_train, X_test, y_test = prepare_data(df_train, df_2026)
    model = train_model(X_train, y_train)
    predictions = predict(model, X_test)
    fantasy_table = build_fantasy_table(df_2026, predictions)

    # Compute 2026 championship standings from the completed race data
    # and use them to fine-tune predictions — drivers leading the title
    # get a small boost, backmarkers get a small penalty.
    form_df = compute_championship_form(df_2026)
    fantasy_table = apply_championship_signal(fantasy_table, form_df, weight=0.15)

    return fantasy_table


def predict_upcoming_race(practice_df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a DataFrame of practice session data for the upcoming race
    (must have: Abbreviation, TeamName, GridPosition, RaceName)
    and returns a fantasy table prediction using historical form features.
    """
    df_2025 = load_dataset("data/processed/race_results_2025.csv")
    df_2026 = load_dataset("data/processed/race_results_2026.csv")

    df_history = pd.concat([df_2025, df_2026], ignore_index=True)
    df_history = build_features(df_history)

    # Get the latest rolling features per driver from history
    latest_form = (
        df_history.sort_values(["Abbreviation", "Year", "RoundNumber"])
        .groupby("Abbreviation")
        .last()
        .reset_index()[["Abbreviation", "TeamName", "PreviousPosition",
                         "AveragePositionChange", "Consistency", "Rolling3Average"]]
    )

    upcoming = practice_df.merge(latest_form, on="Abbreviation", how="left", suffixes=("", "_hist"))

    # Fill team from practice data (more accurate for 2026 lineup)
    upcoming["TeamName"] = upcoming["TeamName"].fillna(upcoming.get("TeamName_hist", "Unknown"))
    upcoming["PreviousPosition"] = upcoming["PreviousPosition"].fillna(10.0)
    upcoming["AveragePositionChange"] = upcoming["AveragePositionChange"].fillna(0.0)
    upcoming["Consistency"] = upcoming["Consistency"].fillna(0.0)
    upcoming["Rolling3Average"] = upcoming["Rolling3Average"].fillna(10.0)

    upcoming["GridvsForm"] = upcoming["GridPosition"] - upcoming["Rolling3Average"]
    upcoming["FormTrend"] = upcoming["Rolling3Average"] - upcoming["PreviousPosition"]

    # Dummy position column so prepare_data works — not used in prediction
    upcoming["Position"] = 10.0
    upcoming["Status"] = "Finished"

    # Weight 2026 races 3x higher than 2025 so current car pace dominates
    sample_weight = np.where(df_history["Year"] == 2026, 3.0, 1.0)

    X_train, y_train, X_test, _ = prepare_data(df_history, upcoming)
    model = train_model(X_train, y_train, sample_weight=sample_weight)
    base_predictions = predict(model, X_test)

    fantasy_table = build_fantasy_table(upcoming, base_predictions)

    # --- Practice pace signal ---
    # Convert GapToPole (seconds) into a 1–20 position-scale estimate.
    # A driver on pole (gap=0) maps to P1; the slowest maps to P20.
    if "GapToPole" in upcoming.columns:
        max_gap = upcoming["GapToPole"].max()
        if max_gap > 0:
            practice_pace = 1 + (upcoming["GapToPole"].values / max_gap) * 19
        else:
            practice_pace = upcoming["GridPosition"].values.astype(float)
    else:
        practice_pace = upcoming["GridPosition"].values.astype(float)

    # Teammate gap adjustment: slower teammate gets a small penalty
    if "GapToTeammate" in upcoming.columns:
        max_team_gap = upcoming["GapToTeammate"].max()
        if max_team_gap > 0:
            teammate_penalty = (upcoming["GapToTeammate"].values / max_team_gap) * 3
        else:
            teammate_penalty = np.zeros(len(upcoming))
    else:
        teammate_penalty = np.zeros(len(upcoming))

    # --- Circuit history signal ---
    race_name = practice_df["RaceName"].iloc[0]
    circuit_history = (
        df_history[df_history["RaceName"] == race_name]
        .groupby("Abbreviation")["Position"]
        .mean()
    )
    circuit_avg = upcoming["Abbreviation"].map(circuit_history)
    circuit_signal = circuit_avg.fillna(pd.Series(base_predictions, index=upcoming.index)).values

    # Blend: 45% form model + 35% practice pace + 10% teammate gap + 10% circuit history
    blended = (
        0.45 * base_predictions
        + 0.35 * practice_pace
        + 0.10 * teammate_penalty
        + 0.10 * circuit_signal
    )
    blended = np.clip(blended, 1, 20)

    fantasy_table["Predicted"] = blended.round(2)

    # Apply championship standings signal on top of the blended prediction.
    # We use all historical + 2026 data so the standings reflect the full season so far.
    form_df = compute_championship_form(df_history[df_history["Year"] == df_history["Year"].max()])
    fantasy_table = apply_championship_signal(fantasy_table, form_df, weight=0.15)

    # Compute scoring columns from blended predictions
    fantasy_table["PositionChange"] = fantasy_table["GridPosition"] - fantasy_table["Predicted"]
    fantasy_table["Top10Finish"] = (fantasy_table["Predicted"] <= 10).astype(int)
    fantasy_table["Top5Finish"] = (fantasy_table["Predicted"] <= 5).astype(int)
    fantasy_table["DNF"] = 0

    return fantasy_table
