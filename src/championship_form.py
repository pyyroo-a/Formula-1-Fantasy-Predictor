import pandas as pd
import numpy as np

# Standard F1 points for finishing positions 1 through 10.
# Drivers outside the top 10 score 0 points.
POINTS_MAP = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
              6: 8,  7: 6,  8: 4,  9: 2,  10: 1}


def compute_championship_form(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes the full race results DataFrame for the current season and returns
    a per-driver championship form table.

    Columns returned:
      - Abbreviation   : driver code (e.g. "VER", "NOR")
      - ChampPoints    : total F1 points scored so far this season
      - ChampPosition  : current standings position (1 = leader)
      - FormSignal     : normalised 0-1 score where 1.0 = championship leader.
                         This is what we blend into the race predictions.
    """

    df = results_df.copy()

    # Map each finish position to its F1 fantasy points value.
    # Positions outside the top 10 get 0 points.
    df["RacePoints"] = df["Position"].map(POINTS_MAP).fillna(0)

    # Sum all race points per driver to get their current season total.
    standings = (
        df.groupby("Abbreviation")["RacePoints"]
        .sum()
        .reset_index()
        .rename(columns={"RacePoints": "ChampPoints"})
    )

    # Sort descending so the driver with the most points is at the top.
    standings = standings.sort_values("ChampPoints", ascending=False).reset_index(drop=True)

    # Assign championship position (1 = leader, 2 = second, etc.)
    standings["ChampPosition"] = standings.index + 1

    # Normalise points to a 0–1 scale.
    # The leader gets 1.0; a driver with 0 points gets 0.0.
    # We use max points as the denominator so everything is relative to the leader.
    max_points = standings["ChampPoints"].max()
    if max_points > 0:
        standings["FormSignal"] = (standings["ChampPoints"] / max_points).round(4)
    else:
        # No races completed yet — give everyone an equal neutral signal
        standings["FormSignal"] = 0.5

    return standings[["Abbreviation", "ChampPoints", "ChampPosition", "FormSignal"]]


def apply_championship_signal(
    fantasy_table: pd.DataFrame,
    form_df: pd.DataFrame,
    weight: float = 0.15,
) -> pd.DataFrame:
    """
    Blends the championship form signal into an existing set of predictions.

    How it works:
      - A high FormSignal (close to 1.0) means the driver is near the top of
        the standings, so we shift their predicted position slightly upward (lower number = better).
      - A low FormSignal (close to 0.0) means the driver is struggling this season,
        so we shift their predicted position slightly downward.
      - The `weight` parameter controls how much influence the signal has.
        Default 0.15 means it contributes 15% of a max 3-position shift.

    The adjustment formula:
      championship_adjustment = (0.5 - FormSignal) * 3 * weight
      A leader (FormSignal=1.0) gets  -1.5*weight adjustment (moves up the order).
      A backmarker (FormSignal=0.0) gets +1.5*weight adjustment (moves down).
    """
    df = fantasy_table.copy()

    # Merge the form signal onto the predictions table by driver abbreviation.
    df = df.merge(form_df[["Abbreviation", "FormSignal", "ChampPoints", "ChampPosition"]],
                  on="Abbreviation", how="left")

    # Drivers not in the standings (e.g. new mid-season entries) get a neutral signal.
    df["FormSignal"] = df["FormSignal"].fillna(0.5)
    df["ChampPoints"] = df["ChampPoints"].fillna(0)
    df["ChampPosition"] = df["ChampPosition"].fillna(20)

    # Calculate how much to adjust the predicted position.
    # (0.5 - FormSignal) gives a value between -0.5 and +0.5:
    #   leader -> (0.5 - 1.0) = -0.5  -> improves predicted position
    #   last   -> (0.5 - 0.0) = +0.5  -> worsens predicted position
    # Multiply by 3 to scale to a max ±1.5 position shift, then apply weight.
    df["ChampAdjustment"] = (0.5 - df["FormSignal"]) * 3 * weight

    # Apply the adjustment and clip to the valid 1–20 position range.
    df["Predicted"] = np.clip(df["Predicted"] + df["ChampAdjustment"], 1, 20).round(2)

    # Drop the intermediate adjustment column — it's not needed downstream.
    df = df.drop(columns=["ChampAdjustment"])

    return df
