"""
Bits every race weekend endpoint needs: the season schedule, which race is next,
and the best practice order available right now. Used by race_weekend.py (the
team), finishes.py (predicted finishes) and weekend_lock.py (the auto lock).
"""
import fastf1
import pandas as pd

from src.config import SEASON
from src.fetch_practice import fallback_sessions, first_available_practice
from src.weekend import load_grid


def load_schedule():
    fastf1.Cache.enable_cache("data/cache")
    return fastf1.get_event_schedule(SEASON, include_testing=False)


def next_race(schedule, now):
    """The next race that hasn't started yet, or None once the season is over."""
    for _, event in schedule.sort_values("RoundNumber").iterrows():
        race_date = event["Session5Date"]
        if pd.isna(race_date):
            continue
        if pd.Timestamp(race_date) > now:
            return event
    return None


def weekend_grid(race_name: str, final_session: str):
    """
    Best order available right now for the live preview.

    Sprint weekend: sprint qualifying, because the deadline is the sprint race so
    that session has already run. Normal weekend: FP3, working back to FP1.
    Returns (df, session_used), or (None, None) if nothing has been published.
    """
    if final_session == "SQ":
        try:
            return load_grid(race_name, "SQ"), "SQ"
        except Exception:
            # sprint quali not out yet, FP1 is better than nothing
            df, used, _ = first_available_practice(SEASON, race_name, ["FP1"])
            return df, used
    df, used, _ = first_available_practice(SEASON, race_name, fallback_sessions(final_session))
    return df, used
