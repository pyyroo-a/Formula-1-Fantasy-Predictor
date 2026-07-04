import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from src.data_loader import load_dataset
from src.features import build_features
from src.models import prepare_data, train_model, predict, build_fantasy_table


def build_trained_model() -> tuple[RandomForestRegressor, pd.DataFrame]:
    """Train on all historical + completed 2026 data. Returns model and full training df."""
    df_2024 = load_dataset("data/processed/race_results_2024.csv")
    df_2025 = load_dataset("data/processed/race_results_2025.csv")
    df_2026 = load_dataset("data/processed/race_results_2026.csv")

    df_train = pd.concat([df_2024, df_2025, df_2026], ignore_index=True)
    df_train = build_features(df_train)

    features = [
        "TeamName", "GridPosition", "PreviousPosition",
        "AveragePositionChange", "Consistency", "GridvsForm", "FormTrend", "Position"
    ]
    df_train = df_train.dropna(subset=features)

    X_train = pd.get_dummies(df_train[features].drop("Position", axis=1), columns=["TeamName"])
    y_train = df_train["Position"]

    model = train_model(X_train, y_train)

    return model, df_train, X_train.columns.tolist()


def run_pipeline() -> pd.DataFrame:
    """Returns fantasy table for all completed 2026 races (for the race selector)."""
    df_2024 = load_dataset("data/processed/race_results_2024.csv")
    df_2025 = load_dataset("data/processed/race_results_2025.csv")
    df_2026 = load_dataset("data/processed/race_results_2026.csv")

    df_train = pd.concat([df_2024, df_2025], ignore_index=True)
    df_train = build_features(df_train)
    df_2026 = build_features(df_2026)

    X_train, y_train, X_test, y_test = prepare_data(df_train, df_2026)
    model = train_model(X_train, y_train)
    predictions = predict(model, X_test)
    fantasy_table = build_fantasy_table(df_2026, predictions)

    return fantasy_table


def predict_upcoming_race(practice_df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a DataFrame of practice session data for the upcoming race
    (must have: Abbreviation, TeamName, GridPosition, RaceName)
    and returns a fantasy table prediction using historical form features.
    """
    df_2024 = load_dataset("data/processed/race_results_2024.csv")
    df_2025 = load_dataset("data/processed/race_results_2025.csv")
    df_2026 = load_dataset("data/processed/race_results_2026.csv")

    df_history = pd.concat([df_2024, df_2025, df_2026], ignore_index=True)
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

    X_train, y_train, X_test, _ = prepare_data(df_history, upcoming)
    model = train_model(X_train, y_train)
    predictions = predict(model, X_test)

    fantasy_table = build_fantasy_table(upcoming, predictions)

    return fantasy_table
