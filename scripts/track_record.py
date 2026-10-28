"""
Builds data/track_record_2026.json for the track record page (project 5).

Every weekend PitWall really locked that has official points: what locked team 1
scored, and what the simple picks scored, graded with the same code as the season
scorecard (src/track_record.py). The Monday GitHub Action runs this after it saves the
official points, so the page updates itself. You can run it by hand too:

    python scripts/track_record.py

It loads each locked weekend's deadline practice (OpenF1 first) for the FP3 order
column, so it needs the network. Doesn't need the model's packages.
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.config import SEASON, results_path
from src.fetch_practice import deadline_grid
from src.official_points import load_official_points
from src.snapshots import find_snapshot
from src.track_record import build_rows, summarise

OUT = f"data/track_record_{SEASON}.json"


def main():
    results = pd.read_csv(results_path(SEASON))
    rounds = [(int(rnd), g["RaceName"].iloc[0], list(g["Abbreviation"]))
              for rnd, g in results.groupby("RoundNumber")]
    rows = build_rows(load_official_points(), rounds, deadline_grid, find_snapshot)
    record = {"updated": date.today().isoformat(), "rows": rows, "summary": summarise(rows)}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1)
    print(f"wrote {OUT}: {len(rows)} locked weekends")
    for r in rows:
        print(f"  R{r['round']} {r['race']}: " + ", ".join(f"{k} {v}" for k, v in r["cells"].items()))


if __name__ == "__main__":
    main()
