"""
Builds data/chip_history.json for the CHIPS tab (project 6).

Every 2025 and 2026 race weekend: what 3x, Limitless and No Negative would really have
been worth (src/chip_history.py), grouped by track, the best tracks per chip, and the
honest check of whether 2025's ranking predicted 2026's.

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

from src.chip_history import CHIPS, best_tracks, rank_check, track_key, track_table, weekend_values
from src.official_points import load_official_points

OUT = "data/chip_history.json"
PROCESSED = "data/processed"


def _locations(year: int) -> dict[int, str]:
    s = fastf1.get_event_schedule(year, include_testing=False)
    return {int(r["RoundNumber"]): r["Location"] for _, r in s.iterrows()}


def _positions(rows: pd.DataFrame) -> tuple[dict, dict]:
    starts = {a: g for a, g in zip(rows["Abbreviation"], rows["GridPosition"]) if pd.notna(g)}
    finishes = {a: p for a, p in zip(rows["Abbreviation"], rows["Position"]) if pd.notna(p)}
    return starts, finishes


def _sprints(year: int) -> pd.DataFrame:
    path = f"{PROCESSED}/sprint_results_{year}.csv"
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=["RoundNumber"])


def weekends_2026(official: dict) -> list[dict]:
    results = pd.read_csv(f"{PROCESSED}/race_results_2026.csv")
    sprint_rounds = set(_sprints(2026)["RoundNumber"].astype(int))
    where = _locations(2026)
    out = []
    for rnd, rows in results.groupby("RoundNumber"):
        rnd = int(rnd)
        rp = official.get(rnd)
        if not rp:
            continue
        there = set(rows["Abbreviation"])
        drivers = {a: v["points"] for a, v in rp["drivers"].items() if a in there}
        constructors = {c: v["points"] for c, v in rp["constructors"].items()}
        starts, finishes = _positions(rows)
        out.append({"season": 2026, "round": rnd, "track": track_key(where[rnd]),
                    "name": rows["RaceName"].iloc[0], "sprint": rnd in sprint_rounds,
                    "values": weekend_values(drivers, constructors, rp.get("prices"), starts, finishes)})
    return out


def main():
    logging.getLogger("fastf1").setLevel(logging.WARNING)
    # the Monday Action starts with no cache folder, and FastF1 won't make it itself
    os.makedirs("data/cache", exist_ok=True)
    fastf1.Cache.enable_cache("data/cache")
    weekends = weekends_2026(load_official_points())
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
