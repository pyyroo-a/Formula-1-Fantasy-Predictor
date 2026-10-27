"""
Weekly refresh: fetches any completed 2026 races not yet in the CSV and appends
them, then refreshes F1 Fantasy prices for the upcoming round.

Prints a summary for the GitHub Actions log. A price-fetch failure is caught so
it can never fail the race-data update, the two are independent.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from src.config import SEASON, results_path, sprint_results_path
from src.fetch_results import update_season_results, update_sprint_results
from src.fetch_prices import save_prices, save_price_history
from src import official_points


def main():
    csv_path = results_path()

    added = update_season_results(SEASON, csv_path)

    if added:
        print(f"::notice::Added {len(added)} new race(s): {', '.join(added)}")
    else:
        print("::notice::No new races to add.")

    # sprint weekends score points twice, so we keep those results too
    try:
        sprints = update_sprint_results(SEASON, sprint_results_path())
        if sprints:
            print(f"::notice::Added {len(sprints)} new sprint(s): {', '.join(sprints)}")
    except Exception as e:
        print(f"::warning::Could not update sprint results: {e}")

    # Refresh prices for the upcoming round = latest completed round + 1.
    # The F1 Fantasy feed publishes the next round's prices right after a race.
    try:
        completed = pd.read_csv(csv_path)
        upcoming_round = int(completed["RoundNumber"].astype(int).max()) + 1
        save_prices(upcoming_round)
        save_price_history(upcoming_round)
        print(f"::notice::Refreshed prices for upcoming round {upcoming_round}.")
    except Exception as e:
        # Never let a price hiccup fail the race-data job; results are what matter.
        print(f"::warning::Could not refresh prices: {e}")

    # the game's own points for the round that just finished, the scorecard grades with
    # these (src/official_points.py). same deal as prices, a failure here never stops the job
    try:
        latest = int(pd.read_csv(csv_path)["RoundNumber"].astype(int).max())
        pts = official_points.fetch_official_points(latest)
        if official_points.is_raced(pts):
            official_points.save_official_round(latest, pts)
            print(f"::notice::Saved official points for round {latest}.")
        else:
            print(f"::warning::Round {latest} has no official points in the feed yet.")
    except Exception as e:
        print(f"::warning::Could not save official points: {e}")


if __name__ == "__main__":
    main()
