import pandas as pd
from src.data_loader import load_dataset
from src.features import build_features
from src.models import prepare_data, train_model, predict, build_fantasy_table


def run_pipeline() -> pd.DataFrame:
    df_2023 = load_dataset("data/processed/race_results_2023.csv")
    df_2024 = load_dataset("data/processed/race_results_2024.csv")
    df_2025 = load_dataset("data/processed/race_results_2025.csv")

    df_train = pd.concat([df_2023, df_2024], ignore_index=True)
    df_train = build_features(df_train)
    df_2025 = build_features(df_2025)

    X_train, y_train, X_test, y_test = prepare_data(df_train, df_2025)
    model = train_model(X_train, y_train)
    predictions = predict(model, X_test)
    fantasy_table = build_fantasy_table(df_2025, predictions)

    return fantasy_table
