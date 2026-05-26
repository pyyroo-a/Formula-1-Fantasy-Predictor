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

def calculate_fantasy_score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["FantasyValue"] = (
        0.5 * df["PositionChange"] +
        0.4 * df["Top10Finish"] +
        0.3 * df["Top5Finish"] -
        0.2 * df["DNF"]
    )

    return df

def assign_pick_categories(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    cutoffs = df["FantasyValue"].quantile([0.25,0.75])
    low = cutoffs[0.25]
    high = cutoffs[0.75]

    def categorize(value):
        if value >= high:
            return "Value"
        
        elif value <= low:
            return "Risk"
        
        else:
            return "Avoid"
        

    df["PickCategory"] = df["FantasyValue"].apply(categorize) 
    # Above code goes through every row in the DF and then passes it into categorize to assign a category value
    # This is based on the drivers fantasy value and then compared with the position 

    return df

def build_fantasy_team(
        fantasy_table: pd.DataFrame,
        race_name: str
) -> pd.DataFrame:
    race_predictions = fantasy_table[
        fantasy_table["RaceName"] == race_name
    ].copy()

    race_predictions = calculate_fantasy_score(race_predictions)

    race_predictions["GridGap"] = (
        race_predictions["GridPosition"] - race_predictions["Predicted"]
    )

    safe_picks = get_safe_picks(race_predictions)
    safe_picks["PickCategory"] = "Safe"

    midfield = get_midfield_drivers(race_predictions)
    midfield = assign_pick_categories(midfield)

    position_gain_picks = get_position_gain_picks(midfield)

    fantasy_team = pd.concat([
        safe_picks,
        position_gain_picks
    ]).drop_duplicates()

    return fantasy_team

def generate_explanations(team: pd.DataFrame) -> pd.DataFrame:
    team = team.copy()

    def explain(row):
        grid = int(row["GridPosition"])
        predicted = round(row["Predicted"])
        avg_change = round(row["AveragePositionChange"], 1)
        gap = round(row["GridGap"], 1)

        if row["PickCategory"] == "Safe":
            return f"Safe Pick: starts P{grid}, predicted P{predicted}, consistent top finisher"
        
        elif row["PickCategory"] == "Value":
            return f"Value Pick: starts P{grid}, predicted P{predicted}, averages {avg_change} position gains — strong upside"
        
        elif row["PickCategory"] == "Risk":
            return f"Risk Pick: starts p{grid}, predicted P{predicted}, inconsistent but {gap} positions of potential upside"

        else:
            return f"Avoid: starts P{grid}, predicted P{predicted}, low position gain history averaging {avg_change}"
        
    team["Explanation"] = team.apply(explain, axis=1)

    return team

