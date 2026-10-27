"""
Model-free teams to grade PitWall against on the scorecard.

If PitWall can't beat these, I could basically just guess. Each one only uses what a
person could see before the deadline (except hindsight best, which is the ceiling):

  * copy the FP3 order:     the fastest cars in final practice (or sprint quali)
  * most expensive that fit: spend as much of the $100M as possible
  * copy the crowd:         the most owned team, from the ownership saved at the lock
  * hindsight best:         the best team you could have had, knowing the real points

None of them touch FantasyValue or the model. Every team is 5 drivers and 2
constructors under budget, ties go to the cheaper team, and each gets a 2x pick.
Brute force over every combination like build_budget_teams, fine for 22 drivers.
"""
from itertools import combinations

import pandas as pd


def _search(driver_prices: dict, constructor_prices: dict, combo_value, constructor_value,
            budget: float):
    """
    The legal team with the highest combo_value(drivers) + constructor values.
    Ties go to the cheaper team. Returns (drivers, constructors) or None if nothing fits.
    """
    # best constructor pairs first, cheapest first among equals, so for any 5 drivers
    # the first pair that fits the money left is the best one for them
    pairs = sorted(
        ((a, b) for a, b in combinations(sorted(constructor_prices), 2)),
        key=lambda p: (-(constructor_value(p[0]) + constructor_value(p[1])),
                       constructor_prices[p[0]] + constructor_prices[p[1]]),
    )
    best_key, best = None, None
    for combo in combinations(sorted(driver_prices), 5):
        driver_cost = sum(driver_prices[a] for a in combo)
        if driver_cost > budget:
            continue
        value = combo_value(combo)
        for pair in pairs:
            cost = driver_cost + constructor_prices[pair[0]] + constructor_prices[pair[1]]
            if cost > budget:
                continue
            total = value + constructor_value(pair[0]) + constructor_value(pair[1])
            # rounded so float noise in summed percentages can't decide a tie
            key = (round(total, 6), -round(cost, 6))
            if best_key is None or key > best_key:
                best_key, best = key, (combo, pair)
            break
    return best


def _team(found, driver_prices: dict, constructor_prices: dict, boost_key) -> dict | None:
    if found is None:
        return None
    combo, pair = found
    boost = max(combo, key=boost_key)
    return {
        "drivers": [{"Abbreviation": a, "Price": driver_prices[a]} for a in combo],
        "constructors": [{"name": c, "price": constructor_prices[c]} for c in pair],
        "boost_pick": {"Abbreviation": boost},
        "total_cost": round(sum(driver_prices[a] for a in combo)
                            + sum(constructor_prices[c] for c in pair), 1),
    }


def fp3_order_team(grid: pd.DataFrame, prices: dict, budget: float = 100.0) -> dict | None:
    """
    Copy the FP3 order: the legal team with the lowest sum of its drivers' grid
    positions plus each constructor's best car on the grid. 2x on the fastest driver.

    Only reads Abbreviation, TeamName and GridPosition, never FantasyValue or Predicted.
    """
    grid = grid[["Abbreviation", "TeamName", "GridPosition"]]
    pos = {a: float(p) for a, p in zip(grid["Abbreviation"], grid["GridPosition"])
           if a in prices.get("drivers", {})}
    best_car = grid.groupby("TeamName")["GridPosition"].min().to_dict()
    driver_prices = {a: prices["drivers"][a] for a in pos}
    # a constructor with no car on the grid can't be ranked, so it's left out
    constructor_prices = {c: p for c, p in prices.get("constructors", {}).items() if c in best_car}

    found = _search(driver_prices, constructor_prices,
                    lambda combo: -sum(pos[a] for a in combo),
                    lambda c: -float(best_car[c]), budget)
    return _team(found, driver_prices, constructor_prices, lambda a: -pos[a])


def most_expensive_team(prices: dict, budget: float = 100.0) -> dict | None:
    """The team that spends the most of the budget. 2x on the priciest driver."""
    driver_prices = prices.get("drivers", {})
    constructor_prices = prices.get("constructors", {})
    found = _search(driver_prices, constructor_prices,
                    lambda combo: sum(driver_prices[a] for a in combo),
                    lambda c: constructor_prices[c], budget)
    return _team(found, driver_prices, constructor_prices, lambda a: driver_prices[a])


def crowd_team(ownership: dict, prices: dict, budget: float = 100.0) -> dict | None:
    """
    Copy the crowd: the team with the highest total ownership (selected_pct) that fits.
    2x on the most captained driver in it.
    """
    driver_prices = prices.get("drivers", {})
    constructor_prices = prices.get("constructors", {})
    d_own = ownership.get("drivers", {})
    c_own = ownership.get("constructors", {})

    def selected(table, name):
        return float(table.get(name, {}).get("selected_pct", 0.0))

    found = _search(driver_prices, constructor_prices,
                    lambda combo: sum(selected(d_own, a) for a in combo),
                    lambda c: selected(c_own, c), budget)
    return _team(found, driver_prices, constructor_prices,
                 lambda a: float(d_own.get(a, {}).get("captain_pct", 0.0)))


def hindsight_best_team(round_points: dict, prices: dict, budget: float = 100.0) -> dict | None:
    """
    The best team you could have picked knowing the real points, the ceiling.
    The 2x counts: the team's top scorer is doubled, same as team_points does.
    """
    driver_prices = prices.get("drivers", {})
    constructor_prices = prices.get("constructors", {})
    d_pts = {a: float(round_points["drivers"].get(a, {}).get("points", 0.0)) for a in driver_prices}
    c_pts = round_points.get("constructors", {})

    found = _search(driver_prices, constructor_prices,
                    lambda combo: sum(d_pts[a] for a in combo) + max(d_pts[a] for a in combo),
                    lambda c: float(c_pts.get(c, {}).get("points", 0.0)), budget)
    return _team(found, driver_prices, constructor_prices, lambda a: d_pts[a])
