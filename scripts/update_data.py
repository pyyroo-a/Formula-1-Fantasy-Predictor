"""
Fetches any completed 2026 races not yet in the CSV and appends them.
Exits with code 0 always; prints a summary for the GitHub Actions log.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.fetch_results import update_season_results

CSV_PATH = "data/processed/race_results_2026.csv"

added = update_season_results(2026, CSV_PATH)

if added:
    print(f"::notice::Added {len(added)} new race(s): {', '.join(added)}")
else:
    print("::notice::No new races to add.")
