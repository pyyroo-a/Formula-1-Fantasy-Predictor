import os
import fastf1
import pandas as pd

from src.team_names import normalize_team_names

os.makedirs("data/cache", exist_ok=True)
fastf1.Cache.enable_cache("data/cache")

# Remaining 2026 sprint weekends — FP1 is the only practice session
SPRINT_WEEKENDS = {
    "Dutch Grand Prix",
    "Singapore Grand Prix",
}


def is_sprint_weekend(race_name: str) -> bool:
    return race_name in SPRINT_WEEKENDS


def fallback_sessions(first: str) -> list[str]:
    """
    The order we try practice sessions in, starting from `first` and working
    backwards. FP3 -> [FP3, FP2, FP1], FP2 -> [FP2, FP1], anything else -> [first].
    """
    order = ["FP3", "FP2", "FP1"]
    return order[order.index(first):] if first in order else [first]


def first_available_practice(year: int, race_name: str, sessions: list[str]):
    """
    Tries each practice session in order and gives back the first one that loads,
    as (practice_df, session_used, last_error). If none of them load, practice_df
    and session_used are None and last_error says why the last try failed.

    This loop used to be copied in six different places.
    """
    last_error = None
    for sess in sessions:
        try:
            return get_practice_grid(year, race_name, sess), sess, None
        except Exception as e:
            last_error = str(e)
    return None, None, last_error


def get_practice_grid(year: int, race_name: str, session: str = "FP3") -> pd.DataFrame:
    """
    Fetches practice session data and returns estimated grid positions
    based on fastest lap times.

    For sprint weekends, session is automatically set to FP1 regardless
    of what was passed in, since FP2/FP3 do not exist.
    """
    if is_sprint_weekend(race_name):
        session = "FP1"

    event = fastf1.get_event(year, race_name)
    sess = event.get_session(session)
    sess.load(laps=True, telemetry=False, weather=False, messages=False)

    laps = sess.laps[["Driver", "Team", "LapTime"]].copy()
    laps = laps.dropna(subset=["LapTime"])

    fastest = (
        laps.groupby("Driver")["LapTime"]
        .min()
        .reset_index()
        .sort_values("LapTime")
        .reset_index(drop=True)
    )

    fastest["GridPosition"] = fastest.index + 1

    teams = laps.groupby("Driver")["Team"].first().reset_index()
    fastest = fastest.merge(teams, on="Driver")

    fastest = fastest.rename(columns={"Driver": "Abbreviation", "Team": "TeamName"})
    fastest["RaceName"] = race_name

    # Lap time gap features (in seconds)
    fastest["LapTime_s"] = fastest["LapTime"].dt.total_seconds()
    pole_time = fastest["LapTime_s"].min()
    fastest["GapToPole"] = (fastest["LapTime_s"] - pole_time).round(3)

    team_best = fastest.groupby("TeamName")["LapTime_s"].transform("min")
    fastest["GapToTeammate"] = (fastest["LapTime_s"] - team_best).round(3)

    fastest = fastest[["Abbreviation", "TeamName", "GridPosition", "RaceName", "GapToPole", "GapToTeammate"]]
    fastest = normalize_team_names(fastest)  # same upstream as results, see src/team_names.py

    return fastest
