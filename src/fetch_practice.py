import os
from functools import lru_cache

import fastf1
import pandas as pd

from src import openf1
from src.config import SEASON
from src.team_names import normalize_team_names

os.makedirs("data/cache", exist_ok=True)
fastf1.Cache.enable_cache("data/cache")

# only used as a backup if FastF1's schedule can't be loaded at all
# (no internet and nothing cached). All six 2026 sprint weekends.
_FALLBACK_SPRINTS = {
    2026: {
        "Chinese Grand Prix", "Miami Grand Prix", "Canadian Grand Prix",
        "British Grand Prix", "Dutch Grand Prix", "Singapore Grand Prix",
    },
}


@lru_cache(maxsize=None)
def _sprint_events(year: int) -> frozenset:
    """Every sprint weekend in a season, read from FastF1's schedule (EventFormat)."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    is_sprint = schedule["EventFormat"].astype(str).str.contains("sprint", case=False)
    return frozenset(schedule.loc[is_sprint, "EventName"])


def is_sprint_weekend(race_name: str, year: int = SEASON) -> bool:
    """
    True if this race weekend has a sprint, so FP1 is its only practice session.

    This used to be a hand typed list that only had 2 of the 6 sprints in 2026
    (Dutch and Singapore), so China, Miami, Canada and Britain were treated as
    normal weekends. Now we read it from FastF1's schedule, which is always right
    and keeps working next season. The typed list above is only a backup.
    """
    try:
        return race_name in _sprint_events(year)
    except Exception:
        return race_name in _FALLBACK_SPRINTS.get(year, set())


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


def _session_start_utc(year: int, race_name: str, session_name: str):
    """When a session starts (UTC) per FastF1's schedule, which still loads fine. None if unknown."""
    try:
        return fastf1.get_event(year, race_name).get_session_date(session_name, utc=True)
    except Exception:
        return None


def _openf1_then_fastf1(year: int, race_name: str, session: str, fastf1_loader):
    """
    OpenF1 first, FastF1 as the backup. See src/openf1.py for why.

    Not the other way round because FastF1 now takes ~8s to fail on any session it
    doesn't already have cached (it tries every endpoint and gets a 401 each time),
    and the live preview tries FP3, FP2 and FP1 in turn, so that was ~23s of dead
    requests per page view. FastF1 is still the backup because its cache works
    offline for old sessions, which keeps backtests going if OpenF1 is down.

    If OpenF1 says the session isn't over yet we stop there. FastF1 can't have it
    either, and asking would just cost the 8s.
    """
    start = _session_start_utc(year, race_name, openf1.SESSION_NAMES.get(session, session))
    try:
        return openf1.openf1_grid(year, race_name, session, start)
    except openf1.NotPublishedYet:
        raise
    except openf1.OpenF1Unavailable:
        return fastf1_loader()


def get_sprint_quali_grid(year: int, race_name: str) -> pd.DataFrame:
    """
    Grid estimate from sprint qualifying. Same shape as get_practice_grid.

    On a sprint weekend the fantasy deadline is before the SPRINT RACE, so sprint
    qualifying has already happened when you pick. That gives us a real timed
    order instead of guessing from one practice hour. Measured over the 5 sprint
    weekends of 2026, against the real race grid: 1.90 places off, vs 2.52 for FP1.

    We rank by fastest lap from the session, the same way we do for practice.
    """
    return _openf1_then_fastf1(year, race_name, "SQ",
                               lambda: _fastf1_sprint_quali_grid(year, race_name))


def _fastf1_sprint_quali_grid(year: int, race_name: str) -> pd.DataFrame:
    """
    The FastF1 version, now only the backup.

    FastF1 does not give finishing positions or Q1/Q2/Q3 times for this session,
    only the laps.
    """
    event = fastf1.get_event(year, race_name)
    sess = event.get_session("Sprint Qualifying")
    sess.load(laps=True, telemetry=False, weather=False, messages=False)

    laps = sess.laps[["Driver", "Team", "LapTime"]].dropna(subset=["LapTime"]).copy()
    if laps.empty:
        raise ValueError(f"sprint qualifying for {race_name} has no lap times yet")

    fastest = (
        laps.groupby("Driver")["LapTime"].min().reset_index()
        .sort_values("LapTime").reset_index(drop=True)
    )
    fastest["GridPosition"] = fastest.index + 1

    teams = laps.groupby("Driver")["Team"].first().reset_index()
    fastest = fastest.merge(teams, on="Driver")
    fastest = fastest.rename(columns={"Driver": "Abbreviation", "Team": "TeamName"})
    fastest["RaceName"] = race_name

    fastest["LapTime_s"] = fastest["LapTime"].dt.total_seconds()
    fastest["GapToPole"] = (fastest["LapTime_s"] - fastest["LapTime_s"].min()).round(3)
    team_best = fastest.groupby("TeamName")["LapTime_s"].transform("min")
    fastest["GapToTeammate"] = (fastest["LapTime_s"] - team_best).round(3)

    fastest = fastest[["Abbreviation", "TeamName", "GridPosition", "RaceName", "GapToPole", "GapToTeammate"]]
    return normalize_team_names(fastest)


def get_practice_grid(year: int, race_name: str, session: str = "FP3") -> pd.DataFrame:
    """
    Fetches practice session data and returns estimated grid positions
    based on fastest lap times.

    For sprint weekends, session is automatically set to FP1 regardless
    of what was passed in, since FP2/FP3 do not exist.
    """
    if is_sprint_weekend(race_name, year):
        session = "FP1"
    return _openf1_then_fastf1(year, race_name, session,
                               lambda: _fastf1_practice_grid(year, race_name, session))


def _fastf1_practice_grid(year: int, race_name: str, session: str) -> pd.DataFrame:
    """The FastF1 version, now only the backup. Works for sessions in data/cache."""
    event = fastf1.get_event(year, race_name)
    sess = event.get_session(session)
    sess.load(laps=True, telemetry=False, weather=False, messages=False)

    laps = sess.laps[["Driver", "Team", "LapTime"]].copy()
    laps = laps.dropna(subset=["LapTime"])
    if laps.empty:
        raise ValueError(f"{session} for {race_name} has no lap times")

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
