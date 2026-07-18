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

def qualifying_score(grid_pos: float) -> float:
    """
    Points contribution from qualifying performance.
    Q3 (P1-10) = bonus, Q2 (P11-15) = small bonus, Q1 (P16+) = penalty.
    Scaled to be balanced with the race scoring components.
    """
    if grid_pos <= 10:
        return 1.5   # Made Q3
    elif grid_pos <= 15:
        return 0.5   # Made Q2
    else:
        return -0.5  # Knocked out in Q1


def calculate_fantasy_score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["QualifyingScore"] = df["GridPosition"].apply(qualifying_score)

    df["FantasyValue"] = (
        0.5 * df["PositionChange"] +
        0.4 * df["Top10Finish"] +
        0.3 * df["Top5Finish"] -
        0.2 * df["DNF"] +
        df["QualifyingScore"]
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

def pick_boost_driver(drivers: list) -> dict:
    """
    Recommends which driver to give the 2x points boost to.

    Scoring: FantasyValue is the main factor (highest expected score = best doubling target).
    A small safety bonus is added for drivers starting from the top 6 — they have less
    DNF risk, so the double is less likely to be wasted.
    """
    # Never waste the 2x on a Q1 driver — only consider Q3 qualifiers (P1-10).
    # Fall back to the full list only if no Q3 drivers are in the team.
    q3_drivers = [d for d in drivers if d["GridPosition"] <= 10]
    candidates = q3_drivers if q3_drivers else drivers

    scored = []
    for d in candidates:
        grid = d["GridPosition"]
        predicted = d["Predicted"]
        fv = d["FantasyValue"]

        # Safety bonus: rewards starting near the front (max 0.5 bonus at P1, 0 at P6+)
        safety = max(0.0, (6 - grid) / 6) * 0.5

        scored.append({**d, "_boost_score": fv + safety})

    scored.sort(key=lambda x: x["_boost_score"], reverse=True)
    pick = scored[0]

    grid = pick["GridPosition"]
    predicted = round(pick["Predicted"])
    gain = round(grid - pick["Predicted"], 1)

    if grid <= 3:
        reason = f"Starting P{grid} (Q3), predicted P{predicted} — front row, qualifying points already banked, safest 2x"
    elif grid <= 10:
        reason = f"Starting P{grid} (Q3), predicted P{predicted} — made Q3 so qualifying points secured, good 2x candidate"
    elif gain >= 3:
        reason = f"Starting P{grid}, predicted P{predicted} — no Q3 drivers in team, best available with +{gain} position gain expected"
    else:
        reason = f"Predicted P{predicted} — highest expected score available for the 2x boost"

    alternatives = [s["Abbreviation"] for s in scored[1:3]]

    return {
        "Abbreviation": pick["Abbreviation"],
        "TeamName": pick["TeamName"],
        "GridPosition": grid,
        "Predicted": pick["Predicted"],
        "FantasyValue": pick["FantasyValue"],
        "reason": reason,
        "alternatives": alternatives,
    }


def build_budget_team(
    fantasy_table: pd.DataFrame,
    race_name: str,
    prices: dict,
    budget: float = 100.0,
    min_safe: int = 1,
) -> dict:
    race_df = fantasy_table[fantasy_table["RaceName"] == race_name].copy()
    race_df = calculate_fantasy_score(race_df)

    race_df["GridGap"] = race_df["GridPosition"] - race_df["Predicted"]
    race_df = race_df.reset_index(drop=True)

    driver_prices = prices.get("drivers", {})
    constructor_prices = prices.get("constructors", {})

    race_df["Price"] = race_df["Abbreviation"].map(driver_prices)
    race_df = race_df.dropna(subset=["Price"])

    # Safe = top 3 predicted finishers (lowest Predicted value)
    safe_abbrevs = set(race_df.nsmallest(3, "Predicted")["Abbreviation"].tolist())

    # Assign pick category so we can tag results and filter avoid-tier
    avoid_threshold = race_df["FantasyValue"].quantile(0.25)
    value_threshold = race_df["FantasyValue"].quantile(0.75)

    def _category(row):
        if row["Abbreviation"] in safe_abbrevs:
            return "Safe"
        if row["FantasyValue"] >= value_threshold:
            return "Value"
        if row["FantasyValue"] <= avoid_threshold:
            return "Avoid"
        return "Risk"

    race_df["PickCategory"] = race_df.apply(_category, axis=1)

    # Remove avoid-tier drivers from the candidate pool
    race_df = race_df[race_df["PickCategory"] != "Avoid"]

    # Constructor score = sum of both drivers' FantasyValue — you get points from both cars
    constructor_scores = race_df.groupby("TeamName")["FantasyValue"].sum().to_dict()

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
        # Enforce at least min_safe safe drivers in every team
        safe_count = sum(1 for d in driver_combo if d["Abbreviation"] in safe_abbrevs)
        if safe_count < min_safe:
            continue

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
                            "PickCategory": d["PickCategory"],
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
                    "boost_pick": None,  # filled in after the loop
                }

    if best_team:
        best_team["boost_pick"] = pick_boost_driver(best_team["drivers"])

    return best_team


def get_race_pool(
    fantasy_table: pd.DataFrame,
    race_name: str,
    prices: dict,
) -> dict:
    """Returns all drivers + constructors for a race with prices and categories — used by the manual team builder."""
    race_df = fantasy_table[fantasy_table["RaceName"] == race_name].copy()
    race_df = calculate_fantasy_score(race_df)
    race_df["GridGap"] = race_df["GridPosition"] - race_df["Predicted"]
    race_df = race_df.reset_index(drop=True)

    driver_prices = prices.get("drivers", {})
    constructor_prices = prices.get("constructors", {})

    race_df["Price"] = race_df["Abbreviation"].map(driver_prices)
    race_df = race_df.dropna(subset=["Price"])

    safe_abbrevs = set(race_df.nsmallest(3, "Predicted")["Abbreviation"].tolist())
    avoid_threshold = race_df["FantasyValue"].quantile(0.25)
    value_threshold = race_df["FantasyValue"].quantile(0.75)

    def _category(row):
        if row["Abbreviation"] in safe_abbrevs:
            return "Safe"
        if row["FantasyValue"] >= value_threshold:
            return "Value"
        if row["FantasyValue"] <= avoid_threshold:
            return "Avoid"
        return "Risk"

    race_df["PickCategory"] = race_df.apply(_category, axis=1)

    # Constructor score = sum of both drivers' FantasyValue — you get points from both cars
    constructor_scores = race_df.groupby("TeamName")["FantasyValue"].sum().to_dict()

    drivers = [
        {
            "Abbreviation": d["Abbreviation"],
            "TeamName": d["TeamName"],
            "GridPosition": int(d["GridPosition"]),
            "Predicted": round(d["Predicted"], 1),
            "FantasyValue": round(d["FantasyValue"], 3),
            "Price": d["Price"],
            "PickCategory": d["PickCategory"],
        }
        for d in race_df.sort_values("Predicted").to_dict("records")
    ]

    constructors = sorted(
        [
            {"name": t, "price": p, "score": round(constructor_scores.get(t, 0.0), 3)}
            for t, p in constructor_prices.items()
        ],
        key=lambda c: -c["score"],
    )

    return {"drivers": drivers, "constructors": constructors}


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

