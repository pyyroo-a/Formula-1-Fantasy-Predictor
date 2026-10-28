"""
How much to trust each driver's practice spot, project 4 on the roadmap.

The forecast is basically the FP3 order, and that's right on average, but some FP3
spots are solid and some are flukes. Three things known before quali tell them apart,
each one is a flag:

  - teammate doesn't back it up: more than 2 places from them in the lock session
  - moved around: their rank jumped about across the weekend's sessions
  - tight pack: under 0.05s from the nearest car, so tiny things reshuffle them

0 flags = high, 1 = medium, 2 or more = low. Every level comes with a plain sentence
saying which checks passed or failed and the real numbers, so it's never just a label.

This never changes a pick. It gets stuck on the driver dicts after the teams are built.
See docs/superpowers/specs/2026-10-28-confidence-and-reasons-design.md.
"""
from typing import Callable

import pandas as pd

# Measured on the 12 FP3 weekends of 2026 (261 driver weekends) with
# scripts/confidence_grade.py, places between a driver's FP3 rank and where they really
# ranked on fantasy points: high 3.02, medium 3.59, low 4.51, and high beat low on 11
# of the 12 weekends (the brainstorm's quick check said 3.06 / 3.46 / 4.56 and 10 of
# 12, close enough: that used raw OpenF1 laps, this goes through our own loaders and
# Monza FP1 wouldn't load). Heads up, these cutoffs were
# picked near the middle of that data after looking at it, so Mexico onwards is the
# honest test (scripts/confidence_grade.py). Don't tune them to make it look better.
MATE_PLACES = 2       # flagged if MORE than this many places from the teammate
SPREAD_LIMIT = 1.5    # flagged if the sample std of their ranks is above this
PACK_GAP_S = 0.05     # flagged if the nearest car is UNDER this many seconds away

# Sprint weekends lock on sprint quali (moved around = FP1 vs sprint quali). Measured
# 2026-10-28 with scripts/confidence_grade.py over the 6 sprint weekends, places off on
# fantasy points: high 4.81, medium 4.30, low 4.78, high beat low on only 3 of 6. So on
# sprint weekends the levels don't mean anything for points and it stays off. (It does
# still split the race finish, 1.41 vs 2.74, but the sprint points muddle the total.)
SHOW_ON_SPRINT_WEEKENDS = False

SESSION_ORDER = ["FP1", "FP2", "FP3"]
SESSION_LABEL = {"SQ": "sprint quali"}


def sessions_for(lock_session: str) -> list[str]:
    """The sessions that count for a weekend locked on lock_session, in order."""
    if lock_session == "SQ":
        return ["FP1", "SQ"]
    return SESSION_ORDER[: SESSION_ORDER.index(lock_session) + 1]


def load_weekend_sessions(load: Callable[[str], pd.DataFrame], lock_session: str) -> dict[str, pd.DataFrame]:
    """
    Loads every session of the weekend up to the lock one. An earlier session that
    won't load just gets skipped (the spread check uses whatever's there), but the
    lock session has to load, everything hangs off it.
    """
    out = {}
    for s in sessions_for(lock_session):
        try:
            grid = load(s)
        except Exception as e:
            if s == lock_session:
                raise
            print(f"confidence: skipping {s}, it wouldn't load ({e})")
            continue
        if grid is None or grid.empty:
            if s == lock_session:
                raise ValueError(f"no {s} grid to work out confidence from")
            continue
        out[s] = grid
    return out


def _join(items: list[str]) -> str:
    """"a", "a and b", "a, b and c"."""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _driver_confidence(row, lock: pd.DataFrame, ranks: list[int], label: str) -> dict:
    passed, flagged, unknown = [], [], []
    rank = int(row["GridPosition"])

    mates = lock[(lock["TeamName"] == row["TeamName"]) & (lock["Abbreviation"] != row["Abbreviation"])]
    if len(mates) != 1:
        unknown.append("no teammate time")
    else:
        mate, mate_rank = mates.iloc[0]["Abbreviation"], int(mates.iloc[0]["GridPosition"])
        if abs(rank - mate_rank) > MATE_PLACES:
            flagged.append(f"teammate {mate} was P{mate_rank}")
        else:
            passed.append(f"teammate {mate} P{mate_rank} backs it up")

    if len(ranks) < 2:
        unknown.append("only one session so far")
    elif pd.Series(ranks).std() > SPREAD_LIMIT:
        flagged.append(f"moved around between sessions (P{min(ranks)} to P{max(ranks)})")
    else:
        passed.append("steady all weekend")

    ahead = lock[lock["GridPosition"] == rank - 1]["GapToPole"]
    behind = lock[lock["GridPosition"] == rank + 1]["GapToPole"]
    gaps = [abs(row["GapToPole"] - g) for g in list(ahead) + list(behind)]
    if not gaps:
        unknown.append("no other car to compare")
    elif min(gaps) < PACK_GAP_S:
        flagged.append(f"only {min(gaps):.3f}s from the next car")
    else:
        passed.append(f"{min(gaps):.3f}s clear of the next car")

    reason = f"P{rank} in {label}."
    if passed:
        first = _join(passed)
        reason += " " + first[0].upper() + first[1:] + "."
    if flagged:
        reason += " But " + _join(flagged) + "."
    if unknown:
        reason += " Couldn't check: " + _join(unknown) + "."

    flags = len(flagged)
    level = "high" if flags == 0 else "medium" if flags == 1 else "low"
    return {"level": level, "flags": flags, "reason": reason}


def weekend_confidence(sessions: dict[str, pd.DataFrame], lock_session: str) -> dict[str, dict]:
    """
    Every driver in the lock session's grid -> {"level", "flags", "reason"}.
    sessions maps a session name to its grid (Abbreviation, TeamName, GridPosition,
    GapToPole), the lock session has to be in there.
    """
    lock = sessions[lock_session]
    label = SESSION_LABEL.get(lock_session, lock_session)
    out = {}
    for _, row in lock.iterrows():
        a = row["Abbreviation"]
        ranks = [int(g.loc[g["Abbreviation"] == a, "GridPosition"].iloc[0])
                 for g in sessions.values() if (g["Abbreviation"] == a).any()]
        out[a] = _driver_confidence(row, lock, ranks, label)
    return out


def attach_confidence(drivers: list[dict], conf: dict | None) -> list[dict]:
    """New copies of the driver dicts with Confidence and ConfidenceReason (None if we don't know)."""
    conf = conf or {}
    out = []
    for d in drivers:
        c = conf.get(d.get("Abbreviation"))
        out.append({**d, "Confidence": c["level"] if c else None,
                    "ConfidenceReason": c["reason"] if c else None})
    return out


def attach_to_teams(teams: list[dict], conf: dict | None) -> list[dict]:
    """Same as attach_confidence for every team's drivers and its 2x pick."""
    out = []
    for t in teams:
        t = {**t, "drivers": attach_confidence(t["drivers"], conf)}
        if t.get("boost_pick"):
            t["boost_pick"] = attach_confidence([t["boost_pick"]], conf)[0]
        out.append(t)
    return out
