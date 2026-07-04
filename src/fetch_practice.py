import fastf1
import pandas as pd

fastf1.Cache.enable_cache("data/cache")

# Remaining 2026 sprint weekends — FP1 is the only practice session
SPRINT_WEEKENDS = {
    "Dutch Grand Prix",
    "Singapore Grand Prix",
}


def is_sprint_weekend(race_name: str) -> bool:
    return race_name in SPRINT_WEEKENDS


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
    fastest = fastest[["Abbreviation", "TeamName", "GridPosition", "RaceName"]]

    return fastest
