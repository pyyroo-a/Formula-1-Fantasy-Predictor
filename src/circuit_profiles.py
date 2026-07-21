import pandas as pd

# Per-circuit profiles for the 2026 F1 calendar.
# overtaking: 1–10 scale (1 = Monaco, 10 = Brazil/Monza)
# attrition:  probability a car fails to finish (DNF risk)
# These are validated and can be overridden by compute_historical_overtaking().
CIRCUIT_PROFILES = {
    "Bahrain Grand Prix":          {"overtaking": 7, "attrition": 0.10},
    "Saudi Arabian Grand Prix":    {"overtaking": 6, "attrition": 0.18},
    "Australian Grand Prix":       {"overtaking": 5, "attrition": 0.12},
    "Japanese Grand Prix":         {"overtaking": 4, "attrition": 0.08},
    "Chinese Grand Prix":          {"overtaking": 7, "attrition": 0.10},
    "Miami Grand Prix":            {"overtaking": 6, "attrition": 0.12},
    "Emilia Romagna Grand Prix":   {"overtaking": 4, "attrition": 0.10},
    "Monaco Grand Prix":           {"overtaking": 1, "attrition": 0.15},
    # 2026 runs Barcelona and Madrid as separate events — Madrid took the
    # "Spanish Grand Prix" name. Barcelona is aero-limited and hard to follow at;
    # Madrid is a new street circuit, so its rating is an unvalidated estimate.
    "Barcelona Grand Prix":        {"overtaking": 4, "attrition": 0.08},
    "Spanish Grand Prix":          {"overtaking": 4, "attrition": 0.10},
    "Canadian Grand Prix":         {"overtaking": 7, "attrition": 0.10},
    "Austrian Grand Prix":         {"overtaking": 7, "attrition": 0.08},
    "British Grand Prix":          {"overtaking": 7, "attrition": 0.10},
    "Belgian Grand Prix":          {"overtaking": 8, "attrition": 0.12},
    "Hungarian Grand Prix":        {"overtaking": 3, "attrition": 0.08},
    "Dutch Grand Prix":            {"overtaking": 3, "attrition": 0.08},
    "Italian Grand Prix":          {"overtaking": 9, "attrition": 0.10},
    "Azerbaijan Grand Prix":       {"overtaking": 7, "attrition": 0.20},
    "Singapore Grand Prix":        {"overtaking": 4, "attrition": 0.15},
    "United States Grand Prix":    {"overtaking": 7, "attrition": 0.10},
    "Mexico City Grand Prix":      {"overtaking": 5, "attrition": 0.10},
    "São Paulo Grand Prix":        {"overtaking": 9, "attrition": 0.12},
    "Las Vegas Grand Prix":        {"overtaking": 6, "attrition": 0.15},
    "Qatar Grand Prix":            {"overtaking": 6, "attrition": 0.10},
    "Abu Dhabi Grand Prix":        {"overtaking": 5, "attrition": 0.08},
}

_NEUTRAL = {"overtaking": 5, "attrition": 0.10}


def compute_historical_overtaking(df: pd.DataFrame) -> dict[str, float]:
    """
    Derives an overtaking score (1–10) per circuit from historical race data
    by computing mean absolute position change per driver per race.
    Returns a dict of {race_name: computed_overtaking_score}.
    """
    df = df.copy()
    df["PosChange"] = (df["GridPosition"] - df["Position"]).abs()

    circuit_avg = (
        df.groupby("RaceName")["PosChange"]
        .mean()
        .dropna()
    )

    if circuit_avg.empty:
        return {}

    min_chg = circuit_avg.min()
    max_chg = circuit_avg.max()
    if max_chg == min_chg:
        return {r: 5.0 for r in circuit_avg.index}

    # Normalize to 1–9 range (leave room for Monaco=1 and Brazil=9 as anchors)
    normalized = 1 + ((circuit_avg - min_chg) / (max_chg - min_chg)) * 8
    return normalized.round(1).to_dict()


def get_circuit_profile(race_name: str, historical_df: pd.DataFrame | None = None) -> dict:
    """
    Returns the circuit profile for race_name.
    If historical_df is provided, the overtaking rating is blended 50/50
    between the hardcoded value and the data-derived value for validation.
    """
    base = CIRCUIT_PROFILES.get(race_name, _NEUTRAL).copy()

    if historical_df is not None:
        computed = compute_historical_overtaking(historical_df)
        if race_name in computed:
            # Blend: trust the data but anchor to domain knowledge
            blended = round((base["overtaking"] + computed[race_name]) / 2, 1)
            base["overtaking"] = blended

    return base


def overtaking_scale(rating: int | float) -> float:
    """
    Converts a 1–10 overtaking rating into a multiplier for OvertakeBonus.
    Neutral (5) → 1.0x. Brazil (9) → 1.8x. Monaco (1) → 0.2x.
    """
    return round(rating / 5.0, 2)


def quali_scale(rating: int | float) -> float:
    """
    Converts a 1–10 overtaking rating into a qualifying score weight multiplier.
    Low overtaking = qualifying matters more.
    Monaco (1) → 1.9x. Spa (8) → 1.2x. Brazil (9) → 1.1x.
    """
    return round(1.0 + (10 - rating) / 10.0, 2)


def get_blend_weights(race_name: str) -> dict[str, float]:
    """
    Returns prediction blend weights tuned to the circuit type.
    Low-overtaking circuits lean on circuit history (grid = result).
    High-overtaking circuits trust the model and FP3 pace more.
    """
    profile = CIRCUIT_PROFILES.get(race_name, _NEUTRAL)
    rating = profile["overtaking"]

    if rating <= 2:
        # Monaco-style: qualifying position is king, circuit history dominates
        return {"model": 0.35, "practice": 0.05, "teammate": 0.05, "circuit": 0.55}
    elif rating <= 4:
        # Low overtaking: Hungary, Singapore, Zandvoort
        return {"model": 0.45, "practice": 0.10, "teammate": 0.05, "circuit": 0.40}
    elif rating <= 6:
        # Neutral
        return {"model": 0.55, "practice": 0.20, "teammate": 0.10, "circuit": 0.15}
    else:
        # High overtaking: Spa, Brazil, Monza — model + pace drives the pick
        return {"model": 0.60, "practice": 0.25, "teammate": 0.10, "circuit": 0.05}
