"""
Validates the DNF model in src/dnf.py by replaying the season race by race.

THE TEST
--------
For every 2026 race, the model is trained ONLY on races that happened before it,
then asked to predict that race. This is walk-forward validation: at no point does
the model see the race it is being graded on, which is the same discipline
src/backtest.py uses for team picks.

HOW A PROBABILITY IS GRADED
---------------------------
You cannot mark a probability right or wrong, because "18% chance of retiring" is
not falsified by either outcome. Two standard scores are used instead:

  Brier score : average of (predicted - actual)^2. Lower is better.
                Rewards being confident only when confidence is warranted.
  Log loss    : punishes confident mistakes far more harshly. Lower is better.

THE BAR TO BEAT
---------------
The baseline is the flat base rate: give every driver the same average chance of
retiring, ignoring who he is, where he starts and which track it is. That is
already a reasonable forecast, and beating it is not automatic. If the model
cannot, the extra machinery is not earning its place and should not be used.

Run:  python scripts/measure_dnf.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())

from src.dnf import DNFModel, label_dnf  # noqa: E402

EPS = 1e-9  # keeps log loss finite if a probability ever reaches 0 or 1


def brier(p, y):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def logloss(p, y):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    y = np.asarray(y, dtype=float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main():
    hist = pd.concat(
        [pd.read_csv(f"data/processed/race_results_{y}.csv") for y in (2025, 2026)],
        ignore_index=True,
    )
    data = label_dnf(hist)

    rounds = sorted(data.loc[data["Year"] == 2026, "RoundNumber"].unique())

    preds, base_preds, actuals, per_race = [], [], [], []

    for rnd in rounds:
        # Strictly everything before this race, and nothing from it.
        train = data[(data["Year"] < 2026) | (data["RoundNumber"] < rnd)]
        test = data[(data["Year"] == 2026) & (data["RoundNumber"] == rnd)]
        test = test.dropna(subset=["GridPosition"])
        if test.empty or len(train) < 200:
            continue

        model = DNFModel.fit(train)
        p = model.predict(test["Abbreviation"], test["GridPosition"],
                          test["RaceName"].iloc[0])
        y = test["DNF"].to_numpy()

        # The baseline knows only the average, computed from the same training data.
        p_base = np.full(len(y), label_dnf(train)["DNF"].mean())

        preds.extend(p); base_preds.extend(p_base); actuals.extend(y)
        per_race.append({
            "round": int(rnd),
            "race": test["RaceName"].iloc[0],
            "actual_dnfs": int(y.sum()),
            "expected": float(p.sum()),
            "brier": brier(p, y),
            "brier_base": brier(p_base, y),
        })

    if not per_race:
        sys.exit("Not enough history to validate.")

    pr = pd.DataFrame(per_race)
    print(f"\n{'R':<4}{'RACE':<26}{'ACTUAL':>7}{'PREDICTED':>11}{'BRIER':>8}{'BASE':>8}")
    for _, r in pr.iterrows():
        flag = "  +" if r["brier"] < r["brier_base"] else "   "
        print(f"{r['round']:<4}{r['race'][:25]:<26}{r['actual_dnfs']:>7}"
              f"{r['expected']:>11.1f}{r['brier']:>8.4f}{r['brier_base']:>8.4f}{flag}")

    b_m, b_b = brier(preds, actuals), brier(base_preds, actuals)
    l_m, l_b = logloss(preds, actuals), logloss(base_preds, actuals)

    print(f"\n{'=' * 62}\nWALK-FORWARD RESULT  ({len(pr)} races, {len(actuals)} driver-races)\n{'=' * 62}")
    print(f"  actual retirements    : {int(np.sum(actuals))}")
    print(f"  model expected        : {np.sum(preds):.1f}")
    print(f"  baseline expected     : {np.sum(base_preds):.1f}")
    print(f"\n  {'':<14}{'MODEL':>10}{'BASELINE':>11}{'CHANGE':>10}")
    print(f"  {'Brier':<14}{b_m:>10.4f}{b_b:>11.4f}{(b_m - b_b) / b_b:>9.1%}")
    print(f"  {'Log loss':<14}{l_m:>10.4f}{l_b:>11.4f}{(l_m - l_b) / l_b:>9.1%}")
    print(f"\n  Races where model beat baseline: "
          f"{int((pr['brier'] < pr['brier_base']).sum())}/{len(pr)}")

    verdict = "MODEL WINS" if (b_m < b_b and l_m < l_b) else "NO IMPROVEMENT, do not ship"
    print(f"\n  VERDICT: {verdict}")

    # How hard is each component being shrunk? Large k means the data did not
    # support that component and it was mostly ignored.
    final = DNFModel.fit(data)
    print(f"\n  Shrinkage strength (higher = less trusted):")
    print(f"    driver  k = {final.k_driver:>7.1f}")
    print(f"    circuit k = {final.k_circuit:>7.1f}")
    print(f"    base rate = {final.p0:.3f}  (recency weighted)")

    # A concrete look at what the model says for a typical upcoming grid.
    print(f"\n  EXAMPLE: P(DNF) by grid slot, average driver")
    for g in (1, 5, 10, 15, 20):
        p = final.predict(["RUS"], [g])[0]
        print(f"    P{g:<3}: {p:.3f}   (expected points hit {p * -20:+.1f})")


if __name__ == "__main__":
    main()
