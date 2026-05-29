import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import numpy as np
from itertools import product

def prepare_data(train_df: pd.DataFrame, test_df: pd.DataFrame):


    features =[
        "TeamName",
        "GridPosition",
        "PreviousPosition",
        "AveragePositionChange",
        "Consistency",
        "GridvsForm",
        "FormTrend",
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

def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> RandomForestRegressor:
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    # This function we just pass the train so we can test it into the model

    return model

def predict(model: RandomForestRegressor, X_test: pd.DataFrame) -> np.ndarray:
    return model.predict(X_test)

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

