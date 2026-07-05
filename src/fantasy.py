import pandas as pd
from itertools import combinations
import numpy as np

def calculate_gainer_score(
    midfield: pd.DataFrame,
    w_avg_position_change: float = 0.1,
    w_predicted: float = 0.1,
    w_confidence: float = 0.1,
    w_grid_gap: float = 0.4
) -> pd.DataFrame:
    midfield = midfield.copy()

    midfield["GridGap"] = midfield["GridPosition"] - midfield["Predicted"]

    midfield["GainerScore"] = (
        w_avg_position_change * midfield["AveragePositionChange"]
        - w_predicted * midfield["Predicted"]
        - w_confidence * midfield["Confidence"]
        + w_grid_gap * midfield["GridGap"]
    )

    return midfield

def get_safe_picks(race_predictions: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    return race_predictions.sort_values(by="Predicted").head(n)

def get_midfield_drivers(
        race_predictions: pd.DataFrame,
        lower_bound: int = 5,
        upper_bound: int = 12,
        confidence_threshold: float = 3.0,
        w_avg_position_change: float = 0.1,
        w_predicted: float = 0.1,
        w_confidence: float = 0.1,
        w_grid_gap: float = 0.4
) -> pd.DataFrame:
    midfield = race_predictions[
        (race_predictions["Predicted"] > lower_bound) &
        (race_predictions["Predicted"] <= upper_bound)
    ].copy()

    midfield = calculate_gainer_score(
        midfield,
        w_avg_position_change=w_avg_position_change,
        w_predicted=w_predicted,
        w_confidence=w_confidence,
        w_grid_gap=w_grid_gap
    )

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
        race_name: str,
        w_avg_position_change: float = 0.1,
        w_predicted: float = 0.1,
        w_confidence: float = 0.1,
        w_grid_gap: float = 0.4
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

    midfield = get_midfield_drivers(
        race_predictions,
        w_avg_position_change=w_avg_position_change,
        w_predicted=w_predicted,
        w_confidence=w_confidence,
        w_grid_gap=w_grid_gap
    )
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

def build_budget_team(
    fantasy_table: pd.DataFrame,
    race_name: str,
    prices: dict,
    budget: float = 100.0,
) -> dict:
    """
    Finds the optimal 5-driver + 2-constructor team within the $100M budget.

    Scores every valid combination and returns the one with the highest
    total FantasyValue. Constructor score is the average FantasyValue
    of their drivers in that race.

    Returns a dict with:
        drivers      -> list of driver dicts
        constructors -> list of constructor dicts
        total_cost   -> float
        budget_remaining -> float
        total_score  -> float
    """
    race_df = fantasy_table[fantasy_table["RaceName"] == race_name].copy()
    race_df = calculate_fantasy_score(race_df)

    race_df["GridGap"] = race_df["GridPosition"] - race_df["Predicted"]
    race_df = race_df.reset_index(drop=True)

    driver_prices = prices.get("drivers", {})
    constructor_prices = prices.get("constructors", {})

    race_df["Price"] = race_df["Abbreviation"].map(driver_prices)
    race_df = race_df.dropna(subset=["Price"])

    # Constructor score = average FantasyValue of their drivers this race
    constructor_scores = (
        race_df.groupby("TeamName")["FantasyValue"].mean().to_dict()
    )

    constructors = [
        {
            "name": team,
            "price": price,
            "score": round(constructor_scores.get(team, 0.0), 3),
        }
        for team, price in constructor_prices.items()
    ]

    drivers_list = race_df.to_dict("records")

    best_score = -np.inf
    best_team = None

    for driver_combo in combinations(drivers_list, 5):
        driver_cost = sum(d["Price"] for d in driver_combo)
        if driver_cost > budget:
            continue

        for constructor_combo in combinations(constructors, 2):
            constructor_cost = sum(c["price"] for c in constructor_combo)
            total_cost = driver_cost + constructor_cost

            if total_cost > budget:
                continue

            total_score = (
                sum(d["FantasyValue"] for d in driver_combo)
                + sum(c["score"] for c in constructor_combo)
            )

            if total_score > best_score:
                best_score = total_score
                best_team = {
                    "drivers": [
                        {
                            "Abbreviation": d["Abbreviation"],
                            "TeamName": d["TeamName"],
                            "GridPosition": int(d["GridPosition"]),
                            "Predicted": round(d["Predicted"], 1),
                            "FantasyValue": round(d["FantasyValue"], 3),
                            "Price": d["Price"],
                        }
                        for d in driver_combo
                    ],
                    "constructors": [
                        {
                            "name": c["name"],
                            "price": c["price"],
                            "score": c["score"],
                        }
                        for c in constructor_combo
                    ],
                    "total_cost": round(total_cost, 1),
                    "budget_remaining": round(budget - total_cost, 1),
                    "total_score": round(best_score, 3),
                }

    return best_team


def evaluate_fantasy_picks(
        fantasy_table: pd.DataFrame,
        w_avg_position_change: float = 0.1,
        w_predicted: float = 0.1,
        w_confidence: float = 0.1,
        w_grid_gap: float = 0.4
) -> pd.DataFrame:
    results = []
    races = fantasy_table["RaceName"].unique()

    for race in races:
        team = build_fantasy_team(
            fantasy_table,
            race,
            w_avg_position_change=w_avg_position_change,
            w_predicted=w_predicted,
            w_confidence=w_confidence,
            w_grid_gap=w_grid_gap
        )

        total_picks = len(team)
        top5_hits = (team["Position"] <= 5).sum()
        top10_hits = (team["Position"] <= 10).sum()
        avg_finish = team["Position"].mean()
        avg_position_gain = team["PositionChange"].mean()
        dnf_count = (team["Status"] != "Finished").sum() if "Status" in team.columns else 0

        results.append({
            "RaceName": race,
            "Total Picks": total_picks,
            "Top 5 Hits": int(top5_hits),
            "Top 5 Hit Rate": round(top5_hits / total_picks, 2),
            "Top 10 Hits": int(top10_hits),
            "Top 10 Hit Rate": round(top10_hits / total_picks, 2),
            "Avg Finish": round(avg_finish, 2),
            "Avg Position Gain": round(avg_position_gain, 2),
            "DNF Count": int(dnf_count)
        })

    return pd.DataFrame(results)

