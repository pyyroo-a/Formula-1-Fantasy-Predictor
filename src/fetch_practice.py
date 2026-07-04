import fastf1
import pandas as pd

fastf1.Cache.enable_cache("data/cache")


def get_practice_grid(year: int, race_name: str, session: str = "FP2") -> pd.DataFrame:
    """
    Fetches practice session data and returns estimated grid positions
    based on fastest lap times, formatted for predict_upcoming_race.

    Args:
        year: The season year (e.g. 2026)
        race_name: FastF1 event name (e.g. "British Grand Prix")
        session: Which practice session to use — FP2 or FP3 (FP3 preferred if available)
    """
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