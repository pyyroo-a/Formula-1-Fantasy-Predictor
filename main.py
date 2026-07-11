from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import fastf1

from src.pipeline import run_pipeline, predict_upcoming_race
from src.fantasy import build_fantasy_team, generate_explanations, build_budget_team, get_race_pool
from src.fetch_practice import get_practice_grid, is_sprint_weekend
from src.fetch_prices import fetch_prices, save_prices
from src.fetch_results import update_season_results

fantasy_table = None
current_prices = None
race_schedule = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global fantasy_table, current_prices, race_schedule

    # Auto-fetch any completed 2026 races not yet in the CSV
    added = update_season_results(2026, "data/processed/race_results_2026.csv")
    if added:
        print(f"Auto-loaded new races: {added}")

    fantasy_table = run_pipeline()
    print(f"Pipeline loaded with {len(fantasy_table)} rows")

    latest_round = int(fantasy_table["RoundNumber"].max())
    try:
        current_prices = fetch_prices(latest_round)
        save_prices(latest_round)
        print(f"Prices loaded for race {latest_round}")
    except Exception as e:
        print(f"Warning: could not fetch prices — {e}")
        current_prices = {"drivers": {}, "constructors": {}}

    try:
        fastf1.Cache.enable_cache("data/cache")
        race_schedule = fastf1.get_event_schedule(2026, include_testing=False)
        print(f"Race schedule loaded: {len(race_schedule)} events")
    except Exception as e:
        print(f"Warning: could not load race schedule — {e}")
        race_schedule = None

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RaceRequest(BaseModel):
    race_name: str


class UpcomingRaceRequest(BaseModel):
    year: int
    race_name: str
    session: str = "FP3"


class BudgetRequest(BaseModel):
    race_name: str
    budget: float = 100.0


@app.post("/predict")
def get_fantasy_team(request: RaceRequest):
    team = build_fantasy_team(fantasy_table, request.race_name)
    team = generate_explanations(team)

    return team[[
        "Abbreviation",
        "TeamName",
        "GridPosition",
        "Position",
        "Predicted",
        "PickCategory",
        "Explanation",
        "FantasyValue"
    ]].to_dict(orient="records")


@app.post("/predict-upcoming")
def get_upcoming_team(request: UpcomingRaceRequest):
    try:
        practice_df = get_practice_grid(request.year, request.race_name, request.session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch practice data: {str(e)}")

    upcoming_table = predict_upcoming_race(practice_df)
    team = build_fantasy_team(upcoming_table, request.race_name)
    team = generate_explanations(team)

    return team[[
        "Abbreviation",
        "TeamName",
        "GridPosition",
        "Predicted",
        "PickCategory",
        "Explanation",
        "FantasyValue"
    ]].to_dict(orient="records")


@app.post("/predict-budget")
def get_budget_team(request: BudgetRequest):
    if not current_prices or not current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    result = build_budget_team(
        fantasy_table,
        request.race_name,
        current_prices,
        budget=request.budget,
    )

    if result is None:
        raise HTTPException(
            status_code=400,
            detail="No valid team found within budget. Try increasing the budget."
        )

    return result


@app.post("/race-pool")
def get_race_pool_endpoint(request: RaceRequest):
    if not current_prices or not current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    result = get_race_pool(fantasy_table, request.race_name, current_prices)

    if not result["drivers"]:
        raise HTTPException(status_code=400, detail="No priced drivers found for that race.")

    return result


@app.get("/races")
def get_races():
    return sorted(fantasy_table["RaceName"].unique().tolist())


@app.get("/upcoming-races")
def get_upcoming_races():
    completed = set(fantasy_table["RaceName"].unique())

    if race_schedule is not None:
        now = pd.Timestamp.now(tz="UTC")
        result = []
        for _, event in race_schedule.sort_values("RoundNumber").iterrows():
            if event["EventName"] in completed:
                continue
            race_date = event["Session5Date"]
            if pd.isna(race_date):
                continue
            # Skip races that finished more than 2 days ago (in case results haven't loaded yet)
            if pd.Timestamp(race_date) < now - pd.Timedelta(days=2):
                continue
            is_sprint = "sprint" in str(event.get("EventFormat", "")).lower()
            result.append({
                "race_name": event["EventName"],
                "is_sprint": is_sprint,
            })
        return result

    # Fallback: hardcoded remainder of 2026 calendar
    fallback = [
        "Belgian Grand Prix", "Hungarian Grand Prix", "Dutch Grand Prix",
        "Italian Grand Prix", "Azerbaijan Grand Prix", "Singapore Grand Prix",
        "United States Grand Prix", "Mexico City Grand Prix", "São Paulo Grand Prix",
        "Las Vegas Grand Prix", "Qatar Grand Prix", "Abu Dhabi Grand Prix",
    ]
    return [
        {"race_name": r, "is_sprint": is_sprint_weekend(r)}
        for r in fallback
        if r not in completed
    ]


@app.post("/upcoming-race-pool")
def get_upcoming_race_pool(request: UpcomingRaceRequest):
    if not current_prices or not current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    try:
        practice_df = get_practice_grid(request.year, request.race_name, request.session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch practice data: {str(e)}")

    upcoming_table = predict_upcoming_race(practice_df)

    pool = get_race_pool(upcoming_table, request.race_name, current_prices)
    if not pool["drivers"]:
        raise HTTPException(status_code=400, detail="No priced drivers found for that race.")

    optimal = build_budget_team(upcoming_table, request.race_name, current_prices, budget=100.0)

    return {"pool": pool, "optimal": optimal}


@app.get("/next-race")
def get_next_race():
    try:
        fastf1.Cache.enable_cache("data/cache")
        schedule = fastf1.get_event_schedule(2026, include_testing=False)
        now = pd.Timestamp.now(tz="UTC")

        for _, event in schedule.sort_values("RoundNumber").iterrows():
            race_date = event["Session5Date"]
            if pd.isna(race_date):
                continue
            if pd.Timestamp(race_date) > now:
                return {
                    "race_name": event["EventName"],
                    "round_number": int(event["RoundNumber"]),
                    "race_date": pd.Timestamp(race_date).isoformat(),
                }
        return None
    except Exception:
        return None


@app.get("/prices")
def get_prices():
    return current_prices


@app.get("/weekend-team")
def get_weekend_team():
    """
    Auto-detects the current race weekend and returns the optimal budget team
    using the best available practice session (FP3 → FP2 → FP1).
    Returns None if no race weekend is active.
    """
    if not current_prices or not current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    try:
        fastf1.Cache.enable_cache("data/cache")
        schedule = fastf1.get_event_schedule(2026, include_testing=False)
        now = pd.Timestamp.now(tz="UTC")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch schedule: {e}")

    # Find the next upcoming race
    upcoming = None
    for _, event in schedule.sort_values("RoundNumber").iterrows():
        race_date = event["Session5Date"]
        if pd.isna(race_date):
            continue
        if pd.Timestamp(race_date) > now:
            upcoming = event
            break

    if upcoming is None:
        return {"active": False, "message": "Season complete"}

    race_date = pd.Timestamp(upcoming["Session5Date"])
    days_until_race = (race_date - now).total_seconds() / 86400

    # Only active within 5 days before the race
    if days_until_race > 5:
        return {
            "active": False,
            "race_name": upcoming["EventName"],
            "days_until": round(days_until_race, 1),
            "message": f"Next race in {round(days_until_race)} days",
        }

    race_name = upcoming["EventName"]

    # Try sessions from best to fallback
    sessions_to_try = ["FP3", "FP2", "FP1"] if not is_sprint_weekend(race_name) else ["FP1"]
    practice_df = None
    session_used = None

    for sess in sessions_to_try:
        try:
            practice_df = get_practice_grid(2026, race_name, sess)
            session_used = sess
            break
        except Exception:
            continue

    if practice_df is None:
        return {
            "active": True,
            "race_name": race_name,
            "days_until": round(days_until_race, 1),
            "message": "No practice data available yet",
            "team": None,
        }

    try:
        upcoming_table = predict_upcoming_race(practice_df)
        result = build_budget_team(upcoming_table, race_name, current_prices, budget=100.0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    return {
        "active": True,
        "race_name": race_name,
        "session_used": session_used,
        "days_until": round(days_until_race, 1),
        "race_date": race_date.isoformat(),
        "team": result,
    }
