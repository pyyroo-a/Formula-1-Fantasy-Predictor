"""
The live race weekend team: the locked snapshot (or a provisional preview before
it's locked) and the held team between races. Predicted finishes are in
finishes.py and the auto lock in weekend_lock.py. How snapshots work is in
Fantasy Predictor/Snapshots.md.
"""
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.api import clock, state
from src.api.weekend_common import load_schedule, next_race, weekend_grid
from src.api.weekend_lock import should_self_lock, start_snapshot_build  # noqa: F401 (tests import should_self_lock from here)
from src.fantasy import build_budget_team, build_budget_teams, get_race_pool
from src.pipeline import predict_upcoming_race
from src.snapshots import find_snapshot, latest_snapshot
from src.confidence import attach_to_teams
from src.weekend import (
    evaluate_team_chips,
    final_practice_session,
    upcoming_dnf_probs,
    weekend_confidence_for,
)

router = APIRouter()


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


@router.get("/weekend-team")
def get_weekend_team(background_tasks: BackgroundTasks):
    """
    The team for the current race weekend.

    If this weekend already has a snapshot we just return it. It never gets rebuilt,
    so restarts, the race starting or opening the site again can't change it.

    Before the snapshot exists (final practice not published and saved yet) we work
    out a live preview and mark it provisional. Nothing is saved from here. Saving
    only happens in POST /snapshot/auto or scripts/lock_team.py.
    """
    try:
        schedule = load_schedule()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch schedule: {e}")
    now = clock.now()

    upcoming = next_race(schedule, now)
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

    if not state.current_prices or not state.current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    final_session = final_practice_session(upcoming)
    practice_df, session_used = weekend_grid(race_name, final_session)

    if practice_df is None:
        # no practice yet, so we say the weekend isn't live. the site then keeps
        # showing the last snapshot as a held team instead of an empty box
        return {
            "active": False,
            "race_name": race_name,
            "days_until": days_until,
            "message": f"No practice data yet, the team locks once {final_session} is published",
        }

    # the session we lock on is out, so save this weekend instead of recomputing it
    # forever and losing it when the race starts. see should_self_lock
    if should_self_lock(race_name, session_used, final_session):
        start_snapshot_build(upcoming, background_tasks)

    try:
        upcoming_table = predict_upcoming_race(practice_df)
        dnf_probs = upcoming_dnf_probs(upcoming_table, race_name)
        teams = build_budget_teams(upcoming_table, race_name, state.current_prices,
                                   budget=100.0, dnf_probs=dnf_probs)
        if teams:
            pool = get_race_pool(upcoming_table, race_name, state.current_prices, dnf_probs=dnf_probs)
            optimal = build_budget_team(upcoming_table, race_name, state.current_prices, budget=100.0)
            limitless = build_budget_team(upcoming_table, race_name, state.current_prices, budget=999.0)
            optimal_score = optimal["total_score"] if optimal else 0.0
            limitless_score = limitless["total_score"] if limitless else optimal_score
            for team in teams:
                team["chips"] = evaluate_team_chips(
                    [d["Abbreviation"] for d in team["drivers"]],
                    [c["name"] for c in team["constructors"]],
                    pool, optimal_score, limitless_score, race_name,
                )
            # after the teams are built so it can't change a pick, None before the lock session
            teams = attach_to_teams(teams, weekend_confidence_for(race_name, session_used, final_session))
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


@router.get("/last-team")
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

    if state.fantasy_table is None or not state.current_prices or not state.current_prices.get("drivers"):
        return {"active": False, "held": False, "message": "No team available yet."}

    latest_round = int(state.fantasy_table["RoundNumber"].max())
    race_rows = state.fantasy_table[state.fantasy_table["RoundNumber"] == latest_round]
    if race_rows.empty:
        return {"active": False, "held": False, "message": "No completed races yet."}
    race_name = race_rows["RaceName"].iloc[0]

    # attach dnf chances so the held team shows its risk too (display only)
    dnf_probs = upcoming_dnf_probs(race_rows, race_name)
    teams = build_budget_teams(state.fantasy_table, race_name, state.current_prices, budget=100.0,
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
