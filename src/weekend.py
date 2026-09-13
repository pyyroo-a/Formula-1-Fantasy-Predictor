"""
Everything we need to work out one race weekend: the three teams, the chip advice,
each driver's dnf chance and the predicted finishing order.

This used to be spread around main.py. We moved it here because three different
things need the exact same steps:
  - the backend, for the provisional preview before a weekend is locked
  - POST /snapshot/auto, which saves the locked snapshot by itself
  - scripts/lock_team.py, the backup you can run on your laptop

If each one had its own copy they would slowly drift apart, and the saved snapshot
wouldn't match what the site showed. So they all go through build_snapshot() here.
"""

import pandas as pd
import requests
import fastf1

from src.pipeline import predict_upcoming_race
from src.fantasy import build_budget_team, build_budget_teams, get_race_pool
from src.fetch_practice import get_practice_grid
from src.dnf import DNFModel, USE_DNF_RISK
from src.data_loader import load_dataset

YEAR = 2026

# tracks where lots of cars retire, used by the no negative chip advice
HIGH_ATTRITION_CIRCUITS = {
    "Azerbaijan Grand Prix", "Singapore Grand Prix", "Monaco Grand Prix",
    "Las Vegas Grand Prix", "Saudi Arabian Grand Prix", "Miami Grand Prix",
}

# how FastF1's schedule names each session
SESSION_NAMES = {"FP1": "Practice 1", "FP2": "Practice 2", "FP3": "Practice 3", "Q": "Qualifying"}

# practice sessions are an hour long. we never treat one as over before that, so we
# can't lock on half a session even if some timing data already shows up
PRACTICE_LENGTH = pd.Timedelta(minutes=60)


def final_practice_session(event) -> str:
    """
    The last practice session before the fantasy deadline, so the one we lock on.

    Sprint weekends only have FP1, normal weekends go up to FP3. We read it from
    FastF1's EventFormat instead of a hardcoded list of sprint races (that list in
    src/fetch_practice.py is out of date).
    """
    fmt = str(event.get("EventFormat", "conventional")).lower()
    return "FP1" if "sprint" in fmt else "FP3"


def session_start_utc(event, session: str):
    """When a session starts in UTC, e.g. session_start_utc(event, "FP3"). None if not found."""
    name = SESSION_NAMES.get(session, session)
    for i in range(1, 6):
        if str(event.get(f"Session{i}", "")) == name:
            t = event.get(f"Session{i}DateUtc")
            if pd.isna(t):
                return None
            t = pd.Timestamp(t)
            return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return None


def session_finished(event, session: str, now) -> bool:
    """True once the session's scheduled hour is over."""
    start = session_start_utc(event, session)
    return start is not None and now >= start + PRACTICE_LENGTH


def session_published(race_name: str, session: str, year: int = YEAR) -> bool:
    """
    Asks F1's timing server directly whether a session's lap data is out yet.

    We check this BEFORE trying to build. That way "not published yet" (normal, just
    try again in 10 minutes) and "published but loading it failed" (an actual problem)
    can never get mixed up. That mix up is what hid the failed locks at Madring: every
    run said "not available yet" even though the data had been out for hours.
    """
    ses = fastf1.get_session(year, race_name, session)
    url = f"https://livetiming.formula1.com{ses.api_path}TimingData.jsonStream"
    r = requests.head(url, timeout=15, allow_redirects=True)
    return r.status_code == 200


def results_already_in_data(race_name: str, year: int = YEAR) -> bool:
    """
    True if this race's results are already in our history.

    If they are, a "prediction" built now would basically train on the answers, so
    anything that saves a snapshot refuses to go ahead.
    """
    try:
        df = load_dataset(f"data/processed/race_results_{year}.csv")
    except Exception:
        return False
    return bool(((df["RaceName"] == race_name) & (df["Year"] == year)).any())


def upcoming_dnf_probs(upcoming_table, race_name):
    """
    Chance of not finishing for each driver in a race that hasn't happened yet.

    We fit the dnf model fresh from all the results each time. It's cheap (a few
    groupbys over ~800 rows) and it means the numbers keep up with the season.

    Returns None if the model is switched off or anything goes wrong. None is the old
    behaviour where everyone is assumed to finish, so the team builder never breaks
    just because the risk model couldn't be fitted.
    """
    if not USE_DNF_RISK:
        return None
    try:
        history = pd.concat(
            [load_dataset(f"data/processed/race_results_{y}.csv") for y in (2025, 2026)],
            ignore_index=True,
        )
        model = DNFModel.fit(history)
        probs = model.predict(
            upcoming_table["Abbreviation"], upcoming_table["GridPosition"], race_name
        )
        return dict(zip(upcoming_table["Abbreviation"], probs))
    except Exception:
        return None


def build_finish_predictions(table: pd.DataFrame) -> list[dict]:
    """
    Turns a prediction table into the predicted finishing order we show on the site.

    We rank the model's own forecast (ModelPredicted, before it gets shrunk onto the
    grid) and put the practice order next to it, which is basically the GridPosition
    estimate.
    """
    t = table.copy()
    t["ModelRank"] = t["ModelPredicted"].rank(method="first").astype(int)

    predictions = []
    for _, r in t.sort_values("ModelRank").iterrows():
        baseline_pos = int(round(r["GridPosition"]))
        model_pos = int(r["ModelRank"])
        predictions.append({
            "abbreviation": r["Abbreviation"],
            "team": r["TeamName"],
            "model_pos": model_pos,
            "baseline_pos": baseline_pos,
            # positive = model thinks they finish higher than practice order says
            "delta": baseline_pos - model_pos,
        })
    return predictions


def _grade(gain, thresholds):
    play, consider = thresholds
    if gain >= play:
        return "PLAY"
    if gain >= consider:
        return "CONSIDER"
    return "HOLD"


def evaluate_team_chips(
    my_drivers: list[str],
    my_constructors: list[str],
    pool: dict,
    optimal_score: float,
    limitless_score: float,
    race_name: str,
) -> dict:
    """
    Grades all 6 chips for a single team (a list of driver abbreviations +
    constructor names). `optimal_score` / `limitless_score` are the best legal
    team and the best uncapped team for this weekend. They don't depend on the
    team being graded, so the caller works them out once and reuses them across
    every generated team.
    """
    driver_map = {d["Abbreviation"]: d for d in pool["drivers"]}
    constructor_map = {c["name"]: c for c in pool["constructors"]}

    my_driver_score = sum(driver_map.get(a, {}).get("FantasyValue", 0) for a in my_drivers)
    my_constructor_score = sum(constructor_map.get(n, {}).get("score", 0) for n in my_constructors)
    my_team_score = my_driver_score + my_constructor_score

    wildcard_gain = max(0.0, round(optimal_score - my_team_score, 1))
    limitless_gain = max(0.0, round(limitless_score - my_team_score, 1))

    # 3x Boost applies to a driver you already own, so the target is the best
    # driver *in this team*, not the best in the whole field.
    my_drivers_in_pool = [driver_map[a] for a in my_drivers if a in driver_map]
    boost_target = max(my_drivers_in_pool, key=lambda d: d["FantasyValue"]) if my_drivers_in_pool else None
    boost_gain = round(boost_target["FantasyValue"], 1) if boost_target else 0.0

    riskiest = min(my_drivers_in_pool, key=lambda d: d["FantasyValue"]) if my_drivers_in_pool else None

    is_high_attrition = race_name in HIGH_ATTRITION_CIRCUITS
    dnf_risk_pct = 120 if is_high_attrition else 65

    return {
        "my_team_score": round(my_team_score, 2),
        "limitless": {
            "gain": limitless_gain,
            "recommendation": _grade(limitless_gain, (40, 20)),
        },
        "wildcard": {
            "gain": wildcard_gain,
            "recommendation": _grade(wildcard_gain, (25, 12)),
        },
        "x3_boost": {
            "gain": boost_gain,
            "target": boost_target["Abbreviation"] if boost_target else None,
            "recommendation": _grade(boost_gain, (30, 15)),
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
    }


def build_snapshot(event, prices: dict, source: str = "auto", note: str | None = None,
                   year: int = YEAR) -> dict:
    """
    Builds the full snapshot for one race weekend from its final practice session.

    Nothing gets saved here, it just returns the dict. Saving lives in
    src/snapshots.py, so building and storing stay separate and easy to test.
    """
    race_name = event["EventName"]
    rnd = int(event["RoundNumber"])
    session = final_practice_session(event)

    practice = get_practice_grid(year, race_name, session)
    table = predict_upcoming_race(practice)
    dnf_probs = upcoming_dnf_probs(table, race_name)

    teams = build_budget_teams(table, race_name, prices, budget=100.0, dnf_probs=dnf_probs)
    if not teams:
        raise ValueError(f"could not build a team within budget for {race_name}")

    # chip advice for each team. the optimal and limitless reference teams are the
    # same for all three, so we work them out once
    pool = get_race_pool(table, race_name, prices, dnf_probs=dnf_probs)
    optimal = build_budget_team(table, race_name, prices, budget=100.0)
    limitless = build_budget_team(table, race_name, prices, budget=999.0)
    optimal_score = optimal["total_score"] if optimal else 0.0
    limitless_score = limitless["total_score"] if limitless else optimal_score
    for team in teams:
        team["chips"] = evaluate_team_chips(
            [d["Abbreviation"] for d in team["drivers"]],
            [c["name"] for c in team["constructors"]],
            pool, optimal_score, limitless_score, race_name,
        )

    now = pd.Timestamp.now(tz="UTC")
    quali = session_start_utc(event, "Q")
    snap = {
        "year": year,
        "race_name": race_name,
        "round": rnd,
        "session_used": session,
        "locked_at": now.isoformat(),
        "source": source,
        # the fantasy deadline is qualifying, so we note if this was built too late for it
        "built_after_quali_start": bool(quali is not None and now > quali),
        "teams": teams,
        "finishes": build_finish_predictions(table),
    }
    if note:
        snap["note"] = note
    return snap
