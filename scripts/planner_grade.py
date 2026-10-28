"""
Grades the transfer ladder on REAL points before it ships (project 3).

Replays 2026 from round 3, walk forward like the scorecard (only info from before each
race), starting from PitWall's team 1 at round 3 with $100M. Then plays the season
three ways (keep, free transfers only, with hits, see src/planner_replay.py) and grades
every race with the official F1 Fantasy points, -10 for every paid transfer.

The two bars: free only has to beat keep or the planner doesn't ship, and with hits
has to beat free only or the paid row gets switched off (SHOW_PAID_ROW).

Usage:
    python scripts/planner_grade.py          # prints a markdown report
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest import predicted_for_round
from src.config import PREVIOUS_SEASON, SEASON, results_path
from src.data_loader import load_dataset
from src.fantasy import build_budget_teams, get_race_pool
from src.official_points import load_official_points
from src.planner import team_cost
from src.planner_replay import play_season

FIRST_ROUND = 3
START_BUDGET = 100.0


def build_rounds(official: dict, df_previous, df_current) -> tuple[list[dict], dict, float, list[str]]:
    """Every graded round, the start team, its bank, and a note per race that fell back."""
    rounds, notes = [], []
    start, bank = None, None
    for rnd in sorted(r for r in df_current["RoundNumber"].unique() if r >= FIRST_ROUND):
        rnd = int(rnd)
        if rnd not in official:
            notes.append(f"R{rnd}: no official points, stopped here")
            break
        prices = official[rnd]["prices"]
        race, table, session = predicted_for_round(rnd, df_previous, df_current)
        if session not in ("FP3", "SQ"):
            notes.append(f"R{rnd} {race}: used {session or 'no practice'}, not the deadline session. "
                         "OpenF1 sometimes drops one, run it again")
        pool = get_race_pool(table, race, prices) if table is not None else None
        if start is None:
            team = build_budget_teams(table, race, prices, budget=START_BUDGET)[0]
            start = {"drivers": [d["Abbreviation"] for d in team["drivers"]],
                     "constructors": [c["name"] for c in team["constructors"]]}
            bank = round(START_BUDGET - team_cost(start["drivers"], start["constructors"], prices), 1)
        rounds.append({"round": rnd, "race": race, "pool": pool, "prices": prices, "points": official[rnd]})
        print(f"R{rnd} {race}: ready", file=sys.stderr)
    return rounds, start, bank, notes


def _head_to_head(a: dict, b: dict) -> str:
    pairs = list(zip(a["per_round"], b["per_round"]))
    won = sum(1 for x, y in pairs if x["points"] > y["points"])
    lost = sum(1 for x, y in pairs if x["points"] < y["points"])
    return f"won {won}, lost {lost}, tied {len(pairs) - won - lost}"


def report(rounds: list[dict], start: dict, seasons: dict, notes: list[str]) -> str:
    keep, free, hits = seasons["keep"], seasons["free_only"], seasons["with_hits"]
    lines = [
        "## Planner grade",
        "",
        f"Rounds {rounds[0]['round']} to {rounds[-1]['round']} of {SEASON}, official F1 Fantasy points, "
        f"-10 per paid transfer. Start: PitWall's R{rounds[0]['round']} team 1 at ${START_BUDGET:.0f}M "
        f"({', '.join(start['drivers'] + start['constructors'])}).",
        "",
        "| Way to play | Real pts/race | Transfers used | Hits paid |",
        "|---|---:|---:|---:|",
    ]
    for name, label in (("keep", "Keep the team"), ("free_only", "Free transfers only"), ("with_hits", "With hits")):
        s = seasons[name]
        lines.append(f"| {label} | {s['average']:.1f} | {sum(r['transfers'] for r in s['per_round'])} | {s['hits']} |")
    lines += [
        "",
        f"- Bar 1, free only vs keep: {free['average'] - keep['average']:+.1f} pts/race, {_head_to_head(free, keep)}.",
        f"- Bar 2, with hits vs free only: {hits['average'] - free['average']:+.1f} pts/race, {_head_to_head(hits, free)}.",
        "",
        "| Race | Keep | Free only | With hits |",
        "|---|---:|---:|---:|",
    ]
    for rnd, k, f, h in zip(rounds, keep["per_round"], free["per_round"], hits["per_round"]):
        def cell(r):
            extra = f" ({r['transfers']}t" + (f", {r['paid']} paid" if r["paid"] else "") + ")" if r["transfers"] else ""
            return f"{r['points']:.0f}{extra}"
        lines.append(f"| R{rnd['round']} {rnd['race']} | {cell(k)} | {cell(f)} | {cell(h)} |")
    if notes:
        lines += ["", "Notes:"] + [f"- {n}" for n in notes]
    return "\n".join(lines) + "\n"


def main():
    official = load_official_points()
    df_previous = load_dataset(results_path(PREVIOUS_SEASON))
    df_current = load_dataset(results_path(SEASON))
    rounds, start, bank, notes = build_rounds(official, df_previous, df_current)
    seasons = {s: play_season(rounds, start, bank, s) for s in ("keep", "free_only", "with_hits")}
    print(report(rounds, start, seasons, notes))


if __name__ == "__main__":
    main()
