"""
Settings shared across the whole project, so they're only written down once.

Basically when the 2027 season starts, SEASON is the one number to change here
(plus making sure this season's results are there as last season's data).
"""

SEASON = 2026
PREVIOUS_SEASON = SEASON - 1


def results_path(year: int = SEASON) -> str:
    """Where a season's race results CSV lives."""
    return f"data/processed/race_results_{year}.csv"
