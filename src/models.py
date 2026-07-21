import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error
import numpy as np
from itertools import product

def prepare_data(train_df: pd.DataFrame, test_df: pd.DataFrame):


    features = [
        "TeamName",
        "GridPosition",
        "PreviousPosition",
        "AveragePositionChange",
        "Consistency",
        "GridvsForm",
        "FormTrend",
        "WinRate",
        "PodiumRate",
        "TeamAvgPosition",
        "Position"
    ]

    train = train_df[features].copy()
    test = test_df[features].copy()

    combined = pd.concat([train, test], ignore_index=True)
    combined = pd.get_dummies(combined, columns=["TeamName"])

    train_encoded = combined.iloc[:len(train)]
    test_encoded = combined.iloc[len(train):]

    X_train = train_encoded.drop("Position", axis=1)
    y_train = train_encoded["Position"]

    X_test = test_encoded.drop("Position", axis=1)
    y_test = test_encoded["Position"]

    # This is basically the logic we used in the notebooks which we are applying here
    return X_train, y_train, X_test, y_test

def train_model(X_train: pd.DataFrame, y_train: pd.Series, sample_weight=None) -> XGBRegressor:
    model = XGBRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train, sample_weight=sample_weight)
    return model

def predict(model: XGBRegressor, X_test: pd.DataFrame) -> np.ndarray:
    return model.predict(X_test)


# How far a predicted position is allowed to stray from the estimated grid.
# 1.0 = trust the model fully, 0.0 = use the grid estimate as-is.
#
# Currently 0.0 — the model's adjustments were measured to be net harmful.
#
# Faithful backtest (run_backtest(use_practice=True), 8 races of 2026), where
# both sides get FP3-estimated grid and the same optimiser:
#     model 98.5/race vs "pick by FP3 order" 113.5/race, winning 0 of 8.
# Handing the model the real qualifying grid instead showed the same direction:
#     1.0 -> -35.9/race, 0.6 -> -22.9, 0.4 -> -12.6, 0.0 -> exactly baseline.
#
# Likely cause: train/serve skew. The model is trained with GridPosition = exact
# qualifying grid, but served GridPosition = practice pace order, which carries
# ~2.4 places of error. It amplifies that noise rather than correcting it.
#
# Raise this above 0.0 only when a backtest run shows the model beating the
# FP3-order baseline. See docs/MODEL.md.
SHRINK_TO_GRID = 0.0


def shrink_to_grid(predicted, grid, k: float = SHRINK_TO_GRID):
    """
    Pulls predicted finishing positions back toward the starting grid.

    The model routinely forecast large climbs (e.g. P14 -> P5.6) that didn't
    happen, which biased team selection toward midfield runners. Grid position
    is a strong predictor in F1, so shrinking toward it is a regression-to-mean
    correction on the model's most speculative calls.
    """
    grid = np.asarray(grid, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return grid + k * (predicted - grid)

def evaluate_model(y_test: pd.Series, predictions: np.ndarray) -> float:
    mean_error = mean_absolute_error(y_test, predictions)
    print(f"Mean Absolute Error: {mean_error:.2f}")

    return mean_error

def build_fantasy_table(test_df: pd.DataFrame, predictions: np.ndarray) -> pd.DataFrame:
    fantasy_table = test_df.copy()

    fantasy_table["Predicted"] = predictions.round(2)
    fantasy_table["PredictedRounded"] = predictions.round().astype(int)

    # We need confidence because it gives the accuracy that we need for fantasy predictions
    # This is something we get before the race which is what we need for predicting which we need for fantasy
    fantasy_table["Confidence"] = (
        abs(fantasy_table["Predicted"] - fantasy_table["GridPosition"])
    ).round(2)

    return fantasy_table

def tune_gainer_weights(fantasy_table: pd.DataFrame) -> dict:
    positive_weights = np.arange(0.1, 1.1, 0.1)
    negative_weights = np.arange(0.1, 0.6, 0.1)

    best_weights = None
    best_score = -np.inf

    races = fantasy_table["RaceName"].unique()

    for w1, w2, w3, w4 in product(positive_weights, negative_weights, negative_weights, positive_weights):
        total_position_gain = 0
        race_count = 0

        for race in races:
            race_df = fantasy_table[fantasy_table["RaceName"] == race].copy()

            midfield = race_df[
                (race_df["Predicted"] > 5) &
                (race_df["Predicted"] <= 12) 
            ].copy()

            if midfield.empty:
                continue

            midfield["GridGap"] = midfield["GridPosition"] - midfield["Predicted"]

            midfield["GainerScore"] = (
                w1 * midfield["AveragePositionChange"] -
                w2 * midfield["Predicted"] -
                w3 * midfield["Confidence"] +
                w4 * midfield["GridGap"]
            )

            top_picks = midfield.sort_values(by="GainerScore", ascending=False).head(3)
            total_position_gain += top_picks["PositionChange"].mean()
            race_count += 1

            if race_count == 0:
                continue

            avg_gain = total_position_gain / race_count

            if avg_gain > best_score:
                best_score = avg_gain
                best_weights = {
                    "avg_position_change": round(w1, 1),
                    "predicted": round(w2, 1),
                    "confidence": round(w3, 1),
                    "grid_gap": round(w4, 1),
                    "avg_position_gain": round(avg_gain, 3)
                }
    
    return best_weights

