from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from src.pipeline import run_pipeline, predict_upcoming_race
from src.fantasy import build_fantasy_team, generate_explanations
from src.fetch_practice import get_practice_grid

fantasy_table = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global fantasy_table
    fantasy_table = run_pipeline()
    print(f"Pipeline loaded with {len(fantasy_table)} rows")
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
    session: str = "FP2"


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


@app.get("/races")
def get_races():
    return sorted(fantasy_table["RaceName"].unique().tolist())
