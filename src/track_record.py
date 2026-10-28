"""
The track record (project 5): what PitWall's locked team really scored each weekend,
against simple picks anyone could make, all in the game's official points.

The grading here is shared with the season scorecard (scripts/scorecard.py), so the
site and the scorecard note can never disagree. The scorecard adds its replay column
on top. Kept free of the model's imports on purpose, the Monday GitHub Action runs it
with just fastf1, pandas and httpx installed.
"""
from src import simple_picks
from src.official_points import team_points

SIMPLE_COLUMNS = ["Locked", "FP3 order", "Most expensive", "Crowd", "Hindsight best"]
PICK_COLUMNS = ["FP3 order", "Most expensive", "Crowd", "Hindsight best"]


def graded(team: dict, round_points: dict) -> float:
    return team_points(
        [d["Abbreviation"] for d in team["drivers"]],
        [c["name"] for c in team["constructors"]],
        (team.get("boost_pick") or {}).get("Abbreviation"),
        round_points,
    )


def names(team: dict) -> list[str]:
    return [d["Abbreviation"] for d in team["drivers"]] + [c["name"] for c in team["constructors"]]


def grade_simple(round_points: dict, prices: dict, grid, snapshot: dict | None,
                 entry: list[str] | None) -> tuple[dict, dict, dict]:
    """
    (cells, why, teams) for the locked team and the model free picks of one raced round.

    The simple columns only get drivers who were actually there that weekend (on the
    deadline grid, or in the race entry when there's no grid). The price list keeps
    drivers who've left, and nobody could have picked them.
    """
    cells = {c: None for c in SIMPLE_COLUMNS}
    why: dict[str, str] = {}
    teams: dict[str, list[str]] = {}

    # what PitWall locked that weekend, team 1
    locked = (snapshot or {}).get("teams") or []
    if locked:
        cells["Locked"] = graded(locked[0], round_points)
        teams["Locked"] = names(locked[0])
    else:
        why["Locked"] = "not locked, the weekend lock started at round 13"

    if grid is not None:
        there = set(grid["Abbreviation"])
    else:
        there = set(entry or prices.get("drivers", {}))
    pool = {"drivers": {a: p for a, p in prices.get("drivers", {}).items() if a in there},
            "constructors": prices.get("constructors", {})}

    picks = {"Hindsight best": simple_picks.hindsight_best_team(round_points, pool)}
    # thousands of teams spend exactly $100.0M, so this column is their average score,
    # not one of them picked by the alphabet (see most_expensive_teams)
    priciest = simple_picks.most_expensive_teams(pool)
    if priciest:
        scores = [graded(t, round_points) for t in priciest]
        cells["Most expensive"] = round(sum(scores) / len(scores), 1)
        teams["Most expensive"] = sorted({n for t in priciest for n in names(t)})
    else:
        why["Most expensive"] = "no legal team under $100M"
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
        cells[col] = graded(team, round_points)
        teams[col] = names(team)

    return cells, why, teams


def build_rows(official: dict, rounds: list, load_grid, find_snapshot) -> list[dict]:
    """
    One row per weekend PitWall really locked AND that has official points. rounds is
    [(round, race, entry)], load_grid(race) gives (grid, session used) like
    deadline_grid, find_snapshot(race) the locked snapshot or None.
    """
    rows = []
    for rnd, race, entry in rounds:
        snapshot = find_snapshot(race)
        round_points = official.get(rnd)
        if not snapshot or not round_points:
            continue
        grid, _ = load_grid(race)
        cells, why, _ = grade_simple(round_points, round_points.get("prices") or {}, grid, snapshot, entry)
        rows.append({"round": rnd, "race": race, "cells": cells, "why": why})
    return rows


def summarise(rows: list[dict]) -> dict:
    """
    Average per race for every column (only races where it has a number), and for each
    simple pick how often PitWall's locked team beat it. A tie isn't a win.
    """
    out = {}
    for col in SIMPLE_COLUMNS:
        vals = [r["cells"][col] for r in rows if r["cells"].get(col) is not None]
        out[col] = {"avg": round(sum(vals) / len(vals), 1) if vals else None, "races": len(vals)}
    for col in PICK_COLUMNS:
        both = [r for r in rows if r["cells"].get("Locked") is not None and r["cells"].get(col) is not None]
        out[col]["beaten"] = sum(r["cells"]["Locked"] > r["cells"][col] for r in both)
        out[col]["of"] = len(both)
    return out
