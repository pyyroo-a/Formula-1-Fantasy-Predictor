"""
Backup way to lock a race weekend: builds its snapshot on your own laptop.

Normally you don't need this. POST /snapshot/auto on Render does it by itself once
final practice is published (see docs/SNAPSHOTS.md). Use this if that didn't happen,
for example the scheduler was switched off or the GitHub token expired.

It builds exactly the same snapshot the automatic one would, then saves it into
data/snapshots/. You commit and push it, and the site picks it up after Render
redeploys.

Usage:
    python scripts/lock_team.py                          # the next race weekend
    python scripts/lock_team.py --race "Spanish Grand Prix"
    python scripts/lock_team.py --race "..." --force     # replace an existing snapshot
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fastf1
import pandas as pd

from src.fetch_prices import fetch_prices
from src.snapshots import find_snapshot, save_snapshot, snapshot_path
from src.weekend import build_snapshot, final_practice_session, results_already_in_data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", help="Event name, e.g. 'Spanish Grand Prix'")
    ap.add_argument("--force", action="store_true", help="Replace an existing snapshot for that race")
    args = ap.parse_args()

    fastf1.Cache.enable_cache("data/cache")
    schedule = fastf1.get_event_schedule(2026, include_testing=False)

    if args.race:
        match = schedule[schedule["EventName"] == args.race]
        if match.empty:
            sys.exit(f"No 2026 event called {args.race!r}.")
        event = match.iloc[0]
    else:
        # the next race that hasn't started yet
        now = pd.Timestamp.now(tz="UTC")
        upcoming = [
            e for _, e in schedule.sort_values("RoundNumber").iterrows()
            if pd.notna(e["Session5Date"]) and pd.Timestamp(e["Session5Date"]) > now
        ]
        if not upcoming:
            sys.exit("No races left this season.")
        event = upcoming[0]

    race = event["EventName"]
    rnd = int(event["RoundNumber"])

    if find_snapshot(race) and not args.force:
        print(f"{race} already has a snapshot ({snapshot_path(2026, rnd, race)}). Use --force to replace it.")
        return

    # if the results are already in, the model would have seen the answers
    if results_already_in_data(race):
        sys.exit(f"{race} results are already in the data, so a snapshot now would be cheating. Not building it.")

    session = final_practice_session(event)
    print(f"Building {race} (round {rnd}) from {session}...")

    # no try/except on purpose: if something breaks you see the real error
    snap = build_snapshot(event, fetch_prices(rnd), source="manual")
    path = save_snapshot(snap, force=args.force)

    print(f"Saved {path}")
    for i, t in enumerate(snap["teams"], 1):
        drivers = ", ".join(d["Abbreviation"] for d in t["drivers"])
        constructors = ", ".join(c["name"] for c in t["constructors"])
        print(f"  team {i}: {drivers} | {constructors} | {t['total_score']} pts")
    if snap.get("built_after_quali_start"):
        print("  heads up: qualifying had already started, so this is too late for the fantasy deadline")
    print("\nNow commit it:  git add data/snapshots && git commit -m \"snapshot for " + race + "\" && git push")


if __name__ == "__main__":
    main()
