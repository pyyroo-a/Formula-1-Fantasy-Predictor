"""
Local tools, hidden in production.
"""
import os
from fastapi import APIRouter, HTTPException
from src.backtest import run_backtest
from src.api import state

router = APIRouter()


@router.get("/backtest")
def get_backtest(refresh: bool = False):
    """
    Replays completed 2026 races with the model trained only on prior races,
    and compares its picks against a grid-order baseline.

    Local analysis tool — disabled unless BACKTEST_ENABLED=true. It retrains the
    model once per race (~1-2 min of CPU), so leaving it open in production would
    let anyone stall the backend. Result is cached in memory after the first run.
    """
    if os.getenv("BACKTEST_ENABLED", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=404, detail="Not found")

    if state.backtest_cache is None or refresh:
        try:
            state.backtest_cache = run_backtest(fallback_prices=state.current_prices)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Backtest failed: {e}")

    return state.backtest_cache
