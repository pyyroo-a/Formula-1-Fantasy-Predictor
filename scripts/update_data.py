"""
Weekly refresh: fetches any completed 2026 races not yet in the CSV and appends
them, then refreshes F1 Fantasy prices for the upcoming round.

Prints a summary for the GitHub Actions log. A price-fetch failure is caught so
it can never fail the race-data update — the two are independent.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from src.fetch_results import update_season_results
from src.fetch_prices import save_prices, save_price_history

CSV_PATH = "data/processed/race_results_2026.csv"

added = update_season_results(2026, CSV_PATH)

if added:
    print(f"::notice::Added {len(added)} new race(s): {', '.join(added)}")
else:
    print("::notice::No new races to add.")

# Refresh prices for the upcoming round = latest completed round + 1.
# The F1 Fantasy feed publishes the next round's prices right after a race.
try:
    completed = pd.read_csv(CSV_PATH)
    upcoming_round = int(completed["RoundNumber"].astype(int).max()) + 1
    save_prices(upcoming_round)
    save_price_history(upcoming_round)
    print(f"::notice::Refreshed prices for upcoming round {upcoming_round}.")
except Exception as e:
    # Never let a price hiccup fail the race-data job; results are what matter.
    print(f"::warning::Could not refresh prices: {e}")
