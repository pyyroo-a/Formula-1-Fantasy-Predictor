import pandas as pd
from itertools import combinations
import numpy as np
from src.circuit_profiles import get_circuit_profile, overtaking_scale, quali_scale
from src.fetch_practice import is_sprint_weekend

# Real F1 Fantasy points scales
RACE_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
QUALI_POINTS = {1: 10, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}

# A sprint weekend scores a second time, on the Saturday sprint. Only the top 8
# score, places gained or lost count the same as the race, and a retirement costs
# -10 instead of -20. There are no sprint qualifying points, because the fantasy
# deadline falls after sprint qualifying, so you already know that result.
#
# Note: a disqualification is meant to be -20, but our data collapses every
# non-finish into "DNF", so a DQ is treated as a retirement here. It is rare.
SPRINT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
SPRINT_DNF_PENALTY = -10

# Should a FORECAST add expected sprint points on a sprint weekend? Measured, not
# guessed. Backtest over the 4 sprint weekends of 2026 (points per race):
#     baseline (FP1 input, no sprint points)      113.0
#     + sprint points only                        113.0   (changed no picks at all)
#     + sprint quali input only                   143.2
#     + both                                      135.8   (Canada 150 -> 120)
# So it does nothing alone and makes things worse alongside the good input. Same
# shape as DNF_WEIGHT: it pumps up drivers already predicted in the top 8, which
# pushes the optimiser off the cheap picks it earns its points from.
# The real sprint points still count in the TRUTH, see sprint_score.
PREDICT_SPRINT_POINTS = False


def sprint_score(grid_position, position, status) -> float:
    """Fantasy points one driver took from a sprint: finishing points plus places gained."""
    if status not in ("Finished", "Lapped") or pd.isna(position):
        return float(SPRINT_DNF_PENALTY)
    pos = int(position)
    points = SPRINT_POINTS.get(pos, 0)
    if not pd.isna(grid_position):
        # sprint grid comes from sprint qualifying, same +1 / -1 per place as the race
        points += int(grid_position) - pos
    return float(points)

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

# ---- the game's real rules, each behind a switch (project 2) ----------------------
#
# Checked against the real game on 2026-10-27, our forecast had three rules wrong. Each
# fix is a switch that starts OFF and only gets turned on if it scores more REAL points
# on the scorecard (scripts/scorecard.py), same idea as DNF_WEIGHT below. They're read
# every time they're used, so the scorecard can flip them for a replay.

# Qualifying: the game gives P1 to P10 +10 down to +1 and P11 to P20 nothing. The -5 is
# only for not setting a time, which we can't predict. We used to give -5 to P16+.
#
# Measured 2026-10-28, scorecard replay of R3 to R18 (16 races), official points:
#     off (what ships)    187.5 pts/race
#     on                  175.3 pts/race   (-12.2, better on 5, worse on 9)
#     on + real bonus     176.8 pts/race   (-10.8)
# The right rule scores worse. Without the -5 the back row costs nothing to own, so
# the optimiser fills up on cheap P16+ drivers: 24 of 80 picks came from P16+ with it
# on, 8 of 80 with it off (Bahrain 212 -> 112, it took Bottas from P21 and he DNF'd).
# The P20 clip below makes those same drivers look even better.
REAL_QUALI_RULES = False

# Constructor qualifying bonus: the game gives -1 neither car in Q2, +1 one in Q2, +3
# both in Q2, +5 one in Q3, +10 both in Q3. We only ever gave +1 / +3.
#
# Measured 2026-10-28, same replay:
#     off   187.5 pts/race
#     on    194.3 pts/race   (+6.8, better on 1, worse on 0)
# Only ONE race picked a different team (Monza, 147 -> 256), the other 15 were the
# same team. So it's +6.8 from a single race, thin evidence.
REAL_CONSTRUCTOR_QUALI_BONUS = False

# The championship nudge (src/championship_form.py) clipped every prediction to P20, but
# 2026 has 22 cars, so a P22 starter got "predicted" P20 and a made up +2 overtake bonus.
# The locked teams picked a P22 driver on 4 of 6 weekends. On = clip to the real field.
#
# Measured 2026-10-28, same replay:
#     off   187.5 pts/race
#     on    200.4 pts/race   (+12.9, better on 5, worse on 3, same team on 8)
# All three switches on together: 154.4 pts/race (-33.1, worse on 13 of 16).
CLIP_TO_REAL_FIELD = False

# Every page should add a constructor up the same way: both drivers' points, Avoid or
# not, plus the qualifying bonus. Off = the old quirks, the team builders drop Avoid
# drivers before adding up their constructor and the pool (Manual Team, chips) skips
# the bonus. See _constructor_scores.
#
# Measured 2026-10-28, scorecard replay of R3 to R18 (16 races), official points:
#     off (what ships)   187.5 pts/race
#     on                 190.3 pts/race   (+2.8, better on 1, worse on 2, same team on 13)
# Basically a wash on points (Monza 147 -> 256, Bahrain 212 -> 149). Its real value is
# that the 3 teams, Manual Team and the chips would all add a constructor up the same way.
FIX_CONSTRUCTOR_QUIRKS = False

# Add each constructor's expected extras (mostly pit stop points, see
# src/constructor_extras.py) to its forecast. The caller passes them in, {} if it
# doesn't have them.
#
# Measured 2026-10-28, same replay:
#     off   187.5 pts/race
#     on    201.6 pts/race   (+14.1, better on 4, worse on 1, same team on 11)
# Every switch on together (all five): 155.5 pts/race (-32.0, worse on 12 of 16), the
# real quali rule drags it down, see REAL_QUALI_RULES.
# Only the replay passes extras in so far. Live (snapshot, API) doesn't yet.
USE_CONSTRUCTOR_EXTRAS = False


def qualifying_score(grid_pos: float) -> float:
    pos = int(round(grid_pos))
    if pos <= 10:
        return QUALI_POINTS.get(pos, 1)   # Q3: +10 down to +1
    elif pos <= 15 or REAL_QUALI_RULES:
        return 0                           # Q2 but not Q3: no points (P11 to P20 in the real game)
    else:
        return -5                          # Q1 knockout: -5, the old rule


# How much of a driver's expected retirement cost to charge against his predicted
# score. 0.0 means "show the risk, do not let it move the picks".
#
# Measured, not chosen. run_backtest(use_practice=True) over 10 races of 2026:
#     weight 0.0  -> 113.9 pts/race   (unchanged behaviour)
#     weight 1.0  ->  87.0 pts/race   (-26.9, worse on 5 of 10 races)
# Charging the full expected penalty pushes the optimiser off cheap deep-field
# drivers, which is exactly where the budget solver earns its points. The risk
# estimate itself is sound (see src/dnf.py, it beats a flat rate on 11 of 12
# races), it is using it as a points deduction that fails.
DNF_WEIGHT = 0.0


def calculate_fantasy_score(
    df: pd.DataFrame,
    race_name: str | None = None,
    scale_by_circuit: bool = True,
    dnf_probs: dict | None = None,
    dnf_weight: float = DNF_WEIGHT,
) -> pd.DataFrame:
    """
    Computes real F1 Fantasy points per driver.

    scale_by_circuit weights the overtake/qualifying components by how hard the
    circuit is to overtake at. That is a *prediction* device, it tilts picks
    toward qualifiers at Monaco and climbers at Spa. Pass False to score an
    actual result, where the game's true unscaled points are what count.

    dnf_probs maps driver abbreviation -> P(does not finish), from src/dnf.py.
    When supplied, the -20 retirement penalty becomes an EXPECTED penalty
    (-20 * p) instead of an all-or-nothing one. This only makes sense for a race
    that has not happened yet, where every driver is otherwise assumed to finish
    and the risky picks therefore look exactly as safe as the reliable ones.
    Leave it as None to score a real result, where the retirements are known.

    dnf_weight controls how much of that expected penalty is actually charged.
    At 0.0 the probabilities are attached to the output for display but change no
    score, which is the shipped default, see DNF_WEIGHT for why.
    """
    df = df.copy()

    if scale_by_circuit and race_name:
        profile = get_circuit_profile(race_name)
        ot_scale = overtaking_scale(profile["overtaking"])   # Brazil 1.8x, Monaco 0.2x
        q_scale  = quali_scale(profile["overtaking"])        # Monaco 1.9x, Brazil 1.1x
    else:
        ot_scale = 1.0
        q_scale = 1.0

    # Use predicted position for upcoming races, actual finish for historical
    pos_col = "Predicted" if "Predicted" in df.columns else "Position"
    pos = df[pos_col].round().clip(1, 20).astype(int)

    # Championship points for finishing position (P1=25 ... P10=1, P11+=0)
    df["RacePoints"] = pos.map(RACE_POINTS).fillna(0)

    # Net overtake/loss scaled by circuit overtaking rating
    # Brazil/Spa: more expected gains → higher weight on position changers
    # Monaco: almost zero passes → devalue this component
    raw_overtake = (df["GridPosition"] - df[pos_col]).round().astype(int)
    df["OvertakeBonus"] = (raw_overtake * ot_scale).round(1)

    # Qualifying score scaled by how much qualifying matters at this circuit
    # Monaco: 1.9x because grid position = finishing position
    # Brazil: 1.1x because you can always overtake
    df["QualifyingScore"] = df["GridPosition"].apply(qualifying_score) * q_scale

    # DNF: -20.
    if dnf_probs is not None:
        # Forward-looking: nobody has retired yet. The probability is always
        # attached so it can be displayed, but it is only charged against the
        # score to the extent of dnf_weight.
        df["DNFProb"] = df["Abbreviation"].map(dnf_probs).fillna(0.0).astype(float)
        df["DNFPenalty"] = (df["DNFProb"] * -20 * dnf_weight).round(2)
    elif "Status" in df.columns:
        # Backward-looking: the result is known, so the penalty is all or nothing.
        dnf_mask = ~df["Status"].isin(["Finished", "Lapped"])
        df["DNFPenalty"] = np.where(dnf_mask, -20, 0)
    else:
        df["DNFPenalty"] = df.get("DNF", pd.Series(0, index=df.index)) * -20

    # FL (+10) and DOTD (+10) excluded, cannot predict reliably pre-race
    df["FantasyValue"] = (
        df["RacePoints"] +
        df["OvertakeBonus"] +
        df["QualifyingScore"] +
        df["DNFPenalty"]
    )

    # A sprint weekend pays out twice, so a driver is worth more there than the
    # same driver at a normal weekend. We only add this when scoring a FORECAST:
    # when scoring a real result the sprint points come from the actual sprint
    # (see sprint_score), and adding them here too would double count.
    #
    # We don't add places gained in the sprint, because our predicted order IS the
    # sprint grid estimate, so the predicted gain is zero for everyone anyway.
    if PREDICT_SPRINT_POINTS and pos_col == "Predicted" and race_name and is_sprint_weekend(race_name):
        df["SprintPoints"] = pos.map(SPRINT_POINTS).fillna(0).astype(float)
        df["FantasyValue"] = df["FantasyValue"] + df["SprintPoints"]

    # Keep PositionChange as alias for backward compat
    df["PositionChange"] = raw_overtake

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

    race_predictions = calculate_fantasy_score(race_predictions, race_name=race_name)

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
            return f"Value Pick: starts P{grid}, predicted P{predicted}, averages {avg_change} position gains, strong upside"
        
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
    A small safety bonus is added for drivers starting from the top 6, they have less
    DNF risk, so the double is less likely to be wasted.
    """
    # Never waste the 2x on a Q1 driver, only consider Q3 qualifiers (P1-10).
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
        reason = f"Starting P{grid} (Q3), predicted P{predicted}: front row, qualifying points already banked, safest 2x"
    elif grid <= 10:
        reason = f"Starting P{grid} (Q3), predicted P{predicted}: made Q3 so qualifying points secured, good 2x candidate"
    elif gain >= 3:
        reason = f"Starting P{grid}, predicted P{predicted}: no Q3 drivers in team, best available with +{gain} position gain expected"
    else:
        reason = f"Predicted P{predicted}, highest expected score available for the 2x boost"

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


def _priced_race_table(
    fantasy_table: pd.DataFrame,
    race_name: str,
    prices: dict,
    dnf_probs: dict | None = None,
    dnf_weight: float = DNF_WEIGHT,
) -> tuple[pd.DataFrame, set[str]]:
    """
    The race's drivers scored, priced and sorted into pick categories. The team
    builders and the pool all start from this, so there's only one copy of it.

    Returns (race_df, safe_abbrevs). Avoid drivers are still in race_df, each
    caller decides what to do with them.
    """
    race_df = fantasy_table[fantasy_table["RaceName"] == race_name].copy()
    race_df = calculate_fantasy_score(race_df, race_name=race_name,
                                      dnf_probs=dnf_probs, dnf_weight=dnf_weight)
    race_df["GridGap"] = race_df["GridPosition"] - race_df["Predicted"]
    race_df = race_df.reset_index(drop=True)

    race_df["Price"] = race_df["Abbreviation"].map(prices.get("drivers", {}))
    race_df = race_df.dropna(subset=["Price"])

    # Safe = top 3 predicted finishers (lowest Predicted value)
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
    return race_df, safe_abbrevs


def _real_constructor_quali_bonus(grids: list) -> int:
    """The game's constructor qualifying bonus from where its two cars start."""
    in_q3 = sum(1 for g in grids if g <= 10)
    in_q2 = sum(1 for g in grids if g <= 15)
    if in_q3 == 2:
        return 10
    if in_q3 == 1:
        return 5
    if in_q2 == 2:
        return 3
    if in_q2 == 1:
        return 1
    return -1


def _constructor_scores(
    race_df: pd.DataFrame,
    constructor_prices: dict,
    *,
    drop_avoid: bool,
    with_bonus: bool,
    extras: dict | None = None,
) -> dict[str, float]:
    """
    Constructor score = sum of both drivers' FantasyValue, since you get points from
    both cars. With with_bonus, plus the Q2/Q3 bonus (+1 if both cars reach Q2, +3 if
    both reach Q3) and a small top team bonus.

    The two flags are there because the callers don't agree, and the cleanup kept
    that on purpose so no prediction moved. Project 2 sorts it out with measurement:
      * the team builders use drop_avoid=True, so an Avoid driver's points vanish
        from his constructor (US GP: Cadillac -3.7 on Bottas alone, both cars -8.8)
      * the pool uses with_bonus=False, so the chip check sees different constructor
        scores than the team builder does
    FIX_CONSTRUCTOR_QUIRKS overrides both flags so everyone adds up the same way.

    extras is each team's expected pit stop (and other) points, only added with
    USE_CONSTRUCTOR_EXTRAS on.
    """
    if FIX_CONSTRUCTOR_QUIRKS:
        drop_avoid, with_bonus = False, True
    extra = (extras or {}) if USE_CONSTRUCTOR_EXTRAS else {}

    if drop_avoid:
        race_df = race_df[race_df["PickCategory"] != "Avoid"]

    sums = race_df.groupby("TeamName")["FantasyValue"].sum().to_dict()
    if not with_bonus:
        return {team: round(sums.get(team, 0.0) + extra.get(team, 0.0), 3) for team in constructor_prices}

    team_avg_pos = (
        race_df.groupby("TeamName")["TeamAvgPosition"].mean().to_dict()
        if "TeamAvgPosition" in race_df.columns else {}
    )
    grids_by_team = race_df.groupby("TeamName")["GridPosition"].apply(list).to_dict()

    def _bonus(team):
        avg = team_avg_pos.get(team, 10.0)
        top_team = 1.5 if avg <= 4 else (0.5 if avg <= 7 else 0.0)

        grids = grids_by_team.get(team, [])
        if len(grids) >= 2 and REAL_CONSTRUCTOR_QUALI_BONUS:
            q_bonus = _real_constructor_quali_bonus(grids)
        elif len(grids) >= 2:
            if all(g <= 10 for g in grids):
                q_bonus = 3  # both in Q3
            elif all(g <= 15 for g in grids):
                q_bonus = 1  # both in Q2
            else:
                q_bonus = 0
        else:
            q_bonus = 0

        return top_team + q_bonus

    return {team: round(sums.get(team, 0.0) + _bonus(team) + extra.get(team, 0.0), 3)
            for team in constructor_prices}


def _driver_out(d: dict, with_dnf: bool) -> dict:
    """One driver the way the API returns it."""
    out = {
        "Abbreviation": d["Abbreviation"],
        "TeamName": d["TeamName"],
        "GridPosition": int(d["GridPosition"]),
        "Predicted": round(d["Predicted"], 1),
        "FantasyValue": round(d["FantasyValue"], 3),
        "Price": d["Price"],
        "PickCategory": d["PickCategory"],
    }
    if with_dnf:
        # None when dnf risk wasn't worked out (e.g. a race that already happened)
        out["DNFProb"] = round(d["DNFProb"], 3) if "DNFProb" in d else None
    return out


def build_budget_team(
    fantasy_table: pd.DataFrame,
    race_name: str,
    prices: dict,
    budget: float = 100.0,
    min_safe: int = 1,
    dnf_probs: dict | None = None,
    dnf_weight: float = DNF_WEIGHT,
    constructor_extras: dict | None = None,
) -> dict:
    race_df, safe_abbrevs = _priced_race_table(fantasy_table, race_name, prices,
                                               dnf_probs=dnf_probs, dnf_weight=dnf_weight)
    constructor_prices = prices.get("constructors", {})

    # constructors get added up from the full table, drop_avoid takes the Avoid
    # drivers out of the sums (unless FIX_CONSTRUCTOR_QUIRKS), see _constructor_scores
    scores = _constructor_scores(race_df, constructor_prices, drop_avoid=True, with_bonus=True,
                                 extras=constructor_extras)

    # Remove avoid-tier drivers from the candidate pool
    race_df = race_df[race_df["PickCategory"] != "Avoid"]
    constructors = [
        {"name": team, "price": price, "score": scores[team]}
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
                    "drivers": [_driver_out(d, with_dnf=False) for d in driver_combo],
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


def build_budget_teams(
    fantasy_table: pd.DataFrame,
    race_name: str,
    prices: dict,
    budget: float = 100.0,
    n: int = 3,
    min_driver_diff: int = 2,
    dnf_probs: dict | None = None,
    dnf_weight: float = DNF_WEIGHT,
    constructor_extras: dict | None = None,
) -> list[dict]:
    """
    Returns n high-scoring teams that are mutually diverse (differ by at least
    min_driver_diff drivers). Runs the full combinations solver once and keeps
    a pool of top candidates, then greedily picks diverse teams from that pool.
    """
    race_df, safe_abbrevs = _priced_race_table(fantasy_table, race_name, prices,
                                               dnf_probs=dnf_probs, dnf_weight=dnf_weight)
    constructor_prices = prices.get("constructors", {})

    # constructors get added up from the full table, drop_avoid takes the Avoid
    # drivers out of the sums (unless FIX_CONSTRUCTOR_QUIRKS), see _constructor_scores
    scores = _constructor_scores(race_df, constructor_prices, drop_avoid=True, with_bonus=True,
                                 extras=constructor_extras)
    race_df = race_df[race_df["PickCategory"] != "Avoid"]

    # Retirement risk per constructor. A constructor scores BOTH its cars, so it
    # carries double the exposure of a single driver: Aston Martin losing both
    # cars at Monza cost -40 on the constructor alone. `dnf_risk` is the chance
    # of losing at least one car, which is the number worth showing a human.
    team_dnf_probs = (
        race_df.groupby("TeamName")["DNFProb"].apply(list).to_dict()
        if "DNFProb" in race_df.columns else {}
    )

    def _team_risk(team):
        ps = team_dnf_probs.get(team, [])
        if not ps:
            return None, None
        both_finish = 1.0
        for pr in ps:
            both_finish *= (1 - pr)
        both_out = 1.0
        for pr in ps:
            both_out *= pr
        return round(1 - both_finish, 3), round(both_out, 3)

    constructors = []
    for team, price in constructor_prices.items():
        any_out, both_out = _team_risk(team)
        constructors.append({
            "name": team,
            "price": price,
            "score": scores[team],
            "dnf_risk": any_out,        # P(at least one car retires)
            "double_dnf_risk": both_out,  # P(both cars retire), the Monza scenario
        })

    drivers_list = race_df.to_dict("records")

    # Collect the top 50 valid teams by score in a single pass
    POOL_SIZE = 50
    pool: list[tuple[float, frozenset, dict]] = []

    for driver_combo in combinations(drivers_list, 5):
        safe_count = sum(1 for d in driver_combo if d["Abbreviation"] in safe_abbrevs)
        if safe_count < 1:
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

            team_dict = {
                "drivers": [_driver_out(d, with_dnf=True) for d in driver_combo],
                "constructors": [
                    {
                        "name": c["name"], "price": c["price"], "score": c["score"],
                        "dnf_risk": c["dnf_risk"], "double_dnf_risk": c["double_dnf_risk"],
                    }
                    for c in constructor_combo
                ],
                "total_cost": round(total_cost, 1),
                "budget_remaining": round(budget - total_cost, 1),
                "total_score": round(total_score, 3),
                "boost_pick": None,
            }
            abbrevs = frozenset(d["Abbreviation"] for d in driver_combo)

            if len(pool) < POOL_SIZE:
                pool.append((total_score, abbrevs, team_dict))
                pool.sort(key=lambda x: -x[0])
            elif total_score > pool[-1][0]:
                pool[-1] = (total_score, abbrevs, team_dict)
                pool.sort(key=lambda x: -x[0])

    # Greedily pick n teams that each differ by at least min_driver_diff from all already-picked teams
    selected: list[tuple[float, frozenset, dict]] = []
    for score, abbrevs, team_dict in pool:
        if len(selected) >= n:
            break
        diverse = all(
            len(abbrevs & sel_abbrevs) <= (5 - min_driver_diff)
            for _, sel_abbrevs, _ in selected
        )
        if diverse:
            selected.append((score, abbrevs, team_dict))

    result = []
    for _, _, team_dict in selected:
        team_dict["boost_pick"] = pick_boost_driver(team_dict["drivers"])
        result.append(team_dict)

    return result


def get_race_pool(
    fantasy_table: pd.DataFrame,
    race_name: str,
    prices: dict,
    dnf_probs: dict | None = None,
    dnf_weight: float = DNF_WEIGHT,
    constructor_extras: dict | None = None,
) -> dict:
    """Returns all drivers + constructors for a race with prices and categories, used by the manual team builder."""
    race_df, _ = _priced_race_table(fantasy_table, race_name, prices,
                                    dnf_probs=dnf_probs, dnf_weight=dnf_weight)
    constructor_prices = prices.get("constructors", {})

    # no Avoid drop and no Q bonus here, unlike the team builders, see _constructor_scores
    scores = _constructor_scores(race_df, constructor_prices, drop_avoid=False, with_bonus=False,
                                 extras=constructor_extras)

    drivers = [_driver_out(d, with_dnf=True) for d in race_df.sort_values("Predicted").to_dict("records")]

    constructors = sorted(
        [{"name": t, "price": p, "score": scores[t]} for t, p in constructor_prices.items()],
        key=lambda c: -c["score"],
    )

    return {"drivers": drivers, "constructors": constructors}
