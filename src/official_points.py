"""
The points referee: the game's OWN points for every driver and constructor, per round.

Basically the F1 Fantasy feed we already read prices from (`feeds/drivers/<round>_en.json`)
also carries what everyone actually scored that round, split into qualifying, race and
sprint. Each round's feed keeps its own round's points, so we can grade every race this
season with the real numbers instead of our own version of the rules.

We used to grade with our own maths (src/backtest.py), and our maths had holes: -5 for
qualifying P16 or worse (the game only does -5 for no time), the wrong constructor
qualifying bonus, and no pit stop points at all. Checked against my real US GP team:
the feed adds up to exactly 238, same as the app.

Saved per round in data/official_points_2026.json so the scorecard doesn't need the
network, and so we keep the numbers even if the feed changes later.
"""
import json
import os

import httpx

from src.fetch_prices import F1_FANTASY_BASE, parse_price_feed

OFFICIAL_POINTS_PATH = "data/official_points_2026.json"


def _num(value) -> float:
    # the feed sends numbers as strings, and "" when a session didn't happen
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _points(item: dict) -> dict:
    return {
        "points": _num(item.get("GamedayPoints")),
        "qualifying": _num(item.get("QualifyingPoints")),
        "race": _num(item.get("RacePoints")),
        "sprint": _num(item.get("SprintPoints")),
    }


def parse_official_points(items: list[dict]) -> dict:
    """
    Turns the raw feed rows into each driver's and constructor's points for that round.

    Same duplicate trap as prices (see parse_price_feed): after a team move the feed keeps
    the old pairing as a second row with the same driver code. Checked on every round of
    2026, the active row is the one with the points and the old one has 0, so the active
    row wins whatever the order.
    """
    drivers: dict[str, dict] = {}
    driver_active: dict[str, bool] = {}
    constructors: dict[str, dict] = {}

    for item in items:
        active = str(item.get("IsActive")) == "1"
        if item["PositionName"] == "DRIVER":
            tla = item["DriverTLA"]
            if tla not in drivers or (active and not driver_active[tla]):
                drivers[tla] = _points(item)
                driver_active[tla] = active
        elif item["PositionName"] == "CONSTRUCTOR":
            constructors[item["FUllName"]] = _points(item)

    return {"drivers": drivers, "constructors": constructors}


def fetch_official_points(round_number: int) -> dict:
    """One round's official points from the feed, plus that round's prices."""
    url = f"{F1_FANTASY_BASE}/feeds/drivers/{round_number}_en.json"
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    items = resp.json()["Data"]["Value"]
    return {**parse_official_points(items), "prices": parse_price_feed(items)}


def is_raced(round_points: dict) -> bool:
    """A round that hasn't happened yet has every driver on 0, that's not a result."""
    return any(d["points"] != 0.0 for d in round_points.get("drivers", {}).values())


def load_official_points(path: str = OFFICIAL_POINTS_PATH) -> dict[int, dict]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {int(k): v for k, v in json.load(f).items()}


def save_official_round(round_number: int, round_points: dict,
                        path: str = OFFICIAL_POINTS_PATH) -> None:
    data = load_official_points(path)
    data[round_number] = round_points
    with open(path, "w", encoding="utf-8") as f:
        json.dump({str(k): data[k] for k in sorted(data)}, f, indent=1, ensure_ascii=False)
        f.write("\n")


def team_points(drivers: list[str], constructors: list[str], boost: str | None,
                round_points: dict) -> float:
    """What a team really scored that round. The 2x driver counts twice."""
    d = round_points["drivers"]
    c = round_points["constructors"]
    total = sum(d.get(a, {}).get("points", 0.0) for a in drivers)
    if boost:
        total += d.get(boost, {}).get("points", 0.0)
    total += sum(c.get(n, {}).get("points", 0.0) for n in constructors)
    return round(total, 1)
