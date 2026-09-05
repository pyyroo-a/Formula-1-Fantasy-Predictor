"""
Measures how wrong practice pace is as a stand-in for the real starting grid.

WHY THIS EXISTS
---------------
The F1 Fantasy deadline falls BEFORE qualifying. So at the moment we have to
pick a team, the real grid does not exist yet and never will in time. Production
substitutes "order the drivers by fastest practice lap" (src/fetch_practice.py)
and then feeds that into GridPosition as though it were fact.

Two places in src/fantasy.py consume GridPosition, and both are non-linear:

  * qualifying_score()  is a STEP function:  P1-P10  -> +10 down to +1
                                             P11-P15 ->  0
                                             P16+    -> -5
  * OvertakeBonus       is (GridPosition - Predicted), scaled per circuit

Pushing a noisy estimate through a step function is biased. Being one place
either side of P10 or P15 flips the score with nothing in between, so a tenth of
a second in practice can swing a driver's points. That is exactly what happened
at Monza 2026: practice had Gasly P9, and he took pole.

This script quantifies that noise, so the next step (sampling over a
distribution of possible grids instead of committing to one) can be calibrated
from real numbers instead of a guess.

WHAT IT COMPARES
----------------
  truth    = GridPosition from data/processed/race_results_<year>.csv
             The actual starting grid, and critically the same column the model
             is TRAINED on. Measuring against it therefore measures the
             train/serve skew described in the notes in src/models.py.

  estimate = practice pace order, from the same function and the same
             FP3 -> FP2 -> FP1 fallback that production uses, so the error we
             measure here is the error the live app actually suffers.

Run:  python scripts/measure_grid_error.py [--year 2026]
Out:  results/grid_error_<year>.csv   (one row per driver per race)
"""

import argparse
import os
import sys

import pandas as pd

# Allow running as `python scripts/measure_grid_error.py` from the repo root.
sys.path.insert(0, os.getcwd())

from src.fetch_practice import get_practice_grid, is_sprint_weekend  # noqa: E402

# The two cliff edges in qualifying_score(). Crossing either one changes a
# driver's fantasy points discontinuously, so an error that straddles a cliff
# costs far more than an error of the same size elsewhere in the field.
CLIFFS = [(10, 11), (15, 16)]


def practice_order(year: int, race_name: str):
    """
    Reproduces production's practice fallback exactly: FP3, then FP2, then FP1.

    Sprint weekends only run FP1. get_practice_grid already forces that
    internally, but we short-circuit here too so the session name we report is
    honest rather than claiming we used FP3.

    Returns (DataFrame, session_name), or (None, None) if nothing loaded.
    """
    sessions = ["FP1"] if is_sprint_weekend(race_name) else ["FP3", "FP2", "FP1"]
    for sess in sessions:
        try:
            return get_practice_grid(year, race_name, sess), sess
        except Exception:
            continue
    return None, None


def main(year: int):
    actual = pd.read_csv(f"data/processed/race_results_{year}.csv")

    rows = []
    per_race = []

    for (rnd, race_name), truth in actual.groupby(["RoundNumber", "RaceName"], sort=True):
        prac, sess = practice_order(year, race_name)
        if prac is None:
            print(f"  R{rnd:<2} {race_name:<28} SKIPPED (no practice data)")
            continue

        # Inner join. A driver who set no practice lap, or who never started,
        # has no meaningful pair to compare and would only pollute the stats.
        m = prac[["Abbreviation", "GridPosition"]].rename(
            columns={"GridPosition": "PracticeOrder"}
        ).merge(
            truth[["Abbreviation", "GridPosition"]].rename(
                columns={"GridPosition": "ActualGrid"}
            ),
            on="Abbreviation", how="inner",
        ).dropna(subset=["ActualGrid"])

        if m.empty:
            print(f"  R{rnd:<2} {race_name:<28} SKIPPED (no overlapping drivers)")
            continue

        # Signed error keeps the direction. Positive means practice placed the
        # driver FURTHER BACK than he actually started, i.e. practice under-rated
        # him. Keeping the sign lets us check for systematic bias later.
        m["Error"] = m["PracticeOrder"] - m["ActualGrid"]
        m["AbsError"] = m["Error"].abs()
        m["RoundNumber"] = rnd
        m["RaceName"] = race_name
        m["Session"] = sess
        rows.append(m)

        # Spearman rather than Pearson: we care whether the ORDER is right, not
        # whether the position numbers are linearly related.
        rho = m["PracticeOrder"].corr(m["ActualGrid"], method="spearman")
        pole_hit = bool((m.loc[m["ActualGrid"] == 1, "PracticeOrder"] == 1).any())

        per_race.append({
            "round": rnd, "race": race_name, "session": sess,
            "mae": m["AbsError"].mean(), "max": m["AbsError"].max(),
            "spearman": rho, "pole_hit": pole_hit,
        })
        print(f"  R{rnd:<2} {race_name:<28} {sess:<4} "
              f"MAE {m['AbsError'].mean():>5.2f}  max {int(m['AbsError'].max()):>2}  "
              f"rho {rho:>5.2f}  pole {'HIT' if pole_hit else 'miss'}")

    if not rows:
        sys.exit("No races could be measured.")

    df = pd.concat(rows, ignore_index=True)
    os.makedirs("results", exist_ok=True)
    out = f"results/grid_error_{year}.csv"
    df.to_csv(out, index=False)

    races = df["RaceName"].nunique()
    err, abs_err = df["Error"], df["AbsError"]

    print(f"\n{'=' * 66}")
    print(f"PRACTICE-ORDER ERROR, {year}   ({races} races, {len(df)} driver-races)")
    print(f"{'=' * 66}")
    print(f"  MAE (mean abs error) : {abs_err.mean():.2f} places")
    print(f"  median abs error     : {abs_err.median():.2f} places")
    print(f"  std of signed error  : {err.std():.2f}")
    print(f"  mean signed error    : {err.mean():+.2f}   (~0 means no systematic bias)")

    # Tails matter more than the average here. A fat tail is what turns a
    # plausible pick into a Monza-style miss, and the tail is precisely what a
    # single point estimate hides from the optimiser.
    print("\n  TAILS")
    for k in (1, 2, 3, 5, 8):
        print(f"    P(|error| >= {k}) : {(abs_err >= k).mean():.3f}")

    print("\n  QUANTILES of |error|")
    for q in (0.5, 0.75, 0.9, 0.95, 0.99):
        print(f"    p{int(q * 100):<3}: {abs_err.quantile(q):.1f}")

    # Errors are not uniform across the field. The same error costs far more at
    # the front, because that is where the qualifying-points curve is steepest.
    print("\n  ERROR BY ACTUAL GRID SEGMENT")
    seg = pd.cut(df["ActualGrid"], [0, 5, 10, 15, 30],
                 labels=["P1-P5", "P6-P10", "P11-P15", "P16+"])
    print(df.groupby(seg, observed=True)["AbsError"]
            .agg(["mean", "median", "max", "count"]).round(2).to_string())

    # The headline number for the scoring problem: how often does practice put a
    # driver on the wrong side of a qualifying_score() step?
    print("\n  CLIFF CROSSINGS (wrong side of a qualifying_score step)")
    any_cross = pd.Series(False, index=df.index)
    for lo, hi in CLIFFS:
        crossed = (((df["PracticeOrder"] <= lo) & (df["ActualGrid"] >= hi)) |
                   ((df["PracticeOrder"] >= hi) & (df["ActualGrid"] <= lo)))
        any_cross |= crossed
        print(f"    P{lo}/P{hi} boundary : {crossed.mean():.3f}  "
              f"({int(crossed.sum())} driver-races)")
    print(f"    ANY cliff crossed : {any_cross.mean():.3f}  "
          f"({int(any_cross.sum())} driver-races)")

    pr = pd.DataFrame(per_race)
    print(f"\n  POLE: practice picked the real pole-sitter in "
          f"{int(pr['pole_hit'].sum())}/{len(pr)} races ({pr['pole_hit'].mean():.0%})")
    print(f"  Worst race: {pr.loc[pr['mae'].idxmax(), 'race']} (MAE {pr['mae'].max():.2f})")
    print(f"  Best race : {pr.loc[pr['mae'].idxmin(), 'race']} (MAE {pr['mae'].min():.2f})")
    print(f"\n  Per-driver-race rows written to {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Measure practice-order vs real grid error.")
    ap.add_argument("--year", type=int, default=2026)
    main(ap.parse_args().year)
