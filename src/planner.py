"""
The transfer ladder: the "my team" planner (project 3).

You already have a team in the game, a budget and some free transfers. For this
weekend the ladder shows the best team you can reach with 0 transfers (keep it), 1, 2,
up to your free ones, plus one paid one at -10. Each row is worked out on its own (the
best 2 transfers often don't include the best single one, budgets get in the way).

Everything is scored with the same numbers the Manual Team page shows (the pool from
get_race_pool), plus the 2x counted again because that's real points in the game.

It states facts, it never says "do this". That was the whole brief: I make the call.
"""
from itertools import combinations

from src.fantasy import pick_boost_driver

# Checked 2026-10-28: 2 free transfers a race, ONE unused one carries over, so 3 at most,
# and every transfer past the free ones costs -10. From the 2026 rules write ups
# (motorsport.com "F1 Fantasy 2026: prizes and changes", fanamp's 2026 rules), the
# official rules page only loads in a browser. 2026 also counts transfers as the net
# change from your last team, which is how we count swaps here.
FREE_PER_RACE = 2
MAX_FREE_TRANSFERS = 3
TRANSFER_HIT = 10

# Show the paid row (one transfer past the free ones, -10 already taken off)?
# Measured in the planner grade (scripts/planner_grade.py), numbers go here.
SHOW_PAID_ROW = True


def next_free_transfers(free_now: int, used: int) -> int:
    """Free transfers next race: what's left over (one carries) plus the usual 2, max 3."""
    return min(MAX_FREE_TRANSFERS, max(free_now - used, 0) + FREE_PER_RACE)


def team_cost(drivers: list[str], constructors: list[str], prices: dict) -> float:
    """What a team costs at these prices. A pick with no price counts 0."""
    d, c = prices.get("drivers", {}), prices.get("constructors", {})
    return round(sum(d.get(a, 0.0) for a in drivers) + sum(c.get(n, 0.0) for n in constructors), 1)


def _lookup(pool: dict) -> tuple[dict, dict]:
    return ({d["Abbreviation"]: d for d in pool["drivers"]},
            {c["name"]: c for c in pool["constructors"]})


def score_team(drivers: list[str], constructors: list[str], pool: dict) -> dict:
    """
    Expected points for a team: 5 drivers + 2 constructors + the 2x driver again.
    A pick that isn't in this weekend's pool scores 0 and gets listed in missing.
    """
    d_map, c_map = _lookup(pool)
    in_pool = [d_map[a] for a in drivers if a in d_map]
    missing = [a for a in drivers if a not in d_map] + [n for n in constructors if n not in c_map]
    total = sum(d["FantasyValue"] for d in in_pool) + sum(c_map[n]["score"] for n in constructors if n in c_map)
    boost = pick_boost_driver(in_pool)["Abbreviation"] if in_pool else None
    if boost:
        total += d_map[boost]["FantasyValue"]
    return {"expected": round(total, 3), "boost": boost, "missing": missing}


def best_with_transfers(current: dict, pool: dict, prices: dict, budget: float, k: int) -> dict | None:
    """
    The best legal team with exactly k swaps from the current one, or None if nothing fits.
    Legal = 5 different drivers and 2 different constructors, everyone coming in is in
    this weekend's pool, and it costs no more than the budget. Ties go to the cheaper team.
    """
    d_price, c_price = prices.get("drivers", {}), prices.get("constructors", {})
    drivers, constructors = list(current["drivers"]), list(current["constructors"])
    d_in = sorted(d["Abbreviation"] for d in pool["drivers"]
                  if d["Abbreviation"] not in drivers and d["Abbreviation"] in d_price)
    c_in = sorted(c["name"] for c in pool["constructors"]
                  if c["name"] not in constructors and c["name"] in c_price)

    best_key, best = None, None
    for n_c in range(0, min(k, 2) + 1):
        n_d = k - n_c
        if n_d > 5:
            continue
        for d_out in combinations(drivers, n_d):
            for d_new in combinations(d_in, n_d):
                new_drivers = [a for a in drivers if a not in d_out] + list(d_new)
                for c_out in combinations(constructors, n_c):
                    for c_new in combinations(c_in, n_c):
                        new_cons = [n for n in constructors if n not in c_out] + list(c_new)
                        cost = team_cost(new_drivers, new_cons, prices)
                        if cost > budget:
                            continue
                        scored = score_team(new_drivers, new_cons, pool)
                        key = (round(scored["expected"], 6), -cost)
                        if best_key is None or key > best_key:
                            swaps = ([{"kind": "driver", "out": o, "in": i} for o, i in zip(d_out, d_new)]
                                     + [{"kind": "constructor", "out": o, "in": i} for o, i in zip(c_out, c_new)])
                            best_key = key
                            best = {"drivers": new_drivers, "constructors": new_cons, "swaps": swaps,
                                    "boost": scored["boost"], "expected": scored["expected"], "cost": cost}
    return best


def _reason(swap: dict, pool: dict, session: str) -> str:
    """The practice facts behind a swap, e.g. "P2 P20 to B1 P3 in FP3"."""
    d_map, _ = _lookup(pool)
    if swap["kind"] == "driver":
        def where(a):
            return f"{a} P{int(d_map[a]['GridPosition'])}" if a in d_map else f"{a} (not in this weekend's field)"
        return f"{where(swap['out'])} to {where(swap['in'])} in {session}"

    def cars(team):
        grids = sorted(int(d["GridPosition"]) for d in pool["drivers"] if d["TeamName"] == team)
        return f"{team} " + " and ".join(f"P{g}" for g in grids) if grids else f"{team} (no cars in {session})"
    return f"{cars(swap['out'])} to {cars(swap['in'])} in {session}"


def _plural(n: int) -> str:
    return f"{n} transfer" if n == 1 else f"{n} transfers"


def transfer_ladder(current: dict, pool: dict, prices: dict, budget: float, free_transfers: int,
                    session: str = "FP3", paid_row: bool | None = None) -> dict:
    """
    The ladder: keep, then the best team with 1, 2, ... free transfers, plus one paid row
    (SHOW_PAID_ROW, or paid_row=True/False to force it, the replay needs that).
    Each row's expected has -10 taken off per paid transfer. Plus the facts.
    """
    show_paid = SHOW_PAID_ROW if paid_row is None else paid_row
    keep = score_team(current["drivers"], current["constructors"], pool)
    rows = [{"transfers": 0, "paid": 0, "drivers": list(current["drivers"]),
             "constructors": list(current["constructors"]), "swaps": [], "boost": keep["boost"],
             "expected": keep["expected"], "vs_keep": 0.0,
             "cost": team_cost(current["drivers"], current["constructors"], prices)}]

    last = free_transfers + (1 if show_paid else 0)
    for k in range(1, last + 1):
        paid = max(0, k - free_transfers)
        best = best_with_transfers(current, pool, prices, budget, k)
        if best is None:
            rows.append({"transfers": k, "paid": paid, "none": True})
            continue
        expected = round(best["expected"] - TRANSFER_HIT * paid, 3)
        rows.append({**best, "transfers": k, "paid": paid, "expected": expected,
                     "vs_keep": round(expected - keep["expected"], 3),
                     "swaps": [{**s, "reason": _reason(s, pool, session)} for s in best["swaps"]]})

    facts = [f"{a} isn't in this weekend's field, so they score 0 here." for a in keep["missing"]]
    real = [r for r in rows if not r.get("none")]
    top = max(real, key=lambda r: r["expected"])
    if top["transfers"] == 0:
        facts.append(f"The highest expected total is keeping your team ({top['expected']:.0f}).")
    else:
        facts.append(f"The highest expected total is with {_plural(top['transfers'])} ({top['expected']:.0f}).")
    for k in range(1, free_transfers + 1):
        if k < len(rows) and not rows[k].get("none") and not rows[k - 1].get("none"):
            facts.append(f"Transfer {k} adds {rows[k]['expected'] - rows[k - 1]['expected']:+.0f}.")
    saved = next_free_transfers(free_transfers, free_transfers - 1)
    if free_transfers >= 1 and saved > next_free_transfers(free_transfers, free_transfers):
        facts.append(f"Skip transfer {free_transfers} and you'd have {saved} free transfers next week.")
    extra = free_transfers + 1
    if show_paid and len(rows) > extra and not rows[extra].get("none") and not rows[free_transfers].get("none"):
        gain = rows[extra]["expected"] + TRANSFER_HIT - rows[free_transfers]["expected"]
        facts.append(f"Transfer {extra} adds {gain:+.0f} but costs -{TRANSFER_HIT}.")
    else:
        facts.append(f"Transfer {extra} costs -{TRANSFER_HIT}.")
    return {"rows": rows, "facts": facts, "missing": keep["missing"]}
