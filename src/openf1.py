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
# each session's driver list, kept for an hour like the sessions list, because a list
# can be out of date during the weekend (Mexico FP3 named car 50 wrong at first)
_drivers_cache: dict[int, tuple[float, list]] = {}
_grid_cache: dict[int, pd.DataFrame] = {}
# the raw laps and drivers per finished session, so the model's grid and the Practice
# page share one download (the free tier is rate limited)
_laps_cache: dict[int, tuple[list, list]] = {}


class NotPublishedYet(Exception):
    """The session isn't over (plus the buffer) or has no timed laps yet. Try later."""


class OpenF1Unavailable(Exception):
    """OpenF1 couldn't give us the session: switched off, not found, network, rate limit."""


class LiveBlocked(NotPublishedYet):
    """
    A session is live, and OpenF1 blocks free users from everything (old sessions too)
    until it ends. Basically "try again later", which is why it's a NotPublishedYet:
    the lock keeps waiting and nobody bothers asking FastF1.
    """


def clear_caches():
    _sessions_cache.clear()
    _drivers_cache.clear()
    _grid_cache.clear()
    _laps_cache.clear()


def _utc(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _detail(data) -> str:
    return str(data.get("detail", "")) if isinstance(data, dict) else ""


def _is_live_block(data) -> bool:
    """We never saw which status code comes with the block, so we go by the message."""
    return _detail(data).startswith("Live F1 session in progress")


def _is_no_results(data) -> bool:
    """OpenF1's "nothing here yet". It comes with a 404, so again we go by the message."""
    return _detail(data).startswith("No results found")


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
        try:
            data = r.json()
        except ValueError:
            data = None
        # OpenF1 answers with a dict instead of a list when something's wrong. Two of
        # those aren't really wrong though. On Mexico FP3 the laps said "No results found."
        # for hours, which just means nothing yet, and we treated it as OpenF1 being down
        if _is_no_results(data):
            return []
        if _is_live_block(data):
            raise LiveBlocked(f"OpenF1 {path}: blocked while a session is live")
        if r.status_code != 200:
            raise OpenF1Unavailable(f"OpenF1 {path} returned {r.status_code}")
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


def _session_drivers(key: int) -> list:
    cached = _drivers_cache.get(key)
    if cached and time.time() - cached[0] < SESSIONS_TTL_S:
        return cached[1]
    drivers = _get("drivers", {"session_key": key})
    _drivers_cache[key] = (time.time(), drivers)
    return drivers


def meeting_drivers(session: dict, needed: set | None = None) -> list[dict]:
    """
    Everyone we can name for one session: its own /drivers first, then any car number
    that's only in /drivers for another session of the same weekend (same meeting_key).

    Basically a session's list can be empty (Monaco FP2, Singapore SQ) or out of date
    (Mexico FP3 had no car 30, LAW). The session's own entry always wins. If `needed`
    is given and the session's own list already names all of them, we don't bother
    asking about the rest of the weekend.
    """
    own = list(_session_drivers(session["session_key"]))
    have = {d["driver_number"] for d in own}
    if needed is not None and set(needed) <= have:
        return own
    meeting = session.get("meeting_key")
    if meeting is None:
        return own
    year = session.get("year") or _utc(session["date_start"]).year
    for other in _sessions(year):
        if other.get("meeting_key") != meeting or other["session_key"] == session["session_key"]:
            continue
        for d in _session_drivers(other["session_key"]):
            if d["driver_number"] not in have:
                own.append(d)
                have.add(d["driver_number"])
    return own


def _name_laps(best: pd.DataFrame, drivers: list, cols: list[str], what: str) -> pd.DataFrame:
    """
    Puts names on each driver's best lap. A car nobody can name gets left out (and
    logged) instead of guessed, and no names at all means there's nothing to rank yet.
    """
    drv = pd.DataFrame(drivers)
    for col in cols:
        if col not in drv:
            drv[col] = None
    drv = drv[cols].drop_duplicates("driver_number") if not drv.empty else pd.DataFrame(columns=cols)
    unnamed = sorted(set(best["driver_number"]) - set(drv["driver_number"]))
    if unnamed:
        print(f"OpenF1 {what}: leaving out car(s) {unnamed}, nobody in the driver lists has that number")
    named = best.merge(drv, on="driver_number")
    if named.empty:
        raise NotPublishedYet(f"no named drivers for {what} yet")
    return named


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
    best = _name_laps(best, drivers, ["driver_number", "name_acronym", "team_name"], race_name)
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


def _finished_session(year: int, race_name: str, session: str, start_utc, now=None) -> int:
    """
    The OpenF1 session (its whole dict) for a finished session. Raises NotPublishedYet if it isn't
    over yet (nobody has those laps, FastF1 included, so don't bother falling back), and
    OpenF1Unavailable if OpenF1 can't help (then FastF1 gets a go).
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
    if not session_ready(match, now if now is not None else pd.Timestamp.now(tz="UTC")):
        raise NotPublishedYet(f"{race_name} {session} isn't over yet (ends {match['date_end']})")
    return match


def _laps_and_drivers(session: dict) -> tuple[list, list]:
    key = session["session_key"]
    if key in _laps_cache:
        return _laps_cache[key]
    laps = _get("laps", {"session_key": key})
    needed = {lap["driver_number"] for lap in laps or [] if lap.get("lap_duration") is not None}
    drivers = meeting_drivers(session, needed)
    # only remember a session once it has timed laps. OpenF1 can still be filling them in
    # after the buffer, and a remembered empty answer would say "not published" until the
    # server restarts, which would stop the automatic lock for the whole weekend
    if any(lap.get("lap_duration") is not None for lap in laps or []):
        _laps_cache[key] = (laps, drivers)
    return laps, drivers


def openf1_grid(year: int, race_name: str, session: str, start_utc, now=None) -> pd.DataFrame:
    """The pace order for one session from OpenF1. Raises like _finished_session."""
    match = _finished_session(year, race_name, session, start_utc, now)
    key = match["session_key"]
    if key in _grid_cache:
        return _grid_cache[key].copy()
    laps, drivers = _laps_and_drivers(match)
    grid = grid_from_openf1(laps, drivers, race_name)
    _grid_cache[key] = grid
    return grid.copy()


def _lap_text(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    return f"{ms // 60000}:{(ms % 60000) / 1000:06.3f}"


def practice_table(laps: list, drivers: list) -> list[dict]:
    """
    The rows the Practice page shows: everyone's fastest lap, fastest first, with the
    gap to the top. Same ranking as grid_from_openf1. OpenF1's full_name is shouty
    ("Charles LECLERC") so the name is built from first and last name instead.
    """
    laps = pd.DataFrame(laps)
    if laps.empty or "lap_duration" not in laps:
        raise NotPublishedYet("no laps yet")
    laps = laps.dropna(subset=["lap_duration"])
    if laps.empty:
        raise NotPublishedYet("no timed laps yet")

    best = laps.groupby("driver_number")["lap_duration"].min().reset_index()
    best = _name_laps(best, drivers, ["driver_number", "name_acronym", "team_name", "first_name", "last_name"],
                      "the practice table")
    best = best.sort_values("lap_duration").reset_index(drop=True)
    best = normalize_team_names(best.rename(columns={"team_name": "TeamName"}))
    pole = best["lap_duration"].min()

    rows = []
    for i, r in best.iterrows():
        named = isinstance(r["first_name"], str) and isinstance(r["last_name"], str)
        rows.append({
            "Position": int(i) + 1,
            "Abbreviation": r["name_acronym"],
            "FullName": f"{r['first_name']} {r['last_name']}" if named else r["name_acronym"],
            "TeamName": r["TeamName"],
            "LapTime": _lap_text(r["lap_duration"]),
            "GapToPole": round(float(r["lap_duration"] - pole), 3),
        })
    return rows


def openf1_practice(year: int, race_name: str, session: str, start_utc, now=None) -> list[dict]:
    """The Practice page's rows for one session from OpenF1. Raises like _finished_session."""
    match = _finished_session(year, race_name, session, start_utc, now)
    laps, drivers = _laps_and_drivers(match)
    return practice_table(laps, drivers)
