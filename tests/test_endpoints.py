"""
Every endpoint, checked against what it returned before the clean up.

If one of these fails after moving code around, the refactor changed an answer
somewhere, which is exactly what we're trying to catch.
"""
import pytest

import src.api.weekend_lock as weekend_lock
from conftest import (
    BAKU_THURSDAY,
    SAT_MADRING_BEFORE_QUALI,
    SAT_MADRING_FP3_RUNNING,
    SUN_MADRING_AFTER_RACE,
)

MADRING = "Spanish Grand Prix"
MONZA = "Italian Grand Prix"

# the weekend tests only ever see these two, so a new race landing in the repo
# can't change what they're testing
UP_TO_MADRING = ("2026_R13_italian_grand_prix.json", "2026_R14_spanish_grand_prix.json")

# the Madring snapshot's team 1, so the chip advisor has a real team to grade
MADRING_TEAM_DRIVERS = ["ANT", "LAW", "HUL", "BOR", "BEA"]
MADRING_TEAM_CONSTRUCTORS = ["McLaren", "Audi"]


# ---- race data -----------------------------------------------------------------

def test_races(client, golden):
    golden("races", client.get("/races"))


def test_upcoming_races(client, golden, at):
    at(SUN_MADRING_AFTER_RACE)
    golden("upcoming_races", client.get("/upcoming-races"))


def test_next_race(client, golden, at):
    at(SUN_MADRING_AFTER_RACE)
    golden("next_race", client.get("/next-race"))


def test_race_sessions(client, golden, at):
    at(SAT_MADRING_BEFORE_QUALI)
    golden("race_sessions", client.post("/race-sessions", json={"race_name": MADRING}))


def test_race_results(client, golden):
    golden("race_results_monza", client.post("/race-results", json={"race_name": MONZA}))


def test_qualifying_results(client, golden):
    golden("qualifying_results_monza", client.post("/qualifying-results", json={"race_name": MONZA}))


@pytest.mark.parametrize("session", ["", "FP2"])
def test_practice_results(client, golden, session):
    golden(f"practice_results_madring_{session or 'auto'}",
           client.post("/practice-results", json={"race_name": MADRING, "session": session}))


# ---- prices --------------------------------------------------------------------

def test_prices(client, golden):
    golden("prices", client.get("/prices"))


def test_price_changes(client, golden):
    golden("price_changes", client.get("/price-changes"))


# ---- teams and chips -----------------------------------------------------------

def test_predict(client, golden):
    golden("predict_monza", client.post("/predict", json={"race_name": MONZA}))


def test_predict_upcoming(client, golden):
    golden("predict_upcoming_madring",
           client.post("/predict-upcoming", json={"race_name": MADRING, "year": 2026, "session": "FP3"}))


def test_predict_budget(client, golden):
    golden("predict_budget_monza", client.post("/predict-budget", json={"race_name": MONZA, "budget": 100.0}))


def test_race_pool(client, golden):
    golden("race_pool_monza", client.post("/race-pool", json={"race_name": MONZA}))


def test_upcoming_race_pool(client, golden):
    golden("upcoming_race_pool_madring",
           client.post("/upcoming-race-pool", json={"race_name": MADRING, "year": 2026, "session": "FP3"}))


def test_chip_advisor(client, golden):
    golden("chip_advisor_madring", client.post("/chip-advisor", json={
        "race_name": MADRING,
        "my_drivers": MADRING_TEAM_DRIVERS,
        "my_constructors": MADRING_TEAM_CONSTRUCTORS,
    }))


# ---- race weekend (snapshots) --------------------------------------------------

def test_weekend_team_locked(client, golden, at, snapshots):
    snapshots(*UP_TO_MADRING)
    at(SAT_MADRING_BEFORE_QUALI)
    golden("weekend_team_locked", client.get("/weekend-team"))


def test_weekend_team_provisional(client, golden, at, empty_snapshots):
    at(SAT_MADRING_BEFORE_QUALI)
    golden("weekend_team_provisional", client.get("/weekend-team"))


def test_weekend_team_after_race(client, golden, at, snapshots):
    snapshots(*UP_TO_MADRING)
    at(SUN_MADRING_AFTER_RACE)
    golden("weekend_team_after_race", client.get("/weekend-team"))


def test_last_team(client, golden, at, snapshots):
    snapshots(*UP_TO_MADRING)
    at(SUN_MADRING_AFTER_RACE)
    golden("last_team", client.get("/last-team"))


def test_last_team_no_snapshots(client, golden, at, empty_snapshots):
    at(SUN_MADRING_AFTER_RACE)
    golden("last_team_no_snapshots", client.get("/last-team"))


def test_finishes_locked(client, golden, at, snapshots):
    snapshots(*UP_TO_MADRING)
    at(SAT_MADRING_BEFORE_QUALI)
    golden("finishes_locked", client.get("/weekend-finishes"))


def test_finishes_provisional(client, golden, at, empty_snapshots):
    at(SAT_MADRING_BEFORE_QUALI)
    golden("finishes_provisional", client.get("/weekend-finishes"))


def test_finishes_held_with_results(client, golden, at, snapshots):
    snapshots(*UP_TO_MADRING)
    at(SUN_MADRING_AFTER_RACE)
    golden("finishes_held", client.get("/weekend-finishes"))


# ---- snapshot automation (only the paths that don't hit the network) ------------

def test_snapshot_auto_needs_secret_configured(client, monkeypatch):
    monkeypatch.delenv("SNAPSHOT_SECRET", raising=False)
    assert client.post("/snapshot/auto").status_code == 503


def test_snapshot_auto_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setenv("SNAPSHOT_SECRET", "test-secret")
    assert client.post("/snapshot/auto", headers={"X-Snapshot-Secret": "nope"}).status_code == 401


@pytest.mark.parametrize("name,when,empty", [
    ("idle_after_race", SUN_MADRING_AFTER_RACE, False),
    ("already_locked", SAT_MADRING_BEFORE_QUALI, False),
    # Madring's results are in the data now, so it refuses before it even looks at FP3
    ("refused_results_in", SAT_MADRING_FP3_RUNNING, True),
    # Baku on FP1 day: live weekend, no snapshot, FP3 hasn't happened yet
    ("waiting_before_fp3", BAKU_THURSDAY, True),
])
def test_snapshot_auto_states(client, golden, at, monkeypatch, tmp_path, snapshots, name, when, empty):
    monkeypatch.setenv("SNAPSHOT_SECRET", "test-secret")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    if empty:
        monkeypatch.setenv("SNAPSHOT_DIR", str(tmp_path))
    else:
        snapshots(*UP_TO_MADRING)
    if name == "waiting_before_fp3":
        # Baku's results are in the data now, pretend they aren't so this keeps testing "waiting"
        monkeypatch.setattr(weekend_lock, "results_already_in_data", lambda race: False)
    at(when)
    golden(f"snapshot_auto_{name}",
           client.post("/snapshot/auto?dry_run=true", headers={"X-Snapshot-Secret": "test-secret"}))


def test_backtest_hidden_in_production(client, monkeypatch):
    monkeypatch.delenv("BACKTEST_ENABLED", raising=False)
    assert client.get("/backtest").status_code == 404


# ---- locking the weekend from a page view --------------------------------------
#
# Bahrain and Singapore both vanished off the site because nothing ever saved them.
# The provisional view was recomputed on every request, so the moment the race
# started and the "upcoming race" moved on, the weekend was gone and the site fell
# back to an older snapshot. So when a provisional is built from the session we
# lock on, it now saves itself instead of being thrown away.
#
# These only test the DECISION. The build itself hits the network, so it stays out.

import json as _json

from src.api.race_weekend import should_self_lock

# UNRACED is made up so its results can never land in data/processed. This used to
# be Singapore, which broke the moment the Monday job added Singapore's results.
# RACED is a real race whose results are in, which is what makes it refused.
UNRACED = "Test Grand Prix"
RACED = "Bahrain Grand Prix"


def test_self_lock_when_provisional_came_from_the_final_session(empty_snapshots):
    assert should_self_lock(UNRACED, session_used="SQ", final_session="SQ") is True


def test_no_self_lock_from_an_earlier_session(empty_snapshots):
    # FP1 standing in because sprint quali isn't published yet. FP1 is a worse
    # predictor, so freezing it would make the saved answer worse than waiting.
    assert should_self_lock(UNRACED, session_used="FP1", final_session="SQ") is False


def test_no_self_lock_without_a_session(empty_snapshots):
    assert should_self_lock(UNRACED, session_used=None, final_session="FP3") is False


def test_no_self_lock_once_the_results_are_known(empty_snapshots):
    # same guard /snapshot/auto has: never build a prediction that saw the answers
    assert should_self_lock(RACED, session_used="FP3", final_session="FP3") is False


def test_no_self_lock_when_the_weekend_is_already_locked(empty_snapshots):
    snap = {"year": 2026, "round": 99, "race_name": UNRACED, "teams": [], "finishes": []}
    (empty_snapshots / "2026_R99_test_grand_prix.json").write_text(_json.dumps(snap))
    assert should_self_lock(UNRACED, session_used="SQ", final_session="SQ") is False


def test_self_lock_can_be_switched_off(empty_snapshots, monkeypatch):
    monkeypatch.setenv("LOCK_ON_VIEW", "0")
    assert should_self_lock(UNRACED, session_used="SQ", final_session="SQ") is False


# ---- the weekend endpoints still hang together after being split into files ----

EXPECTED_ROUTES = {("GET", "/weekend-team"), ("GET", "/last-team"),
                   ("GET", "/weekend-finishes"), ("POST", "/snapshot/auto")}


def test_weekend_routes_are_all_registered(client):
    have = {(m, r.path) for r in client.app.routes for m in getattr(r, "methods", [])}
    assert EXPECTED_ROUTES <= have


def test_snapshot_auto_reports_the_last_failed_build(client, at, monkeypatch, empty_snapshots):
    # _last_snapshot_result gets reassigned with `global`, so if another file ever
    # imports it by name it'd be stuck at {} and the Action would never see failures
    lock = weekend_lock
    monkeypatch.setenv("SNAPSHOT_SECRET", "test-secret")
    monkeypatch.setattr(lock, "fetch_prices", lambda rnd: {"drivers": {"LEC": 24.1}})

    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(lock, "build_snapshot", boom)
    monkeypatch.setattr(lock, "_last_snapshot_result", {})
    monkeypatch.setattr(lock, "results_already_in_data", lambda race: False)

    lock._snapshot_build_lock.acquire()
    lock._build_and_save_snapshot({"EventName": "Test Grand Prix", "RoundNumber": 99})

    at(BAKU_THURSDAY)  # a "waiting" answer, which carries last_result
    r = client.post("/snapshot/auto", headers={"X-Snapshot-Secret": "test-secret"}).json()
    assert r["status"] == "waiting"
    assert r["last_result"]["status"] == "error"
    assert r["last_result"]["detail"] == "boom"
    assert not lock._snapshot_build_lock.locked()


# ---- ownership saved at every lock ----------------------------------------------

def _madring_event():
    from src.api import state
    s = state.race_schedule
    return s[s["EventName"] == MADRING].iloc[0]


def test_snapshot_saves_ownership_at_lock(client, monkeypatch):
    from src import official_points, weekend
    from src.api import state
    fake = {"drivers": {"LEC": {"selected_pct": 26.0, "captain_pct": 14.0}}, "constructors": {}}
    monkeypatch.setattr(official_points, "fetch_ownership", lambda rnd: fake)
    snap = weekend.build_snapshot(_madring_event(), state.current_prices, source="test")
    assert snap["ownership"] == fake
    assert "ownership_fetched_at" in snap


def test_snapshot_keeps_building_when_ownership_fetch_fails(client):
    # conftest makes the feed unreachable, which is the "feed is down" case
    from src import weekend
    from src.api import state
    snap = weekend.build_snapshot(_madring_event(), state.current_prices, source="test")
    assert snap["teams"]
    assert "ownership" not in snap


def test_old_snapshot_without_ownership_still_serves(client, at, snapshots):
    # R13 and R14 were locked before ownership existed
    snapshots(*UP_TO_MADRING)
    at(SAT_MADRING_BEFORE_QUALI)
    r = client.get("/weekend-team")
    assert r.status_code == 200
    assert r.json()["locked"] is True


# ---- the transfer planner (project 3) -----------------------------------------

def _ladder(client, **overrides):
    body = {"race_name": MADRING, "drivers": MADRING_TEAM_DRIVERS,
            "constructors": MADRING_TEAM_CONSTRUCTORS, "budget": 100.0, "free_transfers": 2}
    return client.post("/transfer-ladder", json={**body, **overrides})


def test_transfer_ladder_uses_the_locked_session(client, snapshots):
    snapshots(*UP_TO_MADRING)
    r = _ladder(client)
    body = r.json()
    assert r.status_code == 200
    assert body["provisional"] is False and body["session_used"] == "FP3"
    # the paid row is off (SHOW_PAID_ROW), so keep plus the 2 free ones
    assert [row["transfers"] for row in body["rows"]] == [0, 1, 2]
    assert body["rows"][0]["vs_keep"] == 0
    assert "Transfer 3 costs -10." in body["facts"]


def test_transfer_ladder_is_provisional_before_the_lock(client, empty_snapshots):
    body = _ladder(client).json()
    assert body["provisional"] is True and body["session_used"] == "FP3"


def test_transfer_ladder_matches_the_manual_team_numbers(client, snapshots):
    # same race and session as the Manual Team page, so keep = its drivers + its
    # constructors + the 2x driver once more
    snapshots(*UP_TO_MADRING)
    pool = client.post("/upcoming-race-pool", json={"race_name": MADRING, "year": 2026, "session": "FP3"}).json()["pool"]
    keep = _ladder(client).json()["rows"][0]
    fv = {d["Abbreviation"]: d["FantasyValue"] for d in pool["drivers"]}
    score = {c["name"]: c["score"] for c in pool["constructors"]}
    by_hand = (sum(fv[a] for a in MADRING_TEAM_DRIVERS) + sum(score[c] for c in MADRING_TEAM_CONSTRUCTORS)
               + fv[keep["boost"]])
    assert keep["expected"] == pytest.approx(by_hand, abs=0.01)


def test_transfer_ladder_refuses_bad_free_transfers(client):
    assert _ladder(client, free_transfers=0).status_code == 422
    assert _ladder(client, free_transfers=4).status_code == 422   # 3 is the most you can have
    assert _ladder(client, drivers=MADRING_TEAM_DRIVERS[:4]).status_code == 422
    assert _ladder(client, constructors=["McLaren"]).status_code == 422


def test_transfer_ladder_refuses_the_same_pick_twice(client):
    # final review: the page blocks it, a direct request didn't, and the whole ladder
    # then got built on an illegal team
    twice = [MADRING_TEAM_DRIVERS[0]] * 2 + MADRING_TEAM_DRIVERS[2:]
    assert _ladder(client, drivers=twice).status_code == 422
    assert _ladder(client, constructors=["McLaren", "McLaren"]).status_code == 422


# ---- confidence on the picks (project 4) ----------------------------------------

LEVELS = ("high", "medium", "low")


def test_weekend_team_shows_confidence_once_the_lock_session_is_in(client, at, empty_snapshots):
    at(SAT_MADRING_BEFORE_QUALI)
    body = client.get("/weekend-team").json()
    assert body["session_used"] == "FP3"
    for team in body["teams"]:
        for d in team["drivers"]:
            assert d["Confidence"] in LEVELS
            assert d["ConfidenceReason"].startswith(f"P{d['GridPosition']} in FP3.")
        assert team["boost_pick"]["Confidence"] in LEVELS


def test_no_confidence_on_an_earlier_session_preview(client, at, empty_snapshots, monkeypatch):
    # the FastF1 cache has FP3 even "during" FP3, so pretend FP2 is all that's out
    import src.api.race_weekend as race_weekend
    from src.weekend import load_grid
    monkeypatch.setattr(race_weekend, "weekend_grid", lambda race, final: (load_grid(race, "FP2"), "FP2"))
    at(SAT_MADRING_BEFORE_QUALI)
    body = client.get("/weekend-team").json()
    assert body["session_used"] == "FP2"
    assert all(d.get("Confidence") is None for t in body["teams"] for d in t["drivers"])


def test_snapshot_saves_confidence_at_the_lock(client):
    from src import weekend
    from src.api import state
    snap = weekend.build_snapshot(_madring_event(), state.current_prices, source="test")
    for team in snap["teams"]:
        assert all(d["Confidence"] in LEVELS for d in team["drivers"])
        assert team["boost_pick"]["Confidence"] in LEVELS


def test_confidence_failure_never_breaks_the_weekend(client, at, empty_snapshots, monkeypatch):
    import src.confidence as confidence

    def broken(*args, **kwargs):
        raise RuntimeError("confidence blew up")
    monkeypatch.setattr(confidence, "weekend_confidence", broken)
    at(SAT_MADRING_BEFORE_QUALI)
    r = client.get("/weekend-team")
    assert r.status_code == 200
    assert all(d["Confidence"] is None for t in r.json()["teams"] for d in t["drivers"])


def _ladder_swaps(client):
    rows = _ladder(client).json()["rows"]
    swaps = [s for r in rows for s in r.get("swaps", [])]
    return [s for s in swaps if s["kind"] == "driver"], [s for s in swaps if s["kind"] != "driver"]


def test_transfer_ladder_swaps_carry_the_incoming_drivers_confidence(client, empty_snapshots):
    # FP3 is in but nobody has locked yet, so it's worked out live like the main page
    driver_swaps, others = _ladder_swaps(client)
    assert driver_swaps
    for s in driver_swaps:
        assert s["in_confidence"] in LEVELS
        assert s["in_confidence_reason"].startswith("P")
    assert all("in_confidence" not in s for s in others)


def test_transfer_ladder_reads_confidence_from_the_locked_snapshot(client, empty_snapshots):
    # final review: once a weekend is locked the planner has to say exactly what the
    # snapshot says, never a fresh live version that could disagree with the main page
    from src import weekend
    from src.api import state
    from src.snapshots import save_snapshot
    snap = weekend.build_snapshot(_madring_event(), state.current_prices, source="test")
    assert snap["confidence"]
    snap["confidence"] = {a: {**c, "reason": "from the snapshot"} for a, c in snap["confidence"].items()}
    save_snapshot(snap, force=True)
    driver_swaps, _ = _ladder_swaps(client)
    assert driver_swaps
    assert all(s["in_confidence_reason"] == "from the snapshot" for s in driver_swaps)


def test_transfer_ladder_shows_no_confidence_on_an_old_snapshot(client, snapshots):
    # R14 was locked before project 4, so like the main page there's no label
    snapshots(*UP_TO_MADRING)
    driver_swaps, _ = _ladder_swaps(client)
    assert driver_swaps
    assert all(s["in_confidence"] is None for s in driver_swaps)


def test_sprint_weekends_get_no_confidence_while_switched_off():
    from src.weekend import weekend_confidence_for
    assert weekend_confidence_for("Singapore Grand Prix", "SQ", "SQ") is None
