"""
Settings shared across the whole project, so they're only written down once.

Basically when the 2027 season starts, SEASON is the one number to change here
(plus making sure this season's results are there as last season's data).
"""

import os

SEASON = 2026
PREVIOUS_SEASON = SEASON - 1


def processed_dir() -> str:
    """
    Where the results CSVs live. Always data/processed for the real app. The tests
    set PROCESSED_DIR to a frozen copy, otherwise every Monday's new race changed
    the model's training data and the golden answers went stale every week.
    """
    return os.getenv("PROCESSED_DIR", "data/processed")


def results_path(year: int = SEASON) -> str:
    """Where a season's race results CSV lives."""
    return f"{processed_dir()}/race_results_{year}.csv"


def sprint_results_path(year: int = SEASON) -> str:
    """Sprint race results. Kept apart from the main results, see src/fetch_results.py."""
    return f"{processed_dir()}/sprint_results_{year}.csv"
