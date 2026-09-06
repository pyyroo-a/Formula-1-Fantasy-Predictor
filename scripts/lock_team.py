"""
Snapshots the locked team for a race weekend into data/locked_team.json.

WHY THIS EXISTS
---------------
The backend already writes this file when it first sees final-practice data, but
Render's free tier has no persistent disk, so that file dies on every redeploy.
Deploy once during a race weekend and the lineup PitWall recommended is gone.

This script writes the same file from CI instead, and the workflow commits it to
the repo. Committed means it ships inside the deploy image, so it survives every
restart by construction.

The side benefit is the bigger one: the repo accumulates a per-race record of what
PitWall actually recommended *in advance*, which is the raw material for judging
the model on its real forward-looking calls rather than on a replay.

Safe to run repeatedly. It refuses to overwrite an existing lock for the same
race, so the team never changes mid-weekend, which is the whole point of a lock.

Usage:
    python scripts/lock_team.py                      # auto-detect this weekend
    python scripts/lock_team.py --race "Italian Grand Prix"
    python scripts/lock_team.py --race "..." --force  # overwrite an existing lock
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import fastf1
import pandas as pd

from src.pipeline import predict_upcoming_race
from src.fantasy import build_budget_teams, get_race_pool, build_budget_team
from src.fetch_practice import get_practice_grid
from src.fetch_prices import fetch_prices
# evaluate_team_chips lives in main.py rather than src/. It is a pure function
# (verified: it touches no module globals), and importing main only defines the
# FastAPI app without running its startup, so this is safe from a script.
from main import evaluate_team_chips

LOCK_PATH = "data/locked_team.json"

# How close to race day we consider a weekend "live". Matches /weekend-team.
ACTIVE_WINDOW_DAYS = 5


def final_practice_session(event) -> str:
    """
    The last practice session before the fantasy deadline.

    Read from FastF1's EventFormat rather than a hardcoded list of sprint races.
    Sprint weekends run FP1 only; conventional weekends run through FP3.
    """
    fmt = str(event.get("EventFormat", "conventional")).lower()
    return "FP1" if "sprint" in fmt else "FP3"


def find_weekend(schedule, race_name=None):
    """Returns the event to lock: the named race, or the next one due."""
    if race_name:
        match = schedule[schedule["EventName"] == race_name]
        if match.empty:
            sys.exit(f"No 2026 event named {race_name!r}.")
        return match.iloc[0]

    now = pd.Timestamp.now(tz="UTC")
    for _, event in schedule.sort_values("RoundNumber").iterrows():
        race_date = event["Session5Date"]
        if pd.isna(race_date) or pd.Timestamp(race_date) <= now:
            continue
        days_until = (pd.Timestamp(race_date) - now).total_seconds() / 86400
        if days_until <= ACTIVE_WINDOW_DAYS:
            return event
        # The next race is further out than the window, so no weekend is live.
        print(f"::notice::Next race is {round(days_until)} days away. Nothing to lock.")
        sys.exit(0)
    print("::notice::No upcoming races left in the schedule.")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", help="Event name, e.g. 'Italian Grand Prix'")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite an existing lock for the same race")
    args = ap.parse_args()

    fastf1.Cache.enable_cache("data/cache")
    schedule = fastf1.get_event_schedule(2026, include_testing=False)
    event = find_weekend(schedule, args.race)

    race_name = event["EventName"]
    rnd = int(event["RoundNumber"])
    session = final_practice_session(event)

    # A lock already in place for this race is the team that was committed to.
    # Leave it alone unless explicitly told otherwise.
    if os.path.exists(LOCK_PATH) and not args.force:
        try:
            with open(LOCK_PATH) as f:
                existing = json.load(f)
            if existing.get("race_name") == race_name:
                print(f"::notice::{race_name} is already locked. Nothing to do.")
                return
        except (json.JSONDecodeError, OSError):
            pass  # unreadable lock, fall through and rewrite it

    print(f"Locking {race_name} (round {rnd}) on {session}...")

    try:
        practice_df = get_practice_grid(2026, race_name, session)
    except Exception as e:
        # Not an error. Practice simply has not run or published yet, and the
        # workflow polls repeatedly, so a later run will pick it up.
        print(f"::notice::{session} not available yet for {race_name} ({e}). Nothing to lock.")
        return

    prices = fetch_prices(rnd)
    upcoming_table = predict_upcoming_race(practice_df)
    teams = build_budget_teams(upcoming_table, race_name, prices, budget=100.0)
    if not teams:
        print(f"::warning::Could not build a team within budget for {race_name}.")
        return

    # Chip advice, attached exactly as /weekend-team does so the committed lock
    # and a runtime-generated one are the same shape.
    pool = get_race_pool(upcoming_table, race_name, prices)
    optimal = build_budget_team(upcoming_table, race_name, prices, budget=100.0)
    limitless = build_budget_team(upcoming_table, race_name, prices, budget=999.0)
    optimal_score = optimal["total_score"] if optimal else 0.0
    limitless_score = limitless["total_score"] if limitless else optimal_score
    for team in teams:
        team["chips"] = evaluate_team_chips(
            [d["Abbreviation"] for d in team["drivers"]],
            [c["name"] for c in team["constructors"]],
            pool, optimal_score, limitless_score, race_name,
        )

    payload = {
        "race_name": race_name,
        "round": rnd,
        "session_used": session,
        "locked_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "teams": teams,
    }
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    with open(LOCK_PATH, "w") as f:
        json.dump(payload, f, indent=2)

    picks = ", ".join(d["Abbreviation"] for d in teams[0]["drivers"])
    print(f"::notice::Locked {race_name} round {rnd} on {session}. Team 1: {picks}")


if __name__ == "__main__":
    main()
