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

    return parse_price_feed(resp.json()["Data"]["Value"])


def parse_price_feed(items: list[dict]) -> dict:
    """
    Turns the raw feed rows into the two price dicts.

    The catch: when a driver changes team mid-season the feed KEEPS the old pairing
    as a second row with the same TLA, marked IsActive 0 and frozen at the price it
    had back then. So we can get LAW twice, and the stale row can come last:

        LAW   9.3  IsActive 1  Liam Lawson  Racing Bulls      <- the real one
        LAW  15.1  IsActive 0  Liam Lawson  Red Bull Racing   <- old pairing

    This used to be a plain dict assignment, so last row won and rounds 15, 16 and
    17 all stored Lawson at 15.1 instead of 9.7, 9.1 and 9.3. Rounds 12 to 14 were
    only right by luck, the active row happened to be last.

    So an active row always beats an inactive one, whatever the order. But we don't
    just filter the inactive ones out: IsActive describes the CURRENT roster, not
    who raced in that round, so in an old round's feed a driver who has since moved
    has no active row at all (Hadjar in round 12). Dropping those would punch holes
    in price_history. An inactive row is therefore still used when it's all we have.

    Side effect we're living with for now: a driver who has left the grid entirely
    keeps his last price (Tsunoda at 9.7 from round 15 on). He has no practice laps
    so he never reaches a team, he just sits in the price list.
    """
    drivers: dict[str, float] = {}
    constructors: dict[str, float] = {}
    driver_active: dict[str, bool] = {}

    for item in items:
        price = float(item["Value"])
        active = str(item.get("IsActive")) == "1"

        if item["PositionName"] == "DRIVER":
            tla = item["DriverTLA"]
            # first row for this driver, or the first ACTIVE one, wins
            if tla not in drivers or (active and not driver_active[tla]):
                drivers[tla] = price
                driver_active[tla] = active
        elif item["PositionName"] == "CONSTRUCTOR":
            constructors[item["FUllName"]] = price

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
