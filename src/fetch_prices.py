import httpx
import json
import os

F1_FANTASY_BASE = "https://fantasy.formula1.com"


def fetch_prices(race_id: int) -> dict:
    """
    Fetches current driver and constructor prices from the F1 Fantasy feed.

    Args:
        race_id: 1-indexed round number for the season (e.g. 9 = British GP in 2026)

    Returns:
        dict with two keys:
            "drivers"      -> { "VER": 30.5, "NOR": 28.0, ... }
            "constructors" -> { "Red Bull Racing": 30.0, "McLaren": 28.5, ... }
    """
    url = f"{F1_FANTASY_BASE}/feeds/drivers/{race_id}_en.json"
    resp = httpx.get(url)
    resp.raise_for_status()

    items = resp.json()["Data"]["Value"]

    drivers = {}
    constructors = {}

    for item in items:
        price = float(item["Value"])
        if item["PositionName"] == "DRIVER":
            tla = item["DriverTLA"]
            drivers[tla] = price
        elif item["PositionName"] == "CONSTRUCTOR":
            team = item["FUllName"]
            constructors[team] = price

    return {"drivers": drivers, "constructors": constructors}


def save_prices(race_id: int, path: str = "data/prices.json") -> dict:
    """Fetches prices and saves the current snapshot for the backend to read."""
    prices = fetch_prices(race_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"race_id": race_id, "prices": prices}, f, indent=2)
    print(f"Saved prices for race {race_id}: {len(prices['drivers'])} drivers, {len(prices['constructors'])} constructors")
    return prices


def save_price_history(race_id: int, path: str = "data/price_history.json") -> dict:
    """
    Appends this round's prices to a running history file, keyed by round.

    Unlike save_prices (one overwritten snapshot), this keeps every round so we
    can see how prices move over the season. Re-fetching an existing round just
    refreshes it. Returns the full history dict.
    """
    prices = fetch_prices(race_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        with open(path) as f:
            history = json.load(f)
    else:
        history = {}

    history[str(race_id)] = prices
    with open(path, "w") as f:
        json.dump(history, f, indent=2)

    print(f"Saved price history for race {race_id} ({len(history)} rounds stored)")
    return history


def load_prices(path: str = "data/prices.json") -> dict:
    """Loads the current price snapshot from disk."""
    with open(path) as f:
        return json.load(f)["prices"]


def load_current_race_id(path: str = "data/prices.json") -> int:
    """Returns the round the current price snapshot is from (for staleness display)."""
    with open(path) as f:
        return json.load(f)["race_id"]


def fetch_price_changes(current_race_id: int) -> dict:
    """
    Returns current prices with change vs the previous round.
    Each entry: { "price": float, "change": float }
    Positive change = price rose, negative = price dropped.
    """
    current = fetch_prices(current_race_id)

    try:
        previous = fetch_prices(current_race_id - 1)
    except Exception:
        previous = {"drivers": {}, "constructors": {}}

    drivers = {}
    for abbr, price in current["drivers"].items():
        prev = previous["drivers"].get(abbr, price)
        drivers[abbr] = {"price": price, "change": round(price - prev, 1)}

    constructors = {}
    for name, price in current["constructors"].items():
        prev = previous["constructors"].get(name, price)
        constructors[name] = {"price": price, "change": round(price - prev, 1)}

    return {"drivers": drivers, "constructors": constructors}
