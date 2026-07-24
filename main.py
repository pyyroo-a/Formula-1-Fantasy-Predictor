from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import fastf1
import os
import json

os.makedirs("data/cache", exist_ok=True)
os.makedirs("data", exist_ok=True)

LOCKED_TEAM_PATH = "data/locked_team.json"


def load_locked_team() -> dict | None:
    """Returns the saved locked team, or None if no lock file exists."""
    try:
        with open(LOCKED_TEAM_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_locked_team(data: dict) -> None:
    """Saves the locked team to disk so it survives restarts."""
    with open(LOCKED_TEAM_PATH, "w") as f:
        json.dump(data, f, indent=2)

from src.pipeline import run_pipeline, predict_upcoming_race
from src.fantasy import build_fantasy_team, generate_explanations, build_budget_team, build_budget_teams, get_race_pool
from src.fetch_practice import get_practice_grid, is_sprint_weekend
from src.fetch_prices import fetch_prices, save_prices, fetch_price_changes
from src.fetch_results import update_season_results
from src.backtest import run_backtest

fantasy_table = None
current_prices = None
price_changes = None
race_schedule = None
backtest_cache = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global fantasy_table, current_prices, price_changes, race_schedule

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
        price_changes = fetch_price_changes(latest_round)
        print(f"Price changes loaded (round {latest_round} vs {latest_round - 1})")
    except Exception as e:
        print(f"Warning: could not fetch price changes — {e}")
        price_changes = {"drivers": {}, "constructors": {}}

    try:
        fastf1.Cache.enable_cache("data/cache")
        race_schedule = fastf1.get_event_schedule(2026, include_testing=False)
        print(f"Race schedule loaded: {len(race_schedule)} events")
    except Exception as e:
        print(f"Warning: could not load race schedule — {e}")
        race_schedule = None

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

    teams = build_budget_teams(
        fantasy_table,
        request.race_name,
        current_prices,
        budget=request.budget,
    )

    if not teams:
        raise HTTPException(
            status_code=400,
            detail="No valid team found within budget. Try increasing the budget."
        )

    return {"teams": teams}


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

    # Auto-fallback: try requested session, then work backwards
    sessions_to_try = [request.session]
    if request.session == "FP3":
        sessions_to_try = ["FP3", "FP2", "FP1"]
    elif request.session == "FP2":
        sessions_to_try = ["FP2", "FP1"]

    practice_df = None
    session_used = None
    last_error = None

    for sess in sessions_to_try:
        try:
            practice_df = get_practice_grid(request.year, request.race_name, sess)
            session_used = sess
            break
        except Exception as e:
            last_error = str(e)
            continue

    if practice_df is None:
        raise HTTPException(status_code=400, detail=f"No practice data available yet. {last_error}")

    upcoming_table = predict_upcoming_race(practice_df)

    pool = get_race_pool(upcoming_table, request.race_name, current_prices)
    if not pool["drivers"]:
        raise HTTPException(status_code=400, detail="No priced drivers found for that race.")

    optimal = build_budget_team(upcoming_table, request.race_name, current_prices, budget=100.0)

    return {"pool": pool, "optimal": optimal, "session_used": session_used}


@app.post("/race-sessions")
def get_race_sessions(request: RaceRequest):
    """Returns session times for a given race so the frontend can show availability."""
    if race_schedule is None:
        raise HTTPException(status_code=503, detail="Schedule not available")

    now = pd.Timestamp.now(tz="UTC")
    event = race_schedule[race_schedule["EventName"] == request.race_name]
    if event.empty:
        raise HTTPException(status_code=404, detail="Race not found in schedule")

    row = event.iloc[0]
    is_sprint = "sprint" in str(row.get("EventFormat", "")).lower()

    if is_sprint:
        sessions = [
            {"name": "FP1", "date": row.get("Session1Date")},
            {"name": "Sprint Qualifying", "date": row.get("Session2Date")},
            {"name": "Sprint", "date": row.get("Session3Date")},
            {"name": "Qualifying", "date": row.get("Session4Date")},
            {"name": "Race", "date": row.get("Session5Date")},
        ]
    else:
        sessions = [
            {"name": "FP1", "date": row.get("Session1Date")},
            {"name": "FP2", "date": row.get("Session2Date")},
            {"name": "FP3", "date": row.get("Session3Date")},
            {"name": "Qualifying", "date": row.get("Session4Date")},
            {"name": "Race", "date": row.get("Session5Date")},
        ]

    result = []
    for s in sessions:
        d = s["date"]
        if pd.isna(d):
            continue
        ts = pd.Timestamp(d)
        result.append({
            "name": s["name"],
            "date": ts.isoformat(),
            "available": ts < now,
        })

    return {"sessions": result, "is_sprint": is_sprint}


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


@app.get("/price-changes")
def get_price_changes():
    return price_changes


HIGH_ATTRITION_CIRCUITS = {
    "Azerbaijan Grand Prix", "Singapore Grand Prix", "Monaco Grand Prix",
    "Las Vegas Grand Prix", "Saudi Arabian Grand Prix", "Miami Grand Prix",
}


class ChipAdvisorRequest(BaseModel):
    race_name: str
    my_drivers: list[str]
    my_constructors: list[str]


@app.post("/chip-advisor")
def get_chip_advisor(request: ChipAdvisorRequest):
    if not current_prices or not current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    sessions_to_try = ["FP3", "FP2", "FP1"]
    practice_df = None
    session_used = None
    last_error = None

    for sess in sessions_to_try:
        try:
            practice_df = get_practice_grid(2026, request.race_name, sess)
            session_used = sess
            break
        except Exception as e:
            last_error = str(e)
            continue

    if practice_df is None:
        raise HTTPException(status_code=400, detail=f"No practice data available yet. {last_error}")

    upcoming_table = predict_upcoming_race(practice_df)
    pool = get_race_pool(upcoming_table, request.race_name, current_prices)

    if not pool["drivers"]:
        raise HTTPException(status_code=400, detail="No priced drivers found for this race.")

    driver_map = {d["Abbreviation"]: d for d in pool["drivers"]}
    constructor_map = {c["name"]: c for c in pool["constructors"]}

    my_driver_score = sum(driver_map.get(a, {}).get("FantasyValue", 0) for a in request.my_drivers)
    my_constructor_score = sum(constructor_map.get(n, {}).get("score", 0) for n in request.my_constructors)
    my_team_score = my_driver_score + my_constructor_score

    optimal = build_budget_team(upcoming_table, request.race_name, current_prices, budget=100.0)
    optimal_score = optimal["total_score"] if optimal else my_team_score

    limitless = build_budget_team(upcoming_table, request.race_name, current_prices, budget=999.0)
    limitless_score = limitless["total_score"] if limitless else optimal_score

    wildcard_gain = max(0.0, round(optimal_score - my_team_score, 1))
    limitless_gain = max(0.0, round(limitless_score - my_team_score, 1))

    sorted_drivers = sorted(pool["drivers"], key=lambda d: d["FantasyValue"], reverse=True)
    # 3× Boost upgrades your boost driver from 2× to 3× for one race, so the
    # marginal gain is one extra copy of the best driver's fantasy value.
    boost_target = sorted_drivers[0] if sorted_drivers else None
    boost_gain = round(boost_target["FantasyValue"], 1) if boost_target else 0.0

    my_drivers_in_pool = [driver_map[a] for a in request.my_drivers if a in driver_map]
    riskiest = min(my_drivers_in_pool, key=lambda d: d["FantasyValue"]) if my_drivers_in_pool else None

    is_high_attrition = request.race_name in HIGH_ATTRITION_CIRCUITS
    dnf_risk_pct = 120 if is_high_attrition else 65

    def grade(gain, thresholds):
        play, consider = thresholds
        if gain >= play:
            return "PLAY"
        if gain >= consider:
            return "CONSIDER"
        return "HOLD"

    return {
        "session_used": session_used,
        "my_team_score": round(my_team_score, 2),
        "chips": {
            "limitless": {
                "gain": limitless_gain,
                "team": limitless,
                "recommendation": grade(limitless_gain, (40, 20)),
            },
            "wildcard": {
                "gain": wildcard_gain,
                "optimal_team": optimal,
                "recommendation": grade(wildcard_gain, (25, 12)),
            },
            "x3_boost": {
                "gain": boost_gain,
                "target": boost_target["Abbreviation"] if boost_target else None,
                "recommendation": grade(boost_gain, (30, 15)),
            },
            "final_fix": {
                "riskiest_driver": riskiest["Abbreviation"] if riskiest else None,
                "recommendation": "POST-QUALI",
            },
            "no_negative": {
                "dnf_risk_pct": dnf_risk_pct,
                "is_high_attrition": is_high_attrition,
                "recommendation": "HEDGE" if is_high_attrition else "HOLD",
            },
            "autopilot": {
                "recommendation": "SAVE",
            },
        },
    }


@app.post("/race-results")
def get_race_results(request: RaceRequest):
    try:
        df = pd.read_csv("data/processed/race_results_2026.csv")
    except Exception:
        raise HTTPException(status_code=503, detail="Race data unavailable")

    race_df = df[df["RaceName"] == request.race_name].copy()
    if race_df.empty:
        raise HTTPException(status_code=404, detail="Race not found")

    race_df["Position"] = pd.to_numeric(race_df["Position"], errors="coerce")
    race_df["GridPosition"] = pd.to_numeric(race_df["GridPosition"], errors="coerce")
    race_df["PositionChange"] = race_df["GridPosition"] - race_df["Position"]

    finishers = race_df[race_df["Status"] != "DNF"].sort_values("Position")
    dnfs = race_df[race_df["Status"] == "DNF"]
    ordered = pd.concat([finishers, dnfs], ignore_index=True)

    result = []
    for _, row in ordered.iterrows():
        result.append({
            "Abbreviation": row["Abbreviation"],
            "FullName": row["FullName"],
            "TeamName": row["TeamName"],
            "GridPosition": None if pd.isna(row["GridPosition"]) else int(row["GridPosition"]),
            "Position": None if pd.isna(row["Position"]) else int(row["Position"]),
            "PositionChange": None if pd.isna(row.get("PositionChange")) else int(row["PositionChange"]),
            "Status": row["Status"],
        })
    return result


@app.post("/qualifying-results")
def get_qualifying_results(request: RaceRequest):
    try:
        df = pd.read_csv("data/processed/race_results_2026.csv")
        race_data = df[df["RaceName"] == request.race_name]
        if race_data.empty:
            raise HTTPException(status_code=404, detail="Race not found in 2026 data")
        year = int(race_data["Year"].iloc[0])

        fastf1.Cache.enable_cache("data/cache")
        session = fastf1.get_session(year, request.race_name, "Q")
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results.copy()

        def fmt_time(t):
            if pd.isna(t):
                return None
            total_ms = int(t.total_seconds() * 1000)
            mins = total_ms // 60000
            secs = (total_ms % 60000) / 1000
            return f"{mins}:{secs:06.3f}"

        output = []
        for _, row in results.sort_values("Position").iterrows():
            pos = row.get("Position")
            output.append({
                "Position": None if pd.isna(pos) else int(pos),
                "Abbreviation": row["Abbreviation"],
                "FullName": row["FullName"],
                "TeamName": row["TeamName"],
                "Q1": fmt_time(row.get("Q1")),
                "Q2": fmt_time(row.get("Q2")),
                "Q3": fmt_time(row.get("Q3")),
            })
        return output
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch qualifying: {str(e)}")


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

    # Return the locked team immediately if it belongs to this race weekend.
    # The lock is set the first time FP3 data becomes available and never
    # changes mid-weekend — qualifying/race results don't affect it.
    locked = load_locked_team()
    if locked and locked.get("race_name") == race_name:
        # Support both the new multi-team lock and any older single-team lock.
        locked_teams = locked.get("teams") or ([locked["team"]] if locked.get("team") else [])
        return {
            "active": True,
            "race_name": race_name,
            "session_used": locked["session_used"],
            "days_until": round(days_until_race, 1),
            "race_date": race_date.isoformat(),
            "locked": True,
            "locked_at": locked["locked_at"],
            "teams": locked_teams,
            "team": locked_teams[0] if locked_teams else None,
        }

    # No lock yet for this race — try to fetch practice data and generate one.
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
            "message": "No practice data available yet — team will lock once FP3 is complete",
            "team": None,
        }

    try:
        upcoming_table = predict_upcoming_race(practice_df)
        teams = build_budget_teams(upcoming_table, race_name, current_prices, budget=100.0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    if not teams:
        return {
            "active": True,
            "race_name": race_name,
            "days_until": round(days_until_race, 1),
            "message": "Could not build a team within budget for this weekend.",
            "teams": [],
            "team": None,
        }

    # Lock these teams — they won't change again until a new race weekend starts.
    locked_at = pd.Timestamp.now(tz="UTC").isoformat()
    save_locked_team({
        "race_name": race_name,
        "session_used": session_used,
        "locked_at": locked_at,
        "teams": teams,
    })

    return {
        "active": True,
        "race_name": race_name,
        "session_used": session_used,
        "days_until": round(days_until_race, 1),
        "race_date": race_date.isoformat(),
        "locked": True,
        "locked_at": locked_at,
        "teams": teams,
        "team": teams[0],
    }


@app.get("/backtest")
def get_backtest(refresh: bool = False):
    """
    Replays completed 2026 races with the model trained only on prior races,
    and compares its picks against a grid-order baseline.

    Local analysis tool — disabled unless BACKTEST_ENABLED=true. It retrains the
    model once per race (~1-2 min of CPU), so leaving it open in production would
    let anyone stall the backend. Result is cached in memory after the first run.
    """
    global backtest_cache

    if os.getenv("BACKTEST_ENABLED", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=404, detail="Not found")

    if backtest_cache is None or refresh:
        try:
            backtest_cache = run_backtest(fallback_prices=current_prices)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Backtest failed: {e}")

    return backtest_cache


@app.post("/unlock-team")
def unlock_team():
    """Clears the locked team so it regenerates fresh on the next request."""
    if os.path.exists(LOCKED_TEAM_PATH):
        os.remove(LOCKED_TEAM_PATH)
        return {"message": "Team unlocked — will regenerate on next request"}
    return {"message": "No locked team to clear"}


@app.get("/weekend-finishes")
def get_weekend_finishes():
    """
    Predicted finishing order for the active race weekend, once practice data
    exists. For the F1 Predict game mode — separate from fantasy team building.

    Returns two orderings side by side:
      - model:    the model's own forecast (blend before shrink-to-grid)
      - baseline: the practice-pace order (the backtest's winning strategy)

    Only ever covers the upcoming weekend; completed races are not shown.
    """
    try:
        fastf1.Cache.enable_cache("data/cache")
        schedule = fastf1.get_event_schedule(2026, include_testing=False)
        now = pd.Timestamp.now(tz="UTC")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch schedule: {e}")

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

    race_name = upcoming["EventName"]
    race_date = pd.Timestamp(upcoming["Session5Date"])
    days_until = (race_date - now).total_seconds() / 86400

    if days_until > 5:
        return {
            "active": False,
            "race_name": race_name,
            "days_until": round(days_until, 1),
            "message": f"Next race in {round(days_until)} days",
        }

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
            "days_until": round(days_until, 1),
            "message": "No practice data yet — finishes appear once FP3 is complete",
            "predictions": None,
        }

    try:
        table = predict_upcoming_race(practice_df).copy()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    # Model order = rank of the pre-shrink model forecast.
    # Baseline order = practice-pace order, which is the GridPosition estimate.
    table["ModelRank"] = table["ModelPredicted"].rank(method="first").astype(int)

    predictions = []
    for _, r in table.sort_values("ModelRank").iterrows():
        baseline_pos = int(round(r["GridPosition"]))
        model_pos = int(r["ModelRank"])
        predictions.append({
            "abbreviation": r["Abbreviation"],
            "team": r["TeamName"],
            "model_pos": model_pos,
            "baseline_pos": baseline_pos,
            # positive = model expects them to finish higher than practice order does
            "delta": baseline_pos - model_pos,
        })

    return {
        "active": True,
        "race_name": race_name,
        "session_used": session_used,
        "days_until": round(days_until, 1),
        "predictions": predictions,
    }
