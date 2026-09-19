"""
Race data endpoints: the calendar, sessions, and results for races that already happened.
"""
import fastf1
import pandas as pd
from fastapi import APIRouter, HTTPException

from src.api import clock, state
from src.api.schemas import PracticeRequest, RaceRequest
from src.config import SEASON, results_path
from src.data_loader import load_dataset
from src.fetch_practice import is_sprint_weekend

router = APIRouter()


@router.get("/races")
def get_races():
    return sorted(state.fantasy_table["RaceName"].unique().tolist())


@router.get("/upcoming-races")
def get_upcoming_races():
    completed = set(state.fantasy_table["RaceName"].unique())

    if state.race_schedule is not None:
        now = clock.now()
        result = []
        for _, event in state.race_schedule.sort_values("RoundNumber").iterrows():
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


@router.post("/race-sessions")
def get_race_sessions(request: RaceRequest):
    """Returns session times for a given race so the frontend can show availability."""
    if state.race_schedule is None:
        raise HTTPException(status_code=503, detail="Schedule not available")

    now = clock.now()
    event = state.race_schedule[state.race_schedule["EventName"] == request.race_name]
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


@router.get("/next-race")
def get_next_race():
    try:
        fastf1.Cache.enable_cache("data/cache")
        schedule = fastf1.get_event_schedule(SEASON, include_testing=False)
        now = clock.now()

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


@router.post("/race-results")
def get_race_results(request: RaceRequest):
    try:
        df = load_dataset(results_path())
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


@router.post("/qualifying-results")
def get_qualifying_results(request: RaceRequest):
    try:
        df = load_dataset(results_path())
        race_data = df[df["RaceName"] == request.race_name]
        if race_data.empty:
            raise HTTPException(status_code=404, detail=f"Race not found in {SEASON} data")
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


@router.post("/practice-results")
def get_practice_results(request: PracticeRequest):
    """
    Returns the fastest-lap classification for a practice session, plus the list
    of practice sessions that actually exist for the weekend. Sprint weekends run
    only FP1, so the available sessions are read from the real schedule rather
    than assumed — this works for past sprints too, which the hardcoded sprint
    list doesn't cover.
    """
    try:
        df = load_dataset(results_path())
        race_data = df[df["RaceName"] == request.race_name]
        year = int(race_data["Year"].iloc[0]) if not race_data.empty else SEASON
    except Exception:
        year = SEASON

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
