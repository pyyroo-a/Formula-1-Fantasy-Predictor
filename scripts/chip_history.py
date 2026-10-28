"""
Builds data/chip_history.json for the CHIPS tab (project 6).

Every race weekend we have the game's official points for: what 3x, Limitless and No
Negative would really have been worth (src/chip_history.py), grouped by track, the best
tracks per chip, and (once there are two seasons) the honest check of whether last
season's ranking predicted this one's. A new season joins by itself as soon as its
data/official_points_YYYY.json exists.

  Only seasons with the game's own official points, so 2026 for now, and every new
  season gets added as it's raced. We tried 2025 with our own scoring of the results,
  but our maths only counts the basics (a pole to win weekend came out at 35 almost
  everywhere, the real game gave 45 to 93 in 2026), so it made every track look the
  same. 2025 still trains the model, it just isn't used here.

The Monday GitHub Action runs this after the track record. By hand:

    python scripts/chip_history.py
"""
import json
import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fastf1
import pandas as pd

from src.chip_history import (CHIPS, best_tracks, official_seasons, rank_check, sprint_rounds, track_key,
                               track_table, weekend_values)
from src.official_points import load_official_points

OUT = "data/chip_history.json"
PROCESSED = "data/processed"


def weekends_for(year: int, official: dict) -> list[dict]:
    """One season's weekends, official points only."""
    results = pd.read_csv(f"{PROCESSED}/race_results_{year}.csv")
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    where = {int(r["RoundNumber"]): r["Location"] for _, r in schedule.iterrows()}
    sprints = sprint_rounds(schedule)
    out = []
    for rnd, rows in results.groupby("RoundNumber"):
        rnd = int(rnd)
        rp = official.get(rnd)
        if not rp or rnd not in where:
            continue
        there = set(rows["Abbreviation"])
        drivers = {a: v["points"] for a, v in rp["drivers"].items() if a in there}
        constructors = {c: v["points"] for c, v in rp["constructors"].items()}
        starts = {a: g for a, g in zip(rows["Abbreviation"], rows["GridPosition"]) if pd.notna(g)}
        finishes = {a: f for a, f in zip(rows["Abbreviation"], rows["Position"]) if pd.notna(f)}
        out.append({"season": year, "round": rnd, "track": track_key(where[rnd]),
                    "name": rows["RaceName"].iloc[0], "sprint": rnd in sprints,
                    "values": weekend_values(drivers, constructors, rp.get("prices"), starts, finishes)})
    return out


def main():
    logging.getLogger("fastf1").setLevel(logging.WARNING)
    # the Monday Action starts with no cache folder, and FastF1 won't make it itself
    os.makedirs("data/cache", exist_ok=True)
    fastf1.Cache.enable_cache("data/cache")
    weekends = []
    for year in official_seasons("data"):
        weekends += weekends_for(year, load_official_points(f"data/official_points_{year}.json"))
    table = track_table(weekends)
    seasons = sorted({w["season"] for w in weekends})
    # the honest check needs two official seasons: does last season's ranking predict this one's
    check = ({c: rank_check(weekends, c, seasons[-2], seasons[-1]) for c in CHIPS} if len(seasons) >= 2
             else {c: {"tracks": 0, "spearman": None, "top5_hits": None} for c in CHIPS})
    record = {"updated": date.today().isoformat(), "seasons": seasons, "tracks": table,
              "best": {c: best_tracks(table, c) for c in CHIPS}, "check": check}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1)

    print(f"wrote {OUT}: {len(weekends)} weekends, {len(table)} tracks")
    for c in CHIPS:
        b = record["best"][c]
        top = ", ".join(f"{t['name'].replace(' Grand Prix', '')} {t['median']}" for t in b["top"])
        worst = b["worst"]
        print(f"  {c}: best {top} | worst {worst['name'].replace(' Grand Prix', '')} {worst['median']}"
              if worst else f"  {c}: nothing yet")
        print(f"     check: {record['check'][c]}")


if __name__ == "__main__":
    main()
