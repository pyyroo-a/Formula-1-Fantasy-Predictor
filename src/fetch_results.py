import fastf1
import pandas as pd
import os

fastf1.Cache.enable_cache("data/cache")


def _normalize_status(status: str) -> str:
    """Maps FastF1 raw status values to the three categories the pipeline expects."""
    if status == "Finished":
        return "Finished"
    if str(status).startswith("+"):  # "+1 Lap", "+2 Laps", etc.
        return "Lapped"
    return "DNF"


def fetch_race_results(year: int, event_name: str) -> pd.DataFrame:
    event = fastf1.get_event(year, event_name)
    session = event.get_session("Race")
    session.load(laps=False, telemetry=False, weather=False, messages=False)

    # Guard against FastF1 returning stale cached data from the wrong year
    session_year = session.date.year
    if session_year != year:
        raise ValueError(
            f"FastF1 returned {session_year} data for '{event_name}', expected {year}. "
            f"The cache may be stale — try again once FastF1 has updated."
        )

    cols = ["Abbreviation", "FullName", "TeamName", "GridPosition", "Position", "Status"]
    results = session.results[cols].copy()
    results["RaceName"] = event.EventName
    results["RoundNumber"] = int(event.RoundNumber)
    results["Year"] = year

    results["Position"] = pd.to_numeric(results["Position"], errors="coerce")
    results["GridPosition"] = pd.to_numeric(results["GridPosition"], errors="coerce")
    results["Status"] = results["Status"].apply(_normalize_status)

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
