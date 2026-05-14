import pandas as pd

def calculate_gainer_score(midfield: pd.DataFrame) -> pd.DataFrame:
    midfield = midfield.copy()

    midfield["GridGap"] = midfield["GridPosition"] - midfield["Predicted"]

    midfield["GainerScore"] = (
    0.6 *  midfield["AveragePositionChange"]
    - 0.2 * midfield["Predicted"]
    - 0.1 * midfield["Confidence"]
    + 0.4 * midfield["GridGap"]
    )

    return midfield

def get_safe_picks(race_predictions: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    return race_predictions.sort_values(by="Predicted").head(n)

def get_midfield_drivers(
        race_predictions: pd.DataFrame,
        lower_bound: int = 5,
        upper_bound: int = 12,
        confidence_threshold: float = 3.0
) -> pd.DataFrame:
    midfield = race_predictions[
        (race_predictions["Predicted"] > lower_bound) &
        (race_predictions["Predicted"] <= upper_bound)
    ].copy()

    midfield = calculate_gainer_score(midfield)

    midfield = midfield[midfield["Confidence"] < confidence_threshold]

    return midfield

def get_position_gain_picks(midfield: pd.DataFrame) -> pd.DataFrame:
    stable_midfield = midfield.sort_values(
        by="GainerScore",
        ascending=False
    ).head(2)

    risky_pool = midfield[
        ~midfield["Abbreviation"].isin(stable_midfield["Abbreviation"])
    ]
    
    risky_pick = risky_pool.sort_values(
        by="AveragePositionChange",
        ascending=False
    ).head(1)

    return pd.concat([stable_midfield, risky_pick])

def build_fantasy_team(
        fantasy_table: pd.DataFrame,
        race_name: str
) -> pd.DataFrame:
    race_predictions = fantasy_table[
        fantasy_table["RaceName"] == race_name
    ].copy()

    race_predictions["GridGap"] = (
        race_predictions["GridPosition"] - race_predictions["Predicted"]
    )

    safe_picks = get_safe_picks(race_predictions)

    midfield = get_midfield_drivers(race_predictions)

    position_gain_picks = get_position_gain_picks(midfield)

    fantasy_team = pd.concat([
        safe_picks,
        position_gain_picks
    ]).drop_duplicates()

    return fantasy_team