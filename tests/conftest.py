"""
Shared setup for the tests.

The idea: we record what every endpoint returns right now (the "golden" files in
tests/golden/), then whenever we move code around, every endpoint has to give back
exactly the same answer. If anything changes, a test fails and we know straight away
that a refactor accidentally changed the predictions.

To make that work, every answer has to be the same each run, so:
  - prices come from saved files in tests/fixtures/ instead of the live F1 feed
  - "now" is a pretend time we pick for each test, not the real clock
  - the app's startup (which downloads new results and prices) doesn't run
  - OpenF1 is switched off, so practice comes from the FastF1 cache like it always
    did (the OpenF1 code has its own offline tests in test_openf1.py)
  - race results come from a frozen copy in tests/fixtures/processed/ instead of
    data/processed/, which the Monday job changes every week. Before this the goldens
    went stale after every race even though no code had changed

Run the tests:            python -m pytest
Re-record after a change you MEANT to make:   UPDATE_GOLDEN=1 python -m pytest

If a test ever needs a newer race, copy data/processed/*.csv over the frozen copy on
purpose, check only race data moved in the goldens, then re-record.
"""
import importlib
import json
import os
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden"

# no network in the golden tests. test_openf1.py turns it back on with fakes
os.environ["USE_OPENF1"] = "0"

# frozen race results, see the docstring. relative because we chdir to ROOT below
os.environ["PROCESSED_DIR"] = "tests/fixtures/processed"

# the app reads data/... with relative paths, so run everything from the repo root
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# pretend times we test at (UTC). Madring 2026: FP3 10:30, quali 14:00 Sat, race 13:00 Sun
SAT_MADRING_BEFORE_QUALI = pd.Timestamp("2026-09-12 12:30", tz="UTC")
SAT_MADRING_FP3_RUNNING = pd.Timestamp("2026-09-12 10:45", tz="UTC")
SUN_MADRING_AFTER_RACE = pd.Timestamp("2026-09-13 18:40", tz="UTC")
# Baku runs Thursday to Saturday, so Thursday is FP1 day
BAKU_THURSDAY = pd.Timestamp("2026-09-24 12:00", tz="UTC")


def _module(*names):
    """First module that exists. Lets these tests keep working while we split main.py up."""
    for name in names:
        try:
            return importlib.import_module(name)
        except ModuleNotFoundError:
            continue
    raise ModuleNotFoundError(names)


@pytest.fixture(autouse=True)
def no_live_fantasy_feed(monkeypatch):
    """
    No test ever reaches the live F1 Fantasy feed for points or ownership. Same idea as
    USE_OPENF1=0. Building a snapshot then behaves like the feed being down, which it
    has to survive anyway. Tests that want feed data patch in their own fakes.
    """
    import src.official_points as official_points

    def _blocked(*args, **kwargs):
        raise RuntimeError("no live F1 Fantasy feed in tests")

    monkeypatch.setattr(official_points, "fetch_official_points", _blocked)
    monkeypatch.setattr(official_points, "fetch_ownership", _blocked)


@pytest.fixture(scope="session")
def app_state():
    """Loads the same data the app loads at startup, but from saved files."""
    main = importlib.import_module("main")
    state = _module("src.api.state", "main")

    from src.pipeline import run_pipeline
    import fastf1

    fastf1.Cache.enable_cache("data/cache")
    state.fantasy_table = run_pipeline()
    state.current_prices = json.loads((FIXTURES / "prices_r14.json").read_text())
    state.price_changes = json.loads((FIXTURES / "price_changes_r14.json").read_text())
    state.race_schedule = fastf1.get_event_schedule(2026, include_testing=False)
    return main


@pytest.fixture(scope="session")
def client(app_state):
    from fastapi.testclient import TestClient
    # no "with" block on purpose: that would run the real startup and hit the network
    return TestClient(app_state.app)


@pytest.fixture
def at(monkeypatch):
    """Call at(some_time) to make the app think it's that time."""
    def _set(t):
        clock = _module("src.api.clock", "main")
        name = "now" if hasattr(clock, "now") else "_now"
        monkeypatch.setattr(clock, name, lambda: t)
    return _set


@pytest.fixture
def empty_snapshots(monkeypatch, tmp_path):
    """Points the app at an empty snapshot folder, like a weekend nobody has locked yet."""
    monkeypatch.setenv("SNAPSHOT_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def snapshots(monkeypatch, tmp_path):
    """
    Pins which snapshots exist, e.g. snapshots("2026_R13...", "2026_R14...").

    Without this the tests read the real data/snapshots folder, so every new race
    weekend silently changed what "the newest snapshot" meant and quietly rewrote
    these answers. Now they only see the files we name.
    """
    def _use(*names):
        for name in names:
            shutil.copy(ROOT / "data" / "snapshots" / name, tmp_path / name)
        monkeypatch.setenv("SNAPSHOT_DIR", str(tmp_path))
        return tmp_path
    return _use


def _normalise(obj):
    # round trip through JSON so numpy types, key order etc. can't cause fake differences
    return json.loads(json.dumps(obj, sort_keys=True, default=str))


@pytest.fixture
def golden():
    """golden(name, response) checks a response against its recorded copy."""
    def _check(name, response):
        got = {"status": response.status_code, "body": _normalise(response.json())}
        path = GOLDEN / f"{name}.json"
        if os.getenv("UPDATE_GOLDEN") or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(got, indent=1, sort_keys=True))
            return
        expected = json.loads(path.read_text())
        assert got == expected, f"{name} changed. If you meant it, re-record with UPDATE_GOLDEN=1"
    return _check
