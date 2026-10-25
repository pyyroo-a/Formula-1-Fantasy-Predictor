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
