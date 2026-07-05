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
    """Fetches prices and saves to a JSON file for the backend to read."""
    prices = fetch_prices(race_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"race_id": race_id, "prices": prices}, f, indent=2)
    print(f"Saved prices for race {race_id}: {len(prices['drivers'])} drivers, {len(prices['constructors'])} constructors")
    return prices


def load_prices(path: str = "data/prices.json") -> dict:
    """Loads saved prices from disk."""
    with open(path) as f:
        return json.load(f)["prices"]
