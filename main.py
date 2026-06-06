from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from src.pipeline import run_pipeline
from src.fantasy import build_fantasy_team, generate_explanations

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fantasy_table = None


@app.on_event("startup")
def startup():
    global fantasy_table
    fantasy_table = run_pipeline()
    print(f"Pipeline loaded with {len(fantasy_table)} rows")


class RaceRequest(BaseModel):
    race_name: str


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


@app.get("/races")
def get_races():
    return sorted(fantasy_table["RaceName"].unique().tolist())