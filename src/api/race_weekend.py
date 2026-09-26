"""
The live race weekend: the locked snapshot (or a provisional preview before
it's locked), the held team between races, predicted finishes, and
POST /snapshot/auto which locks a weekend by itself. See docs/SNAPSHOTS.md.
"""
import hmac
import os
import threading

import fastf1
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from src.api import clock, state
from src.config import SEASON, results_path
from src.data_loader import load_dataset
from src.fantasy import build_budget_team, build_budget_teams, get_race_pool
from src.fetch_practice import fallback_sessions, first_available_practice
from src.fetch_prices import fetch_prices
from src.pipeline import predict_upcoming_race
from src.snapshots import commit_to_github, find_snapshot, latest_snapshot, save_snapshot
from src.weekend import (
    build_finish_predictions,
    load_grid,
    build_snapshot,
    evaluate_team_chips,
    final_practice_session,
    results_already_in_data,
    session_finished,
    session_published,
    upcoming_dnf_probs,
)

router = APIRouter()


def _load_schedule():
    fastf1.Cache.enable_cache("data/cache")
    return fastf1.get_event_schedule(SEASON, include_testing=False)


def _next_race(schedule, now):
    """The next race that hasn't started yet, or None once the season is over."""
    for _, event in schedule.sort_values("RoundNumber").iterrows():
        race_date = event["Session5Date"]
        if pd.isna(race_date):
            continue
        if pd.Timestamp(race_date) > now:
            return event
    return None


def _weekend_grid(race_name: str, final_session: str):
    """
    Best order available right now for the live preview.

    Sprint weekend: sprint qualifying, because the deadline is the sprint race so
    that session has already run. Normal weekend: FP3, working back to FP1.
    Returns (df, session_used), or (None, None) if nothing has been published.
    """
    if final_session == "SQ":
        try:
            return load_grid(race_name, "SQ"), "SQ"
        except Exception:
            # sprint quali not out yet, FP1 is better than nothing
            df, used, _ = first_available_practice(SEASON, race_name, ["FP1"])
            return df, used
    df, used, _ = first_available_practice(SEASON, race_name, fallback_sessions(final_session))
    return df, used


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
    now = clock.now()

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

    if not state.current_prices or not state.current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    final_session = final_practice_session(upcoming)
    practice_df, session_used = _weekend_grid(race_name, final_session)

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
    now = clock.now()

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
    practice_df, session_used = _weekend_grid(race_name, final_session)

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
            prices = state.current_prices
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
            "at": clock.now().isoformat(),
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
            "at": clock.now().isoformat(),
            "detail": str(e),
        }
        print(f"Snapshot build failed for {race_name}: {e}")
    finally:
        _snapshot_build_lock.release()


@router.post("/snapshot/auto")
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
    now = clock.now()
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
            prices = state.current_prices
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
