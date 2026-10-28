"""
The season scorecard: is PitWall actually better than just guessing?

Grades every 2026 race with the game's OWN points (data/official_points_2026.json, see
src/official_points.py), never our version of the rules. Six columns:

  * Locked:          the team 1 PitWall really locked that weekend (from round 13 on)
  * PitWall replay:  the same thing replayed walk forward, only info from before the race
  * FP3 order, Most expensive, Crowd: model-free picks, see src/simple_picks.py
  * Hindsight best:  the best team you could have had, the ceiling

Everything at $100M, each race a fresh team. Anything we don't have is a "-" with the
reason underneath, never a 0.

Usage:
    python scripts/scorecard.py                    # writes Fantasy Predictor/Scorecard.md
    python scripts/scorecard.py --stdout           # just prints it
    python scripts/scorecard.py --rules current    # which forecast rules the replay uses
"""
import argparse
import os
import sys
from contextlib import contextmanager
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.fantasy as fantasy
import src.simple_picks as simple_picks
from src.backtest import MIN_HISTORY_ROUNDS, deadline_grid, run_backtest
from src.config import SEASON, results_path
from src.data_loader import load_dataset
from src.official_points import load_official_points, team_points
from src.snapshots import find_snapshot

REPORT_PATH = "Fantasy Predictor/Scorecard.md"

COLUMNS = ["Locked", "PitWall replay", "FP3 order", "Most expensive", "Crowd", "Hindsight best"]
SIMPLE = ["FP3 order", "Most expensive", "Crowd", "Hindsight best"]

# which forecast switches in src/fantasy.py each --rules name turns on. join them with +
# to measure them together, e.g. --rules quali+bonus
RULES = {
    "current": {},
    "quali": {"REAL_QUALI_RULES": True},
    "bonus": {"REAL_CONSTRUCTOR_QUALI_BONUS": True},
    "clip": {"CLIP_TO_REAL_FIELD": True},
    "quirks": {"FIX_CONSTRUCTOR_QUIRKS": True},
    "extras": {"USE_CONSTRUCTOR_EXTRAS": True},
}
# every switch at once
RULES["all"] = {k: v for switches in RULES.values() for k, v in switches.items()}


def switches_for(name: str) -> dict:
    """The switches a --rules name turns on, e.g. "quali+bonus" turns on both."""
    switches = {}
    for part in name.split("+"):
        if part not in RULES:
            raise ValueError(f"unknown rules {part!r}, pick from {sorted(RULES)}")
        switches.update(RULES[part])
    return switches


@contextmanager
def rules(**switches):
    """Flips forecast switches in src/fantasy.py for a replay, then puts them back."""
    old = {k: getattr(fantasy, k) for k in switches}
    for k, v in switches.items():
        setattr(fantasy, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(fantasy, k, v)


def _graded(team: dict, round_points: dict) -> float:
    return team_points(
        [d["Abbreviation"] for d in team["drivers"]],
        [c["name"] for c in team["constructors"]],
        (team.get("boost_pick") or {}).get("Abbreviation"),
        round_points,
    )


def _names(team: dict) -> list[str]:
    return [d["Abbreviation"] for d in team["drivers"]] + [c["name"] for c in team["constructors"]]


def _signature(drivers, constructors, boost) -> tuple:
    return frozenset(drivers), frozenset(constructors), boost


def _replay_matches_lock(locked: list, replay: dict | None) -> bool | None:
    """Did the replay pick exactly the team PitWall locked, 2x included? None if no lock."""
    if not locked or not replay or not replay.get("drivers"):
        return None
    team = locked[0]
    lock = _signature(_names(team)[:5], [c["name"] for c in team["constructors"]],
                      (team.get("boost_pick") or {}).get("Abbreviation"))
    again = _signature([d["Abbreviation"] for d in replay["drivers"]],
                       [c["name"] for c in replay["constructors"]],
                       next((d["Abbreviation"] for d in replay["drivers"] if d.get("is_boost")), None))
    return lock == again


def grade_round(rnd: int, race: str, round_points: dict | None, prices: dict | None,
                grid, snapshot: dict | None, replay: dict | None,
                entry: list[str] | None = None) -> dict:
    """
    One race's line of the scorecard. cells[column] is the real score or None, and
    why[column] says why it's missing. teams[column] is who each column picked.

    The simple columns only get drivers who were actually there that weekend (on the
    deadline grid, or in the race entry when there's no grid). The price list keeps
    drivers who've left, and nobody could have picked them.

    replay_matches_lock: whether the replay rebuilt the exact locked team (None if the
    weekend wasn't locked). If it doesn't, the replay isn't really PitWall.
    """
    cells = {c: None for c in COLUMNS}
    why: dict[str, str] = {}
    teams: dict[str, list[str]] = {}
    locked = (snapshot or {}).get("teams") or []
    # the deadline session is FP3, or sprint quali (SQ). anything else means FP3 didn't
    # load and the replay used an earlier session, a different grid than live would have
    used = (replay or {}).get("session_used")
    row = {"round": rnd, "race": race, "cells": cells, "why": why, "teams": teams,
           "replay_matches_lock": _replay_matches_lock(locked, replay),
           "replay_fallback": used if used not in (None, "FP3", "SQ") else None}

    if round_points is None:
        for c in COLUMNS:
            why[c] = "no official points for this round"
        return row

    # what PitWall locked that weekend, team 1
    if locked:
        cells["Locked"] = _graded(locked[0], round_points)
        teams["Locked"] = _names(locked[0])
    else:
        why["Locked"] = "not locked, the weekend lock started at round 13"

    if replay and replay.get("model_score") is not None:
        cells["PitWall replay"] = replay["model_score"]
    elif rnd <= MIN_HISTORY_ROUNDS:
        why["PitWall replay"] = f"the model needs {MIN_HISTORY_ROUNDS} races of 2026 form first"
    else:
        why["PitWall replay"] = (replay or {}).get("error") or "no replay for this round"

    if grid is not None:
        there = set(grid["Abbreviation"])
    else:
        there = set(entry or prices.get("drivers", {}))
    pool = {"drivers": {a: p for a, p in prices.get("drivers", {}).items() if a in there},
            "constructors": prices.get("constructors", {})}

    picks = {
        "Most expensive": simple_picks.most_expensive_team(pool),
        "Hindsight best": simple_picks.hindsight_best_team(round_points, pool),
    }
    if grid is not None:
        picks["FP3 order"] = simple_picks.fp3_order_team(grid, pool)
    else:
        why["FP3 order"] = "no practice grid loaded"
    ownership = (snapshot or {}).get("ownership")
    if ownership:
        picks["Crowd"] = simple_picks.crowd_team(ownership, pool)
    else:
        why["Crowd"] = "no ownership saved at the lock, we only started saving it after the US GP"

    for col, team in picks.items():
        if team is None:
            why[col] = "no legal team under $100M"
            continue
        cells[col] = _graded(team, round_points)
        teams[col] = _names(team)

    return row


def _avg(values: list[float]) -> tuple[float | None, int]:
    if not values:
        return None, 0
    return round(sum(values) / len(values), 1), len(values)


def summarise(rows: list[dict]) -> dict:
    """
    average: per column, over the races that column exists for (and how many).
    average_on_replay_races: the same, but only races the replay has, so it's like
        for like against PitWall.
    replay_beat: per simple column, (races the replay scored MORE, races both exist).
    """
    replay_rows = [r for r in rows if r["cells"]["PitWall replay"] is not None]
    out = {"average": {}, "average_on_replay_races": {}, "replay_beat": {}}
    for col in COLUMNS:
        out["average"][col] = _avg([r["cells"][col] for r in rows if r["cells"][col] is not None])
        out["average_on_replay_races"][col] = _avg(
            [r["cells"][col] for r in replay_rows if r["cells"][col] is not None])
    for col in SIMPLE:
        both = [r for r in replay_rows if r["cells"][col] is not None]
        wins = sum(1 for r in both if r["cells"]["PitWall replay"] > r["cells"][col])
        out["replay_beat"][col] = (wins, len(both))
    return out


def _cell(value) -> str:
    return "-" if value is None else f"{value:.1f}"


def _avg_cell(pair) -> str:
    value, n = pair
    return "-" if value is None else f"{value:.1f} ({n})"


def _rounds_text(rounds: list[int]) -> str:
    return ", ".join(f"R{r}" for r in rounds)


def render(rows: list[dict], rules_name: str, today: str) -> str:
    s = summarise(rows)
    lines = [
        "---",
        "title: Scorecard",
        f"date: {today}",
        "tags: [pitwall, scorecard]",
        "---",
        "",
        "# Scorecard",
        "",
        f"Made on {today} with `python scripts/scorecard.py --rules {rules_name}`, so the "
        f"replay uses the `{rules_name}` forecast rules. Every team is graded the same way and "
        "all points are official F1 Fantasy points, straight from the game's own feed "
        "(`data/official_points_2026.json`), not our version of the rules.",
        "",
        "- **Locked**: team 1 of what PitWall really locked that weekend.",
        "- **PitWall replay**: the same build replayed walk forward, only using what was known "
        "before that race (FP3, or sprint quali on sprint weekends).",
        "- **FP3 order**: the fastest cars in that session that fit, no model.",
        "- **Most expensive**: spend as much of the $100M as possible.",
        "- **Crowd**: the most owned team that fits, from the ownership saved at the lock.",
        "- **Hindsight best**: the best team you could have had, the ceiling.",
        "",
        "Everything is at $100M, each race a fresh team (no transfer limits), and everyone gets "
        "a 2x pick. A \"-\" means we don't have it, the reasons are under the table.",
        "",
        "| Race | " + " | ".join(COLUMNS) + " |",
        "|---|" + "---:|" * len(COLUMNS),
    ]
    for r in rows:
        lines.append(f"| R{r['round']} {r['race']} | "
                     + " | ".join(_cell(r["cells"][c]) for c in COLUMNS) + " |")
    lines.append("| **Average per race (races)** | "
                 + " | ".join(_avg_cell(s["average"][c]) for c in COLUMNS) + " |")
    lines.append("| **Average on the replay's races** | "
                 + " | ".join(_avg_cell(s["average_on_replay_races"][c]) for c in COLUMNS) + " |")
    beat = []
    for c in COLUMNS:
        if c in SIMPLE:
            wins, n = s["replay_beat"][c]
            beat.append(f"{wins} of {n}" if n else "-")
        else:
            beat.append("")
    lines.append("| **Races the replay beat it** | " + " | ".join(beat) + " |")

    checked = [r for r in rows if r.get("replay_matches_lock") is not None]
    if checked:
        off = [r for r in checked if not r["replay_matches_lock"]]
        line = (f"With these rules the replay rebuilt the exact locked team on "
                f"{len(checked) - len(off)} of {len(checked)} locked weekends")
        line += (f", not on {_rounds_text([r['round'] for r in off])}." if off else ".")
        lines += ["", line]

    fell_back = [r for r in rows if r.get("replay_fallback")]
    if fell_back:
        lines += ["", "The replay fell back to an earlier practice session (FP3 didn't load) on "
                  + ", ".join(f"R{r['round']} ({r['replay_fallback']})" for r in fell_back)
                  + ", so those races aren't graded on the grid live would have used. "
                  "Run it again if that's a one-off."]

    # why the gaps, grouped so it's one line per reason
    reasons: dict[tuple[str, str], list[int]] = {}
    for r in rows:
        for col in COLUMNS:
            if r["cells"][col] is None and col in r["why"]:
                reasons.setdefault((col, r["why"][col]), []).append(r["round"])
    if reasons:
        lines += ["", "Why some cells are \"-\":", ""]
        for (col, reason), rounds in reasons.items():
            lines.append(f"- **{col}**, {_rounds_text(rounds)}: {reason}.")

    lines += ["", "Related: [Decisions and evidence](Decisions%20and%20evidence.md), "
                  "[Fantasy scoring](Fantasy%20scoring.md), [Start here](README.md)", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default="current",
                    help=f"one of {sorted(RULES)}, or several joined with +")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing the note")
    args = ap.parse_args()

    official = load_official_points()
    results = load_dataset(results_path(SEASON))

    with rules(**switches_for(args.rules)):
        replay = run_backtest(use_practice=True, official=official)
    replay_by_round = {r["round"]: r for r in replay["races"]}

    rows = []
    for rnd in sorted(results["RoundNumber"].unique()):
        rnd = int(rnd)
        race_rows = results[results["RoundNumber"] == rnd]
        race = race_rows["RaceName"].iloc[0]
        round_points = official.get(rnd)
        grid, _ = deadline_grid(race)
        rows.append(grade_round(
            rnd, race, round_points, (round_points or {}).get("prices"), grid,
            find_snapshot(race), replay_by_round.get(rnd),
            entry=list(race_rows["Abbreviation"]),
        ))
        print(f"R{rnd} {race}: done", file=sys.stderr)

    text = render(rows, args.rules, date.today().isoformat())
    if args.stdout:
        print(text)
    else:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
