import pandas as pd
import os

from src.team_names import normalize_team_names
from src.race_names import normalize_race_names

def save_dataset(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def load_dataset(path: str) -> pd.DataFrame:
    # Team names are normalised on the way in. Cheap, and it means a rename in
    # the source data can never silently split one team into two.
    # race names too, so Madring doesn't pick up Barcelona's old history (src/race_names.py)
    return normalize_race_names(normalize_team_names(pd.read_csv(path)))

def dataset_exists(path: str) -> bool:
    return os.path.exists(path)