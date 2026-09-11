"""
One name per team, everywhere.

WHY THIS EXISTS
---------------
Every join between data sources in PitWall is on TeamName: race results, practice
sessions and the F1 Fantasy price feed all have to agree on it. From round 12
(Dutch GP, 2026) FastF1's race results started using different names for four
teams than it had all season, and than the price feed still uses:

    "Red Bull"          instead of  "Red Bull Racing"
    "Alpine F1 Team"    instead of  "Alpine"
    "RB F1 Team"        instead of  "Racing Bulls"
    "Cadillac F1 Team"  instead of  "Cadillac"

Nothing crashed. Each renamed team quietly became two teams:
  * team form (TeamAvgPosition, a rolling 3-race average) restarted from scratch
    under the new name, so it was built from one race instead of three;
  * backtests scored those constructors as 0, because their real results were
    filed under a name the price feed does not recognise.

The canonical names are the PRICE FEED's names, because that is the source a
constructor has to match to be picked at all.

Only true aliases of the same team in the same era belong here. A genuine rebrand
(Kick Sauber becoming Audi) is a modelling decision about whether history carries
over, and is deliberately NOT mapped.
"""

import pandas as pd

TEAM_ALIASES = {
    "Red Bull": "Red Bull Racing",
    "Alpine F1 Team": "Alpine",
    "RB F1 Team": "Racing Bulls",
    "Cadillac F1 Team": "Cadillac",
}


def normalize_team_name(name):
    """Returns the canonical name, or the name unchanged if it has no alias."""
    return TEAM_ALIASES.get(name, name)


def normalize_team_names(df: pd.DataFrame) -> pd.DataFrame:
    """Applies normalize_team_name to a TeamName column, if there is one."""
    if "TeamName" in df.columns:
        df = df.copy()
        df["TeamName"] = df["TeamName"].map(normalize_team_name)
    return df
