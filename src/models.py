import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import numpy as np

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
