import fastf1
import pandas as pd
import os

fastf1.Cache.enable_cache("data/cache")


def fetch_race_results(year: int, event_name: str) -> pd.DataFrame:
    event = fastf1.get_event(year, event_name)
    session = event.get_session("Race")
    session.load(laps=False, telemetry=False, weather=False, messages=False)

    cols = ["Abbreviation", "FullName", "TeamName", "GridPosition", "Position", "Status"]
    results = session.results[cols].copy()
    results["RaceName"] = event.EventName
    results["RoundNumber"] = int(event.RoundNumber)
    results["Year"] = year

    results["Position"] = pd.to_numeric(results["Position"], errors="coerce")
    results["GridPosition"] = pd.to_numeric(results["GridPosition"], errors="coerce")

    return results


def update_season_results(year: int, path: str) -> list:
    """
    Checks the FastF1 schedule for any completed races not yet in the CSV
    and fetches + appends their results automatically.
    Returns a list of newly added race names.
    """
    schedule = fastf1.get_event_schedule(year, include_testing=False)

    if os.path.exists(path):
        existing = pd.read_csv(path)
        existing_rounds = set(existing["RoundNumber"].astype(int).unique())
    else:
        existing = pd.DataFrame()
        existing_rounds = set()

    now = pd.Timestamp.now(tz="UTC")
    added = []

    for _, event in schedule.sort_values("RoundNumber").iterrows():
        round_num = int(event["RoundNumber"])
        race_date = event["Session5Date"]

        if round_num in existing_rounds:
            continue

        if pd.isna(race_date) or pd.Timestamp(race_date) > now:
            continue

        try:
            results = fetch_race_results(year, event["EventName"])
            existing = pd.concat([existing, results], ignore_index=True)
            added.append(event["EventName"])
            print(f"Loaded results: {event['EventName']} (Round {round_num})")
        except Exception as e:
            print(f"Could not load {event['EventName']}: {e}")

    if added:
        existing.to_csv(path, index=False)
        print(f"Saved {len(added)} new race(s) to {path}")

    return added
