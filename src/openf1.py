"""
OpenF1 (api.openf1.org), where practice and sprint quali laps come from now.

Basically in October 2026 F1 put its live timing archive behind an F1TV login. FastF1
reads that archive, so from then on every new session "loaded" with 0 drivers. It
doesn't raise, it just logs warnings, so the site said "no practice data yet" for the
whole of US GP weekend while FP1 and FP2 had run fine. The automatic lock broke the
same way, see session_published in src/weekend.py.

FastF1 3.9.0 can log in, but only with a paid F1TV Access account and the token runs
out every 4 days, so that's no good for a free project running on Render.

OpenF1 is free, has no login and gives the same laps. Measured against FastF1 on four
weekends we still had cached (Monza, Madring, Baku and Bahrain FP3): same 22 drivers,
same order, same gap to pole down to the millisecond. So it's a straight swap, not an
approximation.

The free tier is rate limited, so a finished session's grid is only downloaded once
per server, and the session list is kept for an hour.

USE_OPENF1=0 switches it off and everything goes back to FastF1 only.
"""
import os
import time

import httpx
import pandas as pd

from src.team_names import normalize_team_names

BASE = "https://api.openf1.org/v1"

# our session codes -> how OpenF1 names them (same names FastF1's schedule uses)
SESSION_NAMES = {"FP1": "Practice 1", "FP2": "Practice 2", "FP3": "Practice 3",
                 "SQ": "Sprint Qualifying"}

# how long after a session ends before we trust all its laps are in. Locking half a
# session would be worse than waiting, and there's 2.5 hours between FP3 and quali
INGEST_BUFFER = pd.Timedelta(minutes=30)

# FastF1's schedule and OpenF1 should have the same start time, this is just slack.
# Small enough that two races' FP2s (a week apart at least) can't get mixed up
MATCH_TOLERANCE = pd.Timedelta(hours=6)

SESSIONS_TTL_S = 3600

_sessions_cache: dict[int, tuple[float, list]] = {}
_grid_cache: dict[int, pd.DataFrame] = {}


class NotPublishedYet(Exception):
    """The session isn't over (plus the buffer) or has no timed laps yet. Try later."""


class OpenF1Unavailable(Exception):
    """OpenF1 couldn't give us the session: switched off, not found, network, rate limit."""


def clear_caches():
    _sessions_cache.clear()
    _grid_cache.clear()


def _utc(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _get(path: str, params: dict):
    """One OpenF1 request. Waits and retries once if we hit the rate limit."""
    for attempt in range(2):
        try:
            r = httpx.get(f"{BASE}/{path}", params=params, timeout=30)
        except httpx.HTTPError as e:
            raise OpenF1Unavailable(f"OpenF1 {path}: {e}") from e
        if r.status_code == 429 and attempt == 0:
            time.sleep(2)
            continue
        if r.status_code != 200:
            raise OpenF1Unavailable(f"OpenF1 {path} returned {r.status_code}")
        data = r.json()
        # OpenF1 answers with a dict instead of a list when something's wrong
        if not isinstance(data, list):
            raise OpenF1Unavailable(f"OpenF1 {path}: {data}")
        return data
    raise OpenF1Unavailable(f"OpenF1 {path} kept rate limiting us")


def _sessions(year: int) -> list:
    cached = _sessions_cache.get(year)
    if cached and time.time() - cached[0] < SESSIONS_TTL_S:
        return cached[1]
    sessions = _get("sessions", {"year": year})
    _sessions_cache[year] = (time.time(), sessions)
    return sessions


def pick_session(sessions: list, session_name: str, start_utc) -> dict | None:
    """
    The OpenF1 session with this name that starts closest to start_utc, or None.

    We match on start time instead of race name on purpose. Names move about (the
    Bahrain GP was in Kuala Lumpur this year and OpenF1 still calls it Bahrain), but
    two sessions with the same name can't start within hours of each other.
    """
    start = _utc(start_utc)
    best, best_gap = None, MATCH_TOLERANCE
    for s in sessions:
        if s.get("session_name") != session_name:
            continue
        gap = abs(_utc(s["date_start"]) - start)
        if gap <= best_gap:
            best, best_gap = s, gap
    return best


def session_ready(session: dict, now) -> bool:
    """True once the session has finished and INGEST_BUFFER has passed."""
    if session.get("is_cancelled"):
        return False
    return _utc(now) >= _utc(session["date_end"]) + INGEST_BUFFER


def grid_from_openf1(laps: list, drivers: list, race_name: str) -> pd.DataFrame:
    """
    Same shape and same maths as get_practice_grid's FastF1 version: rank by each
    driver's fastest lap, then gap to pole and gap to teammate in seconds.
    """
    laps = pd.DataFrame(laps)
    if laps.empty or "lap_duration" not in laps:
        raise NotPublishedYet(f"no laps for {race_name} yet")
    laps = laps.dropna(subset=["lap_duration"])
    if laps.empty:
        raise NotPublishedYet(f"no timed laps for {race_name} yet")

    best = laps.groupby("driver_number")["lap_duration"].min().reset_index()
    drv = pd.DataFrame(drivers)[["driver_number", "name_acronym", "team_name"]].drop_duplicates("driver_number")
    best = best.merge(drv, on="driver_number")
    best = best.sort_values("lap_duration").reset_index(drop=True)

    best["GridPosition"] = best.index + 1
    best = best.rename(columns={"name_acronym": "Abbreviation", "team_name": "TeamName",
                                "lap_duration": "LapTime_s"})
    best["RaceName"] = race_name
    best["GapToPole"] = (best["LapTime_s"] - best["LapTime_s"].min()).round(3)
    team_best = best.groupby("TeamName")["LapTime_s"].transform("min")
    best["GapToTeammate"] = (best["LapTime_s"] - team_best).round(3)

    best = best[["Abbreviation", "TeamName", "GridPosition", "RaceName", "GapToPole", "GapToTeammate"]]
    return normalize_team_names(best)


def openf1_grid(year: int, race_name: str, session: str, start_utc, now=None) -> pd.DataFrame:
    """
    The pace order for one session from OpenF1.

    Raises NotPublishedYet if the session isn't finished yet (nobody has those laps,
    FastF1 included, so don't bother falling back), and OpenF1Unavailable if OpenF1
    can't help (then FastF1 gets a go, which still works for sessions in our cache).
    """
    if os.getenv("USE_OPENF1", "1") != "1":
        raise OpenF1Unavailable("switched off with USE_OPENF1=0")
    name = SESSION_NAMES.get(session)
    if name is None:
        raise OpenF1Unavailable(f"don't know how OpenF1 names {session!r}")
    if start_utc is None or pd.isna(start_utc):
        raise OpenF1Unavailable(f"no start time for {race_name} {session}")

    match = pick_session(_sessions(year), name, start_utc)
    if match is None:
        raise OpenF1Unavailable(f"OpenF1 has no {name} near {start_utc} for {race_name}")

    key = match["session_key"]
    if key in _grid_cache:
        return _grid_cache[key].copy()

    if not session_ready(match, now if now is not None else pd.Timestamp.now(tz="UTC")):
        raise NotPublishedYet(f"{race_name} {session} isn't over yet (ends {match['date_end']})")

    grid = grid_from_openf1(_get("laps", {"session_key": key}),
                            _get("drivers", {"session_key": key}), race_name)
    _grid_cache[key] = grid
    return grid.copy()
