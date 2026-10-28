"""
Expected constructor extras: what a constructor scores on top of its two drivers.

In the game a constructor gets both its drivers' points, its qualifying bonus, AND pit
stop points (up to +20, +5 for the fastest stop, +15 for a world record), plus the odd
penalty. We never modelled the pit stops. Nobody gives out pit stop times for free any
more (OpenF1 only has 6 races this season), so we work out the leftover instead:

    official constructor points - its two drivers' official points - the qualifying
    bonus their real grid earned

and average it per team over the rounds BEFORE the race being predicted, so nothing
leaks in from the future. One catch: the bonus goes off the real grid, and a grid
penalty moves a car away from where it qualified. That small error just ends up in
the leftover too.
"""
import pandas as pd

from src.fantasy import _real_constructor_quali_bonus


def constructor_extras(official: dict[int, dict], results: pd.DataFrame,
                       before_round: int) -> dict[str, float]:
    """Average leftover per constructor over the official rounds before before_round."""
    leftovers: dict[str, list[float]] = {}
    for rnd in sorted(r for r in official if r < before_round):
        pts = official[rnd]
        for team, cars in results[results["RoundNumber"] == rnd].groupby("TeamName"):
            if team not in pts["constructors"]:
                continue
            drivers = sum(pts["drivers"].get(a, {}).get("points", 0.0) for a in cars["Abbreviation"])
            # a pit lane start has no grid slot, it counts as out in Q1
            grids = [g if g > 0 else 99 for g in cars["GridPosition"].fillna(99)]
            leftovers.setdefault(team, []).append(
                pts["constructors"][team]["points"] - drivers - _real_constructor_quali_bonus(grids))
    return {team: round(sum(v) / len(v), 2) for team, v in leftovers.items()}
