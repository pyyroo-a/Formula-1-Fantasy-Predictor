"""
Locking a race weekend: POST /snapshot/auto (the GitHub Action calls it), plus the
self lock the page views use, so both go through the same build. How snapshots work
is in Fantasy Predictor/Snapshots.md.
"""
import hmac
import os
import threading

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from src.api import clock, state
from src.api.weekend_common import load_schedule, next_race
from src.fetch_prices import fetch_prices
from src.snapshots import commit_to_github, find_snapshot, save_snapshot
from src.weekend import (
    build_snapshot,
    final_practice_session,
    results_already_in_data,
    session_finished,
    session_published,
)

router = APIRouter()

# only one snapshot build at a time, and we remember how the last one went so the
# next call (or you, with curl) can see if something failed
_snapshot_build_lock = threading.Lock()

_last_snapshot_result: dict = {}


def should_self_lock(race_name: str, session_used: str | None, final_session: str) -> bool:
    """
    Whether a provisional view should save itself as this weekend's snapshot.

    Why this exists: the provisional prediction was worked out fresh on every
    request and never written down, so it only became permanent if something else
    saved a snapshot. When the scheduler missed (Bahrain round 16, Singapore round
    17) the weekend disappeared the moment the race started, because the "upcoming
    race" moved on and the site fell back to the newest snapshot it still had,
    which was an older race. Hence the predictions that "kept changing".

    So once a provisional is built from the session we lock on, it saves itself and
    stops being provisional. Guards, which are the same ones POST /snapshot/auto
    uses, so a page view can never save something the scheduler would refuse:

      * only the FINAL session counts. An earlier session standing in (FP1 while
        sprint quali isn't out) measured worse, so freezing that would make the
        saved answer worse than waiting a few hours for the real one.
      * never if this weekend already has a snapshot. A locked weekend never changes.
      * never once the results are in our data, or the "prediction" saw the answers.

    LOCK_ON_VIEW=0 switches it off without a redeploy.
    """
    if os.getenv("LOCK_ON_VIEW", "1") != "1":
        return False
    if not session_used or session_used != final_session:
        return False
    if find_snapshot(race_name):
        return False
    if results_already_in_data(race_name):
        return False
    return True


def start_snapshot_build(event, background_tasks: BackgroundTasks) -> bool:
    """
    Kicks off the real snapshot build in the background, the same one /snapshot/auto
    runs, so there is only one way a snapshot ever gets made. Returns False if a
    build is already running, in which case we just leave it to finish.
    """
    if not _snapshot_build_lock.acquire(blocking=False):
        return False
    background_tasks.add_task(_build_and_save_snapshot, event)
    return True


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

    The GitHub Action (.github/workflows/lock-snapshot.yml) calls this every 30
    minutes over the race weekend. Each call
    basically checks: is a race weekend live, is its final practice over and
    published, and does it still not have a snapshot? If yes, it builds one in the
    background, saves it here so the site uses it straight away, and commits it to
    GitHub so it survives restarts and redeploys.

    It answers straight away and builds in the background, because building takes
    longer than the Action is willing to wait for a reply.

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
        schedule = load_schedule()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch schedule: {e}")
    now = clock.now()
    last = _last_snapshot_result or None

    upcoming = next_race(schedule, now)
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
