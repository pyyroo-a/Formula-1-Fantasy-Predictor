"""
Plays a season with the transfer ladder three ways and grades it on REAL points.

  * keep:      never change the team (the 2x still gets picked every race)
  * free_only: every race take the best ladder row that doesn't cost a hit
  * with_hits: every race take the best row, the paid one included

The planner only ships if free_only beats keep, and the paid row only stays if
with_hits beats free_only (Ashen's two bars, see the planner design doc). PitWall's
expected points aren't on the game's exact scale, so only real points can say if
paying -10 on the ladder's say so works.

Budget follows the game: the team's value at that race's prices plus what's left in
the bank, so a team that gets dearer can still be kept.
"""
from src.official_points import team_points
from src.planner import FREE_PER_RACE, TRANSFER_HIT, next_free_transfers, score_team, team_cost, transfer_ladder

STRATEGIES = ("keep", "free_only", "with_hits")


def _pick_row(rows: list[dict], strategy: str) -> dict:
    if strategy == "keep":
        return rows[0]
    allowed = [r for r in rows if not r.get("none") and (strategy == "with_hits" or r["paid"] == 0)]
    return max(allowed, key=lambda r: r["expected"])   # ties go to the fewer transfers


def play_season(rounds: list[dict], start: dict, start_bank: float, strategy: str) -> dict:
    """
    rounds: [{"round", "pool" (None if no forecast that race), "prices", "points" (official)}].
    The first round scores the start team as it is. Returns per round results, the
    average real points per race (hits taken off) and how many hits were paid.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}")
    drivers, constructors = list(start["drivers"]), list(start["constructors"])
    bank = start_bank
    boost = None
    free = 0
    per_round = []
    for i, rnd in enumerate(rounds):
        budget = round(team_cost(drivers, constructors, rnd["prices"]) + bank, 1)
        used, paid = 0, 0
        if rnd["pool"] is not None:
            if i == 0:
                boost = score_team(drivers, constructors, rnd["pool"])["boost"]
            else:
                ladder = transfer_ladder({"drivers": drivers, "constructors": constructors}, rnd["pool"],
                                         rnd["prices"], budget, free, paid_row=True)
                row = _pick_row(ladder["rows"], strategy)
                drivers, constructors, boost = list(row["drivers"]), list(row["constructors"]), row["boost"]
                used, paid = row["transfers"], row["paid"]
        bank = round(budget - team_cost(drivers, constructors, rnd["prices"]), 1)
        points = team_points(drivers, constructors, boost, rnd["points"]) - TRANSFER_HIT * paid
        per_round.append({"round": rnd["round"], "points": points, "transfers": used, "paid": paid,
                          "free_before": free, "budget": budget, "drivers": list(drivers),
                          "constructors": list(constructors), "boost": boost})
        free = FREE_PER_RACE if i == 0 else next_free_transfers(free, used)
    n = len(per_round)
    return {"per_round": per_round,
            "average": round(sum(r["points"] for r in per_round) / n, 1) if n else 0.0,
            "hits": sum(r["paid"] for r in per_round)}
