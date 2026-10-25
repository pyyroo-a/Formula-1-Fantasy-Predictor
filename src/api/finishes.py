"""
GET /weekend-finishes: the predicted finishing order for the race weekend, and how
it did once the results are in. Same snapshot rules as the weekend team.
"""
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.api import clock
from src.api.weekend_common import load_schedule, next_race, weekend_grid
from src.api.weekend_lock import should_self_lock, start_snapshot_build
from src.config import results_path
from src.data_loader import load_dataset
from src.pipeline import predict_upcoming_race
from src.snapshots import find_snapshot, latest_snapshot
from src.weekend import build_finish_predictions, final_practice_session

router = APIRouter()


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
        results = load_dataset(results_path())
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


@router.get("/weekend-finishes")
def get_weekend_finishes(background_tasks: BackgroundTasks):
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
        schedule = load_schedule()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch schedule: {e}")
    now = clock.now()

    upcoming = next_race(schedule, now)
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
    practice_df, session_used = weekend_grid(race_name, final_session)

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

    if should_self_lock(race_name, session_used, final_session):
        start_snapshot_build(upcoming, background_tasks)

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
