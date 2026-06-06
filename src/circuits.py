import pandas as pd

CIRCUIT_PROFILES = {
    "Bahrain Grand Prix": {"circuit_type": "permanent", "drs_zones": 3},
    "Saudi Arabian Grand Prix":     {"circuit_type": "street",         "drs_zones": 3},
    "Australian Grand Prix":        {"circuit_type": "semi-permanent", "drs_zones": 2},
    "Japanese Grand Prix":          {"circuit_type": "permanent",      "drs_zones": 1},
    "Chinese Grand Prix":           {"circuit_type": "permanent",      "drs_zones": 2},
    "Miami Grand Prix":             {"circuit_type": "semi-permanent", "drs_zones": 3},
    "Emilia Romagna Grand Prix":    {"circuit_type": "permanent",      "drs_zones": 1},
    "Monaco Grand Prix":            {"circuit_type": "street",         "drs_zones": 1},
    "Canadian Grand Prix":          {"circuit_type": "semi-permanent", "drs_zones": 2},
    "Spanish Grand Prix":           {"circuit_type": "permanent",      "drs_zones": 2},
    "Austrian Grand Prix":          {"circuit_type": "permanent",      "drs_zones": 3},
    "British Grand Prix":           {"circuit_type": "permanent",      "drs_zones": 2},
    "Hungarian Grand Prix":         {"circuit_type": "permanent",      "drs_zones": 1},
    "Belgian Grand Prix":           {"circuit_type": "permanent",      "drs_zones": 1},
    "Dutch Grand Prix":             {"circuit_type": "permanent",      "drs_zones": 2},
    "Italian Grand Prix":           {"circuit_type": "permanent",      "drs_zones": 2},
    "Azerbaijan Grand Prix":        {"circuit_type": "street",         "drs_zones": 2},
    "Singapore Grand Prix":         {"circuit_type": "street",         "drs_zones": 3},
    "United States Grand Prix":     {"circuit_type": "permanent",      "drs_zones": 2},
    "Mexico City Grand Prix":       {"circuit_type": "permanent",      "drs_zones": 2},
    "São Paulo Grand Prix":         {"circuit_type": "permanent",      "drs_zones": 2},
    "Las Vegas Grand Prix":         {"circuit_type": "street",         "drs_zones": 2},
    "Qatar Grand Prix":             {"circuit_type": "permanent",      "drs_zones": 1},
    "Abu Dhabi Grand Prix":         {"circuit_type": "permanent",      "drs_zones": 2},
}

def calculate_circuit_stats(df: pd.DataFrame) -> pd.DataFrame:
    circuit_stats = df.groupby("RaceName").agg(
        avg_position_change = ("PositionChange", "mean"),
        dnf_rate = ("DNF", "mean"), 
    ).round(2).reset_index()

    return circuit_stats

def get_circuit_profiles(df: pd.DataFrame) -> pd.DataFrame:
    circuit_stats = calculate_circuit_stats(df)

    profiles = pd.DataFrame.from_dict(CIRCUIT_PROFILES, orient="index").reset_index()
    profiles = profiles.rename(columns={"index": "RaceName"})

    combined = profiles.merge(circuit_stats, on="RaceName", how="left")

    return combined

def attach_circuit_profiles(fantasy_table: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    profiles = get_circuit_profiles(df)
    enriched = fantasy_table.merge(profiles, on="RaceName", how="left")
    return enriched