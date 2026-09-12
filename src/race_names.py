"""
Keeps one name per circuit, so history from one track doesn't leak into another.

Basically, the "Spanish Grand Prix" name moved. Up to 2025 it was the race in
Barcelona. In 2026 Barcelona got its own event ("Barcelona Grand Prix") and the
Spanish GP name went to the new Madring street circuit in Madrid.

Everything that looks up a track's history does it by RaceName, so without this
the Madring was quietly borrowing Barcelona's old results: its retirement rate in
the DNF model and its circuit history in the finish predictions.

So for any year before 2026 we rename "Spanish Grand Prix" to "Barcelona Grand Prix".
That also gives the 2026 Barcelona race its real history back.
"""

import pandas as pd

# (race name, first year the name means the new track) -> what it meant before that
_RENAMED_BEFORE = {
    ("Spanish Grand Prix", 2026): "Barcelona Grand Prix",
}


def normalize_race_names(df: pd.DataFrame) -> pd.DataFrame:
    """Renames old races to the circuit they actually ran at. Needs RaceName and Year."""
    if "RaceName" not in df.columns or "Year" not in df.columns:
        return df
    df = df.copy()
    for (name, from_year), old_name in _RENAMED_BEFORE.items():
        mask = (df["RaceName"] == name) & (df["Year"] < from_year)
        df.loc[mask, "RaceName"] = old_name
    return df
