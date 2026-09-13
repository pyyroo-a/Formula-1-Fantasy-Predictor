from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import fastf1
import os
import json
import hmac
import threading

os.makedirs("data/cache", exist_ok=True)
os.makedirs("data", exist_ok=True)






from src.pipeline import run_pipeline, predict_upcoming_race
from src.fantasy import build_fantasy_team, generate_explanations, build_budget_team, build_budget_teams, get_race_pool
from src.fetch_practice import get_practice_grid, is_sprint_weekend
from src.fetch_prices import fetch_prices, save_prices, save_price_history, fetch_price_changes
from src.fetch_results import update_season_results
from src.backtest import run_backtest
from src.dnf import DNFModel, USE_DNF_RISK
from src.data_loader import load_dataset
from src.weekend import (
    evaluate_team_chips,
    upcoming_dnf_probs,
    build_finish_predictions,
    final_practice_session,
    session_finished,
    session_published,
    results_already_in_data,
    build_snapshot,
)
from src.snapshots import find_snapshot, latest_snapshot, save_snapshot, commit_to_github


# kept under its old name because a few endpoints below still call it that
_upcoming_dnf_probs = upcoming_dnf_probs


def _now() -> pd.Timestamp:
    # wrapped in a function so tests can pretend it's a different point in the weekend
    return pd.Timestamp.now(tz="UTC")


def _load_schedule():
    fastf1.Cache.enable_cache("data/cache")
    return fastf1.get_event_schedule(2026, include_testing=False)


def _next_race(schedule, now):
    """The next race that hasn't started yet, or None once the season is over."""
    for _, event in schedule.sort_values("RoundNumber").iterrows():
        race_date = event["Session5Date"]
        if pd.isna(race_date):
            continue
        if pd.Timestamp(race_date) > now:
            return event
    return None


def _team_payload(snap: dict, **extra) -> dict:
    """Turns a saved snapshot into the shape the Overview already knows how to show."""
    teams = snap.get("teams") or []
    return {
        "active": True,
        "race_name": snap.get("race_name"),
        "round": snap.get("round"),
        "session_used": snap.get("session_used"),
        "locked": True,
        "locked_at": snap.get("locked_at"),
        "source": snap.get("source"),
        "teams": teams,
        "team": teams[0] if teams else None,
        **extra,
    }

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

    # Load prices for the UPCOMING round (latest completed + 1) — that's what the
    # fantasy game charges for this weekend's team. The old code loaded the latest
    # *completed* round instead, which is why weekend budgets came out stale (and
    # it overwrote prices.json back to the old round on every restart). Fall back
    # to the completed round if the next round's feed isn't published yet.
    latest_completed = int(fantasy_table["RoundNumber"].max())
    price_round = None
    for target in (latest_completed + 1, latest_completed):
        try:
            current_prices = fetch_prices(target)
            save_prices(target)
            save_price_history(target)
            price_round = target
            print(f"Prices loaded for round {target}")
            break
        except Exception as e:
            print(f"Warning: could not fetch prices for round {target} — {e}")
            current_prices = {"drivers": {}, "constructors": {}}

    try:
        change_round = price_round or latest_completed
        price_changes = fetch_price_changes(change_round)
        print(f"Price changes loaded (round {change_round} vs {change_round - 1})")
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


class PracticeRequest(BaseModel):
    race_name: str
    session: str = ""  # empty = auto-pick the final practice session that exists


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

    pool = get_race_pool(upcoming_table, request.race_name, current_prices,
                         dnf_probs=_upcoming_dnf_probs(upcoming_table, request.race_name))
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
    pool = get_race_pool(upcoming_table, request.race_name, current_prices,
                         dnf_probs=_upcoming_dnf_probs(upcoming_table, request.race_name))

    if not pool["drivers"]:
        raise HTTPException(status_code=400, detail="No priced drivers found for this race.")

    optimal = build_budget_team(upcoming_table, request.race_name, current_prices, budget=100.0)
    limitless = build_budget_team(upcoming_table, request.race_name, current_prices, budget=999.0)

    my_team_score = (
        sum({d["Abbreviation"]: d for d in pool["drivers"]}.get(a, {}).get("FantasyValue", 0) for a in request.my_drivers)
        + sum({c["name"]: c for c in pool["constructors"]}.get(n, {}).get("score", 0) for n in request.my_constructors)
    )
    optimal_score = optimal["total_score"] if optimal else my_team_score
    limitless_score = limitless["total_score"] if limitless else optimal_score

    chips = evaluate_team_chips(
        request.my_drivers, request.my_constructors, pool,
        optimal_score, limitless_score, request.race_name,
    )
    # The manual advisor also surfaces the full suggested teams for the two
    # rebuild chips; the auto-advisor (per generated team) omits these to stay light.
    chips["limitless"]["team"] = limitless
    chips["wildcard"]["optimal_team"] = optimal

    return {
        "session_used": session_used,
        "my_team_score": chips["my_team_score"],
        "chips": chips,
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


@app.post("/practice-results")
def get_practice_results(request: PracticeRequest):
    """
    Returns the fastest-lap classification for a practice session, plus the list
    of practice sessions that actually exist for the weekend. Sprint weekends run
    only FP1, so the available sessions are read from the real schedule rather
    than assumed — this works for past sprints too, which the hardcoded sprint
    list doesn't cover.
    """
    try:
        df = pd.read_csv("data/processed/race_results_2026.csv")
        race_data = df[df["RaceName"] == request.race_name]
        year = int(race_data["Year"].iloc[0]) if not race_data.empty else 2026
    except Exception:
        year = 2026

    try:
        fastf1.Cache.enable_cache("data/cache")
        event = fastf1.get_event(year, request.race_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load event: {str(e)}")

    # Read which practice sessions the weekend actually ran (Session1..Session5).
    practice_names = {"Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3"}
    available = []
    for i in range(1, 6):
        name = event.get(f"Session{i}")
        if name in practice_names:
            available.append(practice_names[name])
    available.sort()  # FP1 → FP2 → FP3

    if not available:
        raise HTTPException(status_code=404, detail="No practice sessions for this race")

    # Use the requested session if it exists this weekend, else the final one.
    session_name = request.session if request.session in available else available[-1]

    try:
        sess = event.get_session(session_name)
        sess.load(laps=True, telemetry=False, weather=False, messages=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch {session_name}: {str(e)}")

    laps = sess.laps[["Driver", "Team", "LapTime"]].dropna(subset=["LapTime"]).copy()
    if laps.empty:
        raise HTTPException(status_code=404, detail=f"No lap data available for {session_name} yet")

    fastest = (
        laps.groupby("Driver")["LapTime"].min().reset_index()
        .sort_values("LapTime").reset_index(drop=True)
    )
    teams = laps.groupby("Driver")["Team"].first()
    pole = fastest["LapTime"].min()

    name_map = {}
    try:
        for _, r in sess.results.iterrows():
            name_map[r["Abbreviation"]] = r["FullName"]
    except Exception:
        pass

    def fmt_time(t):
        total_ms = int(t.total_seconds() * 1000)
        mins = total_ms // 60000
        secs = (total_ms % 60000) / 1000
        return f"{mins}:{secs:06.3f}"

    output = []
    for i, row in fastest.iterrows():
        drv = row["Driver"]
        lap = row["LapTime"]
        output.append({
            "Position": int(i) + 1,
            "Abbreviation": drv,
            "FullName": name_map.get(drv, drv),
            "TeamName": teams.get(drv, ""),
            "LapTime": fmt_time(lap),
            "GapToPole": round((lap - pole).total_seconds(), 3),
        })

    return {"session": session_name, "available_sessions": available, "results": output}


@app.get("/weekend-team")
def get_weekend_team():
    """
    The team for the current race weekend.

    If this weekend already has a snapshot we just return it. It never gets rebuilt,
    so restarts, the race starting or opening the site again can't change it.

    Before the snapshot exists (final practice not published and saved yet) we work
    out a live preview and mark it provisional. Nothing is saved from here. Saving
    only happens in POST /snapshot/auto or scripts/lock_team.py.
    """
    try:
        schedule = _load_schedule()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch schedule: {e}")
    now = _now()

    upcoming = _next_race(schedule, now)
    if upcoming is None:
        return {"active": False, "message": "Season complete"}

    race_name = upcoming["EventName"]
    race_date = pd.Timestamp(upcoming["Session5Date"])
    days_until = round((race_date - now).total_seconds() / 86400, 1)

    snap = find_snapshot(race_name)
    if snap:
        return _team_payload(snap, days_until=days_until, race_date=race_date.isoformat())

    if days_until > 5:
        return {
            "active": False,
            "race_name": race_name,
            "days_until": days_until,
            "message": f"Next race in {round(days_until)} days",
        }

    if not current_prices or not current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    final_session = final_practice_session(upcoming)
    sessions_to_try = ["FP1"] if final_session == "FP1" else ["FP3", "FP2", "FP1"]
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
        # no practice yet, so we say the weekend isn't live. the site then keeps
        # showing the last snapshot as a held team instead of an empty box
        return {
            "active": False,
            "race_name": race_name,
            "days_until": days_until,
            "message": f"No practice data yet, the team locks once {final_session} is published",
        }

    try:
        upcoming_table = predict_upcoming_race(practice_df)
        dnf_probs = _upcoming_dnf_probs(upcoming_table, race_name)
        teams = build_budget_teams(upcoming_table, race_name, current_prices,
                                   budget=100.0, dnf_probs=dnf_probs)
        if teams:
            pool = get_race_pool(upcoming_table, race_name, current_prices, dnf_probs=dnf_probs)
            optimal = build_budget_team(upcoming_table, race_name, current_prices, budget=100.0)
            limitless = build_budget_team(upcoming_table, race_name, current_prices, budget=999.0)
            optimal_score = optimal["total_score"] if optimal else 0.0
            limitless_score = limitless["total_score"] if limitless else optimal_score
            for team in teams:
                team["chips"] = evaluate_team_chips(
                    [d["Abbreviation"] for d in team["drivers"]],
                    [c["name"] for c in team["constructors"]],
                    pool, optimal_score, limitless_score, race_name,
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    if not teams:
        return {
            "active": True,
            "race_name": race_name,
            "days_until": days_until,
            "message": "Could not build a team within budget for this weekend.",
            "teams": [],
            "team": None,
        }

    return {
        "active": True,
        "race_name": race_name,
        "round": int(upcoming["RoundNumber"]),
        "session_used": session_used,
        "final_session": final_session,
        "days_until": days_until,
        "race_date": race_date.isoformat(),
        "locked": False,
        "provisional": True,
        # true when final practice is already out but the snapshot isn't saved yet
        "awaiting_lock": session_used == final_session,
        "teams": teams,
        "team": teams[0],
    }


@app.get("/last-team")
def get_last_team():
    """
    The team to hold on the Overview when there is no live weekend.

    This is just the newest snapshot. It stays up until the next race gets its own
    snapshot, so it doesn't disappear when the race starts.

    If there are no snapshots at all (a fresh setup) we fall back to rebuilding the
    last race's optimal team from the results, like the old behaviour.
    """
    snap = latest_snapshot(with_key="teams")
    if snap:
        return _team_payload(snap, held=True)

    if fantasy_table is None or not current_prices or not current_prices.get("drivers"):
        return {"active": False, "held": False, "message": "No team available yet."}

    latest_round = int(fantasy_table["RoundNumber"].max())
    race_rows = fantasy_table[fantasy_table["RoundNumber"] == latest_round]
    if race_rows.empty:
        return {"active": False, "held": False, "message": "No completed races yet."}
    race_name = race_rows["RaceName"].iloc[0]

    # attach dnf chances so the held team shows its risk too (display only)
    dnf_probs = _upcoming_dnf_probs(race_rows, race_name)
    teams = build_budget_teams(fantasy_table, race_name, current_prices, budget=100.0,
                               dnf_probs=dnf_probs)
    if not teams:
        return {"active": False, "held": False, "message": "Could not rebuild the last team."}

    return {
        "active": True,
        "held": True,
        "race_name": race_name,
        "round": latest_round,
        "session_used": "RACE",
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






def attach_actual_results(snapshot: dict) -> dict:
    """
    Once the race has actually happened, we put the real finishing positions next to
    what we predicted, so you can see how close we got.

    Results come from race_results_2026.csv, which gets the new race either from the
    Monday GitHub Action or when the backend starts up. Until then results_available
    stays False and the site just says the results are on the way.

    The accuracy numbers only count classified drivers. A DNF has no finishing
    position to compare with, so counting them would just mess up the numbers.
    """
    snapshot = dict(snapshot)
    snapshot["results_available"] = False

    try:
        results = load_dataset("data/processed/race_results_2026.csv")
    except Exception:
        return snapshot

    race = results[results["RaceName"] == snapshot.get("race_name")]
    if race.empty:
        return snapshot

    actual = {r["Abbreviation"]: (r["Position"], r["Status"]) for _, r in race.iterrows()}

    rows, model_err, baseline_err = [], [], []
    for p in snapshot.get("predictions") or []:
        pos, status = actual.get(p["abbreviation"], (None, None))
        classified = status in ("Finished", "Lapped") and pd.notna(pos)
        rows.append({
            **p,
            "actual_pos": int(pos) if classified else None,
            "actual_status": status,
        })
        if classified:
            model_err.append(abs(p["model_pos"] - int(pos)))
            baseline_err.append(abs(p["baseline_pos"] - int(pos)))

    snapshot["predictions"] = rows
    snapshot["results_available"] = True
    if model_err:
        snapshot["accuracy"] = {
            "finishers": len(model_err),
            # average places off per driver, lower is better
            "model_mae": round(sum(model_err) / len(model_err), 2),
            "baseline_mae": round(sum(baseline_err) / len(baseline_err), 2),
        }
    return snapshot




def _held_finishes() -> dict | None:
    """
    Predicted finishes from the newest snapshot that has them, for when there is no
    live weekend to show. Same idea as the held team on the Overview.
    """
    snap = latest_snapshot(with_key="finishes")
    if not snap:
        return None
    return attach_actual_results({
        "active": True,
        "held": True,
        "locked": True,
        "race_name": snap.get("race_name"),
        "round": snap.get("round"),
        "session_used": snap.get("session_used"),
        "locked_at": snap.get("locked_at"),
        "predictions": snap["finishes"],
    })


@app.get("/weekend-finishes")
def get_weekend_finishes():
    """
    Predicted finishing order for the race weekend. For the F1 Predict game mode,
    separate from fantasy team building.

    Returns two orderings side by side:
      - model:    the model's own forecast (blend before shrink-to-grid)
      - baseline: the practice-pace order (the backtest's winning strategy)

    Same rules as /weekend-team: if this weekend has a snapshot we return its saved
    finishes, before that a provisional live version, and between race weekends the
    newest snapshot, with the actual results added once they are published.
    """
    try:
        schedule = _load_schedule()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch schedule: {e}")
    now = _now()

    upcoming = _next_race(schedule, now)
    if upcoming is None:
        return _held_finishes() or {"active": False, "message": "Season complete"}

    race_name = upcoming["EventName"]
    race_date = pd.Timestamp(upcoming["Session5Date"])
    days_until = round((race_date - now).total_seconds() / 86400, 1)

    snap = find_snapshot(race_name)
    if snap and snap.get("finishes"):
        return attach_actual_results({
            "active": True,
            "held": False,
            "locked": True,
            "race_name": race_name,
            "round": snap.get("round"),
            "session_used": snap.get("session_used"),
            "locked_at": snap.get("locked_at"),
            "days_until": days_until,
            "predictions": snap["finishes"],
        })

    if days_until > 5:
        return _held_finishes() or {
            "active": False,
            "race_name": race_name,
            "days_until": days_until,
            "message": f"Next race in {round(days_until)} days",
        }

    final_session = final_practice_session(upcoming)
    sessions_to_try = ["FP1"] if final_session == "FP1" else ["FP3", "FP2", "FP1"]
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
        # this weekend has no practice data yet, so keep showing the last race's
        # predictions (and how they did) instead of an empty page
        return _held_finishes() or {
            "active": True,
            "race_name": race_name,
            "days_until": days_until,
            "message": f"No practice data yet, finishes appear once {final_session} is published",
            "predictions": None,
        }

    try:
        table = predict_upcoming_race(practice_df).copy()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    return {
        "active": True,
        "provisional": True,
        "locked": False,
        "race_name": race_name,
        "session_used": session_used,
        "final_session": final_session,
        "days_until": days_until,
        "predictions": build_finish_predictions(table),
    }


# only one snapshot build at a time, and we remember how the last one went so the
# next call (or you, with curl) can see if something failed
_snapshot_build_lock = threading.Lock()
_last_snapshot_result: dict = {}


def _build_and_save_snapshot(event):
    """Runs in the background after /snapshot/auto has already answered."""
    global _last_snapshot_result
    race_name = event["EventName"]
    rnd = int(event["RoundNumber"])
    try:
        try:
            prices = fetch_prices(rnd)
        except Exception:
            prices = current_prices
        if not prices or not prices.get("drivers"):
            raise RuntimeError("prices not available")

        snap = build_snapshot(event, prices, source="auto")
        try:
            save_snapshot(snap)
        except FileExistsError:
            pass  # another build got there first, that's fine
        try:
            github = commit_to_github(snap)
        except Exception as e:
            github = {"committed": False, "reason": str(e)}

        _last_snapshot_result = {
            "status": "locked",
            "race_name": race_name,
            "round": rnd,
            "session_used": snap["session_used"],
            "at": _now().isoformat(),
            "built_after_quali_start": snap.get("built_after_quali_start"),
            "team_1": [d["Abbreviation"] for d in snap["teams"][0]["drivers"]],
            "github": github,
        }
        print(f"Snapshot locked: {race_name} round {rnd}, github: {github}")
    except Exception as e:
        # the session IS published (we checked first), so this is a real failure
        _last_snapshot_result = {
            "status": "error",
            "race_name": race_name,
            "at": _now().isoformat(),
            "detail": str(e),
        }
        print(f"Snapshot build failed for {race_name}: {e}")
    finally:
        _snapshot_build_lock.release()


@app.post("/snapshot/auto")
def auto_snapshot(
    background_tasks: BackgroundTasks,
    x_snapshot_secret: str | None = Header(default=None),
    dry_run: bool = False,
):
    """
    Locks the current race weekend into a snapshot, all by itself.

    cron-job.org calls this every 10 minutes on Fridays and Saturdays. Each call
    basically checks: is a race weekend live, is its final practice over and
    published, and does it still not have a snapshot? If yes, it builds one in the
    background, saves it here so the site uses it straight away, and commits it to
    GitHub so it survives restarts and redeploys.

    It answers straight away and builds in the background, because building takes
    longer than cron-job.org is willing to wait for a reply.

    Calling it a lot is fine, it does nothing once the snapshot exists. It needs the
    X-Snapshot-Secret header to match SNAPSHOT_SECRET so random people can't trigger
    builds. dry_run=true builds everything and shows you the result, but saves and
    commits nothing, which is handy for checking the setup works.
    """
    secret = os.getenv("SNAPSHOT_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="SNAPSHOT_SECRET is not set on the server")
    if not x_snapshot_secret or not hmac.compare_digest(x_snapshot_secret, secret):
        raise HTTPException(status_code=401, detail="Wrong or missing X-Snapshot-Secret header")

    try:
        schedule = _load_schedule()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch schedule: {e}")
    now = _now()
    last = _last_snapshot_result or None

    upcoming = _next_race(schedule, now)
    if upcoming is None:
        return {"status": "idle", "reason": "season complete", "last_result": last}

    race_name = upcoming["EventName"]
    rnd = int(upcoming["RoundNumber"])
    days_until = (pd.Timestamp(upcoming["Session5Date"]) - now).total_seconds() / 86400
    if days_until > 5:
        return {
            "status": "idle",
            "reason": f"no live weekend, {race_name} is in {round(days_until)} days",
            "last_result": last,
        }

    existing = find_snapshot(race_name)
    if existing:
        # already locked. we still make sure it reached GitHub, in case the commit
        # failed last time (otherwise a restart would lose it)
        try:
            github = commit_to_github(existing, dry_run=dry_run)
        except Exception as e:
            github = {"committed": False, "reason": str(e)}
        return {
            "status": "already_locked",
            "race_name": race_name,
            "locked_at": existing.get("locked_at"),
            "github": github,
        }

    if results_already_in_data(race_name):
        return {
            "status": "refused",
            "reason": f"{race_name} results are already in the data, a snapshot now would have seen the answers",
        }

    session = final_practice_session(upcoming)
    if not session_finished(upcoming, session, now):
        return {"status": "waiting", "reason": f"{session} for {race_name} hasn't finished yet", "last_result": last}
    try:
        published = session_published(race_name, session)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not check whether {session} is published: {e}")
    if not published:
        return {"status": "waiting", "reason": f"{session} for {race_name} isn't published yet", "last_result": last}

    if dry_run:
        # build right here so you can see the result in the reply. nothing is saved
        try:
            prices = fetch_prices(rnd)
        except Exception:
            prices = current_prices
        try:
            snap = build_snapshot(upcoming, prices, source="auto")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{session} is published but building failed: {e}")
        return {
            "status": "dry_run",
            "race_name": race_name,
            "round": rnd,
            "session_used": session,
            "built_after_quali_start": snap.get("built_after_quali_start"),
            "teams": [
                {
                    "drivers": [d["Abbreviation"] for d in t["drivers"]],
                    "constructors": [c["name"] for c in t["constructors"]],
                    "score": t["total_score"],
                }
                for t in snap["teams"]
            ],
            "finishes_top_5": [f["abbreviation"] for f in snap["finishes"][:5]],
            "github": commit_to_github(snap, dry_run=True),
        }

    if not _snapshot_build_lock.acquire(blocking=False):
        return {"status": "building", "race_name": race_name, "reason": "a build is already running"}
    background_tasks.add_task(_build_and_save_snapshot, upcoming)
    return {
        "status": "started",
        "race_name": race_name,
        "round": rnd,
        "session_used": session,
        "last_result": last,
    }
