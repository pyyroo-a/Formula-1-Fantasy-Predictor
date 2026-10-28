"""
Chip history by track (project 6): what 3x, Limitless and No Negative would really have
been worth at each track, so you can weigh up a chip before a race. Facts, not advice.

  3x           the top scoring driver's points that weekend, the extra a 3x adds over
               the 2x. Says who and from where, so a one-off like Antonelli P19 to P1
               at Monza 2026 is out in the open
  No Negative  what an average team would have got back: 7 x the mean, over every
               driver and constructor, of the points they lost below zero
  Limitless    the best team with no budget cap minus the best $100M team. Needs that
               round's prices, so 2026 only for now

Only 2025 and 2026 (my call, same as the model: older seasons are old cars). Kept free
of the model's imports so the Monday GitHub Action can run it.
"""
import pandas as pd

from src import simple_picks
from src.official_points import team_points

CHIPS = ["3x", "Limitless", "No Negative"]

# FastF1's schedule calls the same place different things in different years. The
# 2026 "Bahrain GP" was in Kuala Lumpur, that's a different track, so it stays apart
TRACK_ALIASES = {"Monte Carlo": "Monaco"}


def track_key(location: str) -> str:
    return TRACK_ALIASES.get(location, location)


def _limitless(driver_pts: dict, constructor_pts: dict, prices: dict) -> float:
    top_d = sorted(driver_pts, key=lambda a: (-driver_pts[a], a))[:5]
    top_c = sorted(constructor_pts, key=lambda c: (-constructor_pts[c], c))[:2]
    unlimited = (sum(driver_pts[a] for a in top_d) + driver_pts[top_d[0]]
                 + sum(constructor_pts[c] for c in top_c))
    round_points = {"drivers": {a: {"points": p} for a, p in driver_pts.items()},
                    "constructors": {c: {"points": p} for c, p in constructor_pts.items()}}
    pool = {"drivers": {a: p for a, p in prices.get("drivers", {}).items() if a in driver_pts},
            "constructors": {c: p for c, p in prices.get("constructors", {}).items() if c in constructor_pts}}
    best = simple_picks.hindsight_best_team(round_points, pool)
    capped = team_points([d["Abbreviation"] for d in best["drivers"]], [c["name"] for c in best["constructors"]],
                         best["boost_pick"]["Abbreviation"], round_points)
    return round(unlimited - capped, 1)


def weekend_values(driver_pts: dict, constructor_pts: dict, prices: dict | None,
                   starts: dict, finishes: dict, sprint_missing: bool = False) -> dict:
    """
    What each chip was worth this weekend. driver_pts / constructor_pts are the
    weekend's total points (race + quali + sprint). starts / finishes are race grid and
    finishing positions, just for saying who. A sprint weekend whose sprint results we
    don't have gets None everywhere, never a number that quietly skipped the sprint.
    """
    if sprint_missing:
        return {"3x": None, "No Negative": None, "Limitless": None}

    top = sorted(driver_pts, key=lambda a: (-driver_pts[a], a))[0]
    start, finish = starts.get(top), finishes.get(top)
    where = f" P{int(start)} to P{int(finish)}" if start is not None and finish is not None else ""
    three_x = {"value": float(driver_pts[top]), "who": f"{top}{where}"}

    every = list(driver_pts.values()) + list(constructor_pts.values())
    lost = sum(max(0.0, -p) for p in every) / len(every)
    no_negative = round(7 * lost, 1)

    limitless = _limitless(driver_pts, constructor_pts, prices) if prices else None
    return {"3x": three_x, "No Negative": no_negative, "Limitless": limitless}


def _value(v):
    return v["value"] if isinstance(v, dict) else v


def track_table(weekends: list[dict]) -> list[dict]:
    """
    One row per track: for each chip the median over the weekends that have a number,
    each season's value (with who, for 3x) and how many seasons it's based on.
    weekends are {"season", "round", "track", "name", "sprint", "values"}.
    """
    by_track: dict[str, list[dict]] = {}
    for w in weekends:
        by_track.setdefault(w["track"], []).append(w)

    rows = []
    for track, ws in sorted(by_track.items()):
        ws = sorted(ws, key=lambda w: (w["season"], w["round"]))
        chips = {}
        for chip in CHIPS:
            vals = [{"season": w["season"], "value": _value(w["values"][chip]),
                     "who": (w["values"][chip] or {}).get("who") if chip == "3x" else None}
                    for w in ws if w["values"].get(chip) is not None]
            nums = [v["value"] for v in vals]
            chips[chip] = {"median": round(float(pd.Series(nums).median()), 1) if nums else None,
                           "values": vals, "seasons": len({v["season"] for v in vals})}
        rows.append({"track": track, "name": ws[-1]["name"], "sprint": any(w["sprint"] for w in ws),
                     "chips": chips})
    return rows


def best_tracks(table: list[dict], chip: str, n: int = 3) -> dict:
    """The top n tracks for a chip by median and the worst one. Ties go by track name."""
    have = [{"track": r["track"], "name": r["name"], "median": r["chips"][chip]["median"],
             "seasons": r["chips"][chip]["seasons"]}
            for r in table if r["chips"][chip]["median"] is not None]
    if not have:
        return {"top": [], "worst": None}
    top = sorted(have, key=lambda r: (-r["median"], r["track"]))[:n]
    worst = sorted(have, key=lambda r: (r["median"], r["track"]))[0]
    return {"top": top, "worst": worst}


def rank_check(weekends: list[dict], chip: str, past: int = 2025, future: int = 2026) -> dict:
    """
    Does a track's past say anything about its future? Over tracks raced in both
    seasons: the rank correlation between past and future values, and how many of the
    past's top 5 were really top 5. 1.0 = perfect, 0 = no better than chance.
    """
    def per_track(season):
        vals: dict[str, list[float]] = {}
        for w in weekends:
            v = w["values"].get(chip)
            if w["season"] == season and v is not None:
                vals.setdefault(w["track"], []).append(_value(v))
        return {t: float(pd.Series(v).median()) for t, v in vals.items()}

    a, b = per_track(past), per_track(future)
    both = sorted(set(a) & set(b))
    if len(both) < 3:
        return {"tracks": len(both), "spearman": None, "top5_hits": None}
    s_a, s_b = pd.Series([a[t] for t in both]), pd.Series([b[t] for t in both])
    top = lambda d: set(sorted(both, key=lambda t: (-d[t], t))[:5])
    return {"tracks": len(both), "spearman": round(float(s_a.corr(s_b, method="spearman")), 2),
            "top5_hits": len(top(a) & top(b))}
