"""
The transfer planner (project 3): POST /transfer-ladder.

Your team in, the ladder out: keep, then the best team with each number of free
transfers, the facts, and why each swap. The maths is in src/planner.py.

The forecast gets worked out live from the practice grid, the same way the Manual Team
page does it, because a locked snapshot only keeps the 3 teams and the finishing order,
not every driver. Once the weekend is locked we use the session it locked on.
"""
from fastapi import APIRouter, HTTPException

from src.api import state
from src.api.schemas import TransferLadderRequest
from src.api.weekend_common import weekend_grid
from src.fantasy import get_race_pool
from src.fetch_practice import is_sprint_weekend
from src.pipeline import predict_upcoming_race
from src.planner import transfer_ladder
from src.snapshots import find_snapshot
from src.confidence import attach_confidence
from src.weekend import upcoming_dnf_probs, weekend_confidence_for

router = APIRouter()


@router.post("/transfer-ladder")
def get_transfer_ladder(request: TransferLadderRequest):
    if not state.current_prices or not state.current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    snap = find_snapshot(request.race_name)
    lock_session = snap.get("session_used") if snap else None
    wanted = lock_session or ("SQ" if is_sprint_weekend(request.race_name) else "FP3")
    practice_df, session_used = weekend_grid(request.race_name, wanted)
    if practice_df is None:
        raise HTTPException(status_code=400, detail="No practice data yet for this race, the ladder needs at least FP1.")

    table = predict_upcoming_race(practice_df)
    pool = get_race_pool(table, request.race_name, state.current_prices,
                         dnf_probs=upcoming_dnf_probs(table, request.race_name))
    # so each swap can say how sure we are about the driver coming in
    pool["drivers"] = attach_confidence(pool["drivers"],
                                        weekend_confidence_for(request.race_name, session_used, wanted))
    ladder = transfer_ladder({"drivers": request.drivers, "constructors": request.constructors},
                             pool, state.current_prices, request.budget, request.free_transfers,
                             session=session_used)
    return {
        "race_name": request.race_name,
        "session_used": session_used,
        # locked = the session the weekend locked on, anything else is a preview
        "provisional": lock_session is None or session_used != lock_session,
        **ladder,
    }
