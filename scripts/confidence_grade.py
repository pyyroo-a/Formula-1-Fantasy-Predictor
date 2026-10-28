"""
Are the confidence levels honest? (project 4)

For every finished 2026 weekend: each driver's level from src/confidence.py, worked
out from the session the weekend locks on (FP3, or sprint quali on sprint weekends)
and the sessions before it. Then how far their lock session rank ended up from where
they really ranked: on the game's official fantasy points, the race finish (finishers
only) and the quali grid. If high confidence really means "trust it more", high should
land closer than low.

Run it by hand, it fetches the sessions (OpenF1 first, FastF1 for what's cached):

    python scripts/confidence_grade.py

Writes every driver row to archive/results/confidence_rows_2026.csv. Re-run after a
few races from Mexico, the cutoffs were picked on R1 to R18 so new races are the
honest test. Never tune the cutoffs to make this look better.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src.confidence import load_weekend_sessions, weekend_confidence
from src.config import results_path
from src.fetch_practice import is_sprint_weekend
from src.official_points import load_official_points

YEAR = 2026
OUT = "archive/results/confidence_rows_2026.csv"
LEVELS = ["high", "medium", "low"]


def _finished(status) -> bool:
    s = str(status)
    return s.startswith(("Finished", "+")) or s == "Lapped"


def places_off(rows: pd.DataFrame, target: str, ascending: bool, finishers_only: bool = False) -> pd.Series:
    """
    Places between each driver's lock session rank and their real rank on target,
    both re-ranked among that round's rows that have the target (and finished, if
    finishers_only). NaN for rows that don't count.
    """
    out = pd.Series(float("nan"), index=rows.index)
    for _, x in rows.groupby("round"):
        x = x.dropna(subset=[target])
        if finishers_only:
            x = x[x["status"].map(_finished)]
        if x.empty:
            continue
        out[x.index] = (x["rank"].rank() - x[target].rank(ascending=ascending)).abs()
    return out


def summarise(rows: pd.DataFrame) -> dict:
    """Per level: n, places off (fantasy points, finish, grid), share within 2 places.
    Plus how many rounds high beat low on fantasy points."""
    rows = rows.assign(fpts_off=places_off(rows, "fpts", ascending=False),
                       finish_off=places_off(rows, "finish", ascending=True, finishers_only=True),
                       grid_off=places_off(rows, "grid", ascending=True))
    out = {}
    for lvl in LEVELS:
        x = rows[rows["level"] == lvl]
        out[lvl] = {"n": len(x), "fpts_off": x["fpts_off"].mean(),
                    "within2": (x["fpts_off"].dropna() <= 2).mean() if x["fpts_off"].notna().any() else float("nan"),
                    "finish_off": x["finish_off"].mean(), "grid_off": x["grid_off"].mean()}
    wins = rounds = 0
    for _, x in rows.groupby("round"):
        hi = x.loc[x["level"] == "high", "fpts_off"].mean()
        lo = x.loc[x["level"] == "low", "fpts_off"].mean()
        if pd.isna(hi) or pd.isna(lo):
            continue
        rounds += 1
        wins += hi < lo
    out["high_beat_low"], out["rounds"] = wins, rounds
    return out


def build_rows() -> pd.DataFrame:
    from src.weekend import load_grid   # heavy import, only needed for the real run

    results = pd.read_csv(results_path(YEAR))
    points = load_official_points()
    rows = []
    for (rnd, race), res in results.groupby(["RoundNumber", "RaceName"]):
        if rnd not in points:
            print(f"R{rnd} {race}: no official points yet, skipped")
            continue
        lock = "SQ" if is_sprint_weekend(race, YEAR) else "FP3"
        try:
            sessions = load_weekend_sessions(lambda s: load_grid(race, s, YEAR), lock)
        except Exception as e:
            print(f"R{rnd} {race}: {lock} wouldn't load ({e}), skipped")
            continue
        conf = weekend_confidence(sessions, lock)
        res = res.set_index("Abbreviation")
        pts = points[rnd].get("drivers", {})
        for _, d in sessions[lock].iterrows():
            a = d["Abbreviation"]
            rows.append({"round": rnd, "race": race, "kind": "sprint" if lock == "SQ" else "normal",
                         "sessions": "+".join(sessions), "driver": a, "rank": int(d["GridPosition"]),
                         "level": conf[a]["level"], "flags": conf[a]["flags"],
                         "grid": res["GridPosition"].get(a), "finish": res["Position"].get(a),
                         "status": res["Status"].get(a), "fpts": pts.get(a, {}).get("points")})
        print(f"R{rnd} {race}: {lock}, sessions {'+'.join(sessions)}, {len(sessions[lock])} drivers")
    return pd.DataFrame(rows)


def _table(rows: pd.DataFrame, title: str) -> str:
    s = summarise(rows)
    lines = [f"\n### {title} ({rows['round'].nunique()} weekends)\n",
             "| Confidence | Driver weekends | Places off, fantasy points | Within 2 places | Places off, finish | Places off, grid |",
             "|---|---:|---:|---:|---:|---:|"]
    for lvl in LEVELS:
        v = s[lvl]
        lines.append(f"| {lvl} | {v['n']} | {v['fpts_off']:.2f} | {v['within2']:.0%} | "
                     f"{v['finish_off']:.2f} | {v['grid_off']:.2f} |")
    lines.append(f"\nHigh beat low on fantasy points in {s['high_beat_low']} of {s['rounds']} weekends.")
    return "\n".join(lines)


def main():
    rows = build_rows()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rows.to_csv(OUT, index=False)
    print(f"\nwrote {len(rows)} rows to {OUT}")
    for kind, title in [("normal", "Normal weekends (FP3)"), ("sprint", "Sprint weekends (sprint quali)")]:
        x = rows[rows["kind"] == kind]
        if not x.empty:
            print(_table(x, title))


if __name__ == "__main__":
    main()
