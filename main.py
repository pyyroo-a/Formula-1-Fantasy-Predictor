"""
PitWall backend entry point.

This file only sets the app up: startup (load results, prices and the schedule),
CORS, and plugging in the endpoint files from src/api/. The endpoints themselves
live in src/api/, one file per area.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import fastf1
import os

os.makedirs("data/cache", exist_ok=True)
os.makedirs("data", exist_ok=True)


from src.pipeline import run_pipeline
from src.fetch_prices import fetch_prices, save_prices, save_price_history, fetch_price_changes
from src.fetch_results import update_season_results
from src.config import SEASON, results_path
from src.api import state, races, prices, teams, race_weekend, dev


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-fetch any completed races this season that aren't in the CSV yet
    added = update_season_results(SEASON, results_path())
    if added:
        print(f"Auto-loaded new races: {added}")

    state.fantasy_table = run_pipeline()
    print(f"Pipeline loaded with {len(state.fantasy_table)} rows")

    # Load prices for the UPCOMING round (latest completed + 1) — that's what the
    # fantasy game charges for this weekend's team. The old code loaded the latest
    # *completed* round instead, which is why weekend budgets came out stale (and
    # it overwrote prices.json back to the old round on every restart). Fall back
    # to the completed round if the next round's feed isn't published yet.
    latest_completed = int(state.fantasy_table["RoundNumber"].max())
    price_round = None
    for target in (latest_completed + 1, latest_completed):
        try:
            state.current_prices = fetch_prices(target)
            save_prices(target)
            save_price_history(target)
            price_round = target
            print(f"Prices loaded for round {target}")
            break
        except Exception as e:
            print(f"Warning: could not fetch prices for round {target} — {e}")
            state.current_prices = {"drivers": {}, "constructors": {}}

    try:
        change_round = price_round or latest_completed
        state.price_changes = fetch_price_changes(change_round)
        print(f"Price changes loaded (round {change_round} vs {change_round - 1})")
    except Exception as e:
        print(f"Warning: could not fetch price changes — {e}")
        state.price_changes = {"drivers": {}, "constructors": {}}

    try:
        fastf1.Cache.enable_cache("data/cache")
        state.race_schedule = fastf1.get_event_schedule(SEASON, include_testing=False)
        print(f"Race schedule loaded: {len(state.race_schedule)} events")
    except Exception as e:
        print(f"Warning: could not load race schedule — {e}")
        state.race_schedule = None

    yield


app = FastAPI(lifespan=lifespan)

cors_origins_env = os.getenv("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# every group of endpoints lives in its own file under src/api/
for module in (races, prices, teams, race_weekend, dev):
    app.include_router(module.router)
