from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from src.pipeline import run_pipeline, predict_upcoming_race
from src.fantasy import build_fantasy_team, generate_explanations, build_budget_team
from src.fetch_practice import get_practice_grid, is_sprint_weekend
from src.fetch_prices import fetch_prices, save_prices

fantasy_table = None
current_prices = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global fantasy_table, current_prices

    fantasy_table = run_pipeline()
    print(f"Pipeline loaded with {len(fantasy_table)} rows")

    # Derive the latest completed race_id from the 2026 data
    latest_round = int(fantasy_table["RoundNumber"].max())
    try:
        current_prices = fetch_prices(latest_round)
        save_prices(latest_round)
        print(f"Prices loaded for race {latest_round}")
    except Exception as e:
        print(f"Warning: could not fetch prices — {e}")
        current_prices = {"drivers": {}, "constructors": {}}

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


@app.get("/races")
def get_races():
    return sorted(fantasy_table["RaceName"].unique().tolist())


@app.get("/upcoming-races")
def get_upcoming_races():
    completed = set(fantasy_table["RaceName"].unique())
    all_2026 = [
        "Hungarian Grand Prix",
        "Belgian Grand Prix",
        "Dutch Grand Prix",
        "Italian Grand Prix",
        "Azerbaijan Grand Prix",
        "Singapore Grand Prix",
        "United States Grand Prix",
        "Mexico City Grand Prix",
        "São Paulo Grand Prix",
        "Las Vegas Grand Prix",
        "Qatar Grand Prix",
        "Abu Dhabi Grand Prix",
    ]
    return [
        {"race_name": r, "is_sprint": is_sprint_weekend(r)}
        for r in all_2026
        if r not in completed
    ]


@app.get("/prices")
def get_prices():
    return current_prices
