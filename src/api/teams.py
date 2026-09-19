"""
Team building endpoints: predictions, budget teams, driver pools and chip advice.
"""
from fastapi import APIRouter, HTTPException

from src.api import state
from src.api.schemas import BudgetRequest, ChipAdvisorRequest, RaceRequest, UpcomingRaceRequest
from src.config import SEASON
from src.fantasy import (
    build_budget_team,
    build_budget_teams,
    build_fantasy_team,
    generate_explanations,
    get_race_pool,
)
from src.fetch_practice import fallback_sessions, first_available_practice, get_practice_grid
from src.pipeline import predict_upcoming_race
from src.weekend import evaluate_team_chips, upcoming_dnf_probs

router = APIRouter()


@router.post("/predict")
def get_fantasy_team(request: RaceRequest):
    team = build_fantasy_team(state.fantasy_table, request.race_name)
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


@router.post("/predict-upcoming")
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


@router.post("/predict-budget")
def get_budget_team(request: BudgetRequest):
    if not state.current_prices or not state.current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    teams = build_budget_teams(
        state.fantasy_table,
        request.race_name,
        state.current_prices,
        budget=request.budget,
    )

    if not teams:
        raise HTTPException(
            status_code=400,
            detail="No valid team found within budget. Try increasing the budget."
        )

    return {"teams": teams}


@router.post("/race-pool")
def get_race_pool_endpoint(request: RaceRequest):
    if not state.current_prices or not state.current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    result = get_race_pool(state.fantasy_table, request.race_name, state.current_prices)

    if not result["drivers"]:
        raise HTTPException(status_code=400, detail="No priced drivers found for that race.")

    return result


@router.post("/upcoming-race-pool")
def get_upcoming_race_pool(request: UpcomingRaceRequest):
    if not state.current_prices or not state.current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    # try the requested session first, then work backwards
    practice_df, session_used, last_error = first_available_practice(
        request.year, request.race_name, fallback_sessions(request.session))

    if practice_df is None:
        raise HTTPException(status_code=400, detail=f"No practice data available yet. {last_error}")

    upcoming_table = predict_upcoming_race(practice_df)

    pool = get_race_pool(upcoming_table, request.race_name, state.current_prices,
                         dnf_probs=upcoming_dnf_probs(upcoming_table, request.race_name))
    if not pool["drivers"]:
        raise HTTPException(status_code=400, detail="No priced drivers found for that race.")

    optimal = build_budget_team(upcoming_table, request.race_name, state.current_prices, budget=100.0)

    return {"pool": pool, "optimal": optimal, "session_used": session_used}


@router.post("/chip-advisor")
def get_chip_advisor(request: ChipAdvisorRequest):
    if not state.current_prices or not state.current_prices.get("drivers"):
        raise HTTPException(status_code=503, detail="Prices not available")

    practice_df, session_used, last_error = first_available_practice(
        SEASON, request.race_name, fallback_sessions("FP3"))

    if practice_df is None:
        raise HTTPException(status_code=400, detail=f"No practice data available yet. {last_error}")

    upcoming_table = predict_upcoming_race(practice_df)
    pool = get_race_pool(upcoming_table, request.race_name, state.current_prices,
                         dnf_probs=upcoming_dnf_probs(upcoming_table, request.race_name))

    if not pool["drivers"]:
        raise HTTPException(status_code=400, detail="No priced drivers found for this race.")

    optimal = build_budget_team(upcoming_table, request.race_name, state.current_prices, budget=100.0)
    limitless = build_budget_team(upcoming_table, request.race_name, state.current_prices, budget=999.0)

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
