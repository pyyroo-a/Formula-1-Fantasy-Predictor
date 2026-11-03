"""
Checks for the OpenF1 fallback (src/openf1.py).

F1 put its live timing archive behind an F1TV login in October 2026, so FastF1 stopped
loading new sessions and the site sat on "no practice data yet" all US GP weekend.
OpenF1 gives the same laps for free. None of these hit the network, the HTTP calls
are swapped for canned answers shaped like OpenF1's real ones.
"""
import pandas as pd
import pytest

import src.fetch_practice as fp
import src.openf1 as of1

START = pd.Timestamp("2026-10-23 21:00", tz="UTC")  # US GP FP2


def _session(key=11390, name="Practice 2", start=START, minutes=60, cancelled=False):
    return {
        "session_key": key,
        "session_name": name,
        "date_start": start.isoformat(),
        "date_end": (start + pd.Timedelta(minutes=minutes)).isoformat(),
        "is_cancelled": cancelled,
        "year": 2026,
    }


LAPS = [
    {"driver_number": 16, "lap_duration": 95.512},
    {"driver_number": 16, "lap_duration": 94.900},   # LEC's best
    {"driver_number": 12, "lap_duration": 95.010},
    {"driver_number": 1, "lap_duration": 95.300},
    {"driver_number": 1, "lap_duration": None},      # out lap, no time
    {"driver_number": 44, "lap_duration": 95.700},
]
DRIVERS = [
    {"driver_number": 16, "name_acronym": "LEC", "team_name": "Ferrari", "first_name": "Charles", "last_name": "Leclerc"},
    {"driver_number": 44, "name_acronym": "HAM", "team_name": "Ferrari", "first_name": "Lewis", "last_name": "Hamilton"},
    {"driver_number": 12, "name_acronym": "ANT", "team_name": "Mercedes", "first_name": "Andrea Kimi", "last_name": "Antonelli"},
    {"driver_number": 1, "name_acronym": "VER", "team_name": "Red Bull Racing", "first_name": "Max", "last_name": "Verstappen"},
]


# ---- turning laps into a grid --------------------------------------------------

def test_grid_ranks_by_each_drivers_fastest_lap():
    grid = of1.grid_from_openf1(LAPS, DRIVERS, "United States Grand Prix")
    assert grid["Abbreviation"].tolist() == ["LEC", "ANT", "VER", "HAM"]
    assert grid["GridPosition"].tolist() == [1, 2, 3, 4]
    assert (grid["RaceName"] == "United States Grand Prix").all()


def test_grid_gaps_match_what_fastf1_gave_us():
    grid = of1.grid_from_openf1(LAPS, DRIVERS, "United States Grand Prix").set_index("Abbreviation")
    assert grid.loc["LEC", "GapToPole"] == 0.0
    assert grid.loc["ANT", "GapToPole"] == 0.11
    # gap to teammate: HAM is 0.8 off LEC, LEC is the reference so 0
    assert grid.loc["HAM", "GapToTeammate"] == 0.8
    assert grid.loc["LEC", "GapToTeammate"] == 0.0


def test_grid_has_exactly_the_columns_the_model_expects():
    grid = of1.grid_from_openf1(LAPS, DRIVERS, "United States Grand Prix")
    assert list(grid.columns) == ["Abbreviation", "TeamName", "GridPosition", "RaceName",
                                  "GapToPole", "GapToTeammate"]


def test_grid_with_no_timed_laps_is_not_published():
    with pytest.raises(of1.NotPublishedYet):
        of1.grid_from_openf1([{"driver_number": 16, "lap_duration": None}], DRIVERS, "X")


# ---- finding the right session -------------------------------------------------

def test_pick_session_matches_on_name_and_start_time():
    sessions = [_session(1, "Practice 1", START - pd.Timedelta(hours=3, minutes=30)),
                _session(2, "Practice 2", START),
                _session(3, "Practice 2", START + pd.Timedelta(days=28))]  # a later race's FP2
    assert of1.pick_session(sessions, "Practice 2", START)["session_key"] == 2


def test_pick_session_finds_nothing_when_no_start_time_is_close():
    sessions = [_session(2, "Practice 2", START + pd.Timedelta(days=7))]
    assert of1.pick_session(sessions, "Practice 2", START) is None


def test_pick_session_copes_with_fastf1s_timezone_free_times():
    # FastF1's schedule hands back naive UTC times, OpenF1 has +00:00 on them
    sessions = [_session(2, "Practice 2", START)]
    assert of1.pick_session(sessions, "Practice 2", pd.Timestamp("2026-10-23 21:00"))["session_key"] == 2


# ---- never using a session that isn't over --------------------------------------

def test_session_not_ready_while_it_is_running():
    assert of1.session_ready(_session(), START + pd.Timedelta(minutes=40)) is False


def test_session_not_ready_straight_after_it_ends():
    # laps can still be coming in, and freezing half a session would be worse than waiting
    assert of1.session_ready(_session(), START + pd.Timedelta(minutes=65)) is False


def test_session_ready_once_the_buffer_has_passed():
    assert of1.session_ready(_session(), START + pd.Timedelta(minutes=60) + of1.INGEST_BUFFER) is True


def test_cancelled_session_is_never_ready():
    assert of1.session_ready(_session(cancelled=True), START + pd.Timedelta(days=1)) is False


# ---- fetching, with the HTTP swapped out --------------------------------------

@pytest.fixture
def fake_openf1(monkeypatch):
    """Swaps OpenF1's HTTP for canned answers. Returns the list of calls made."""
    calls = []
    sessions = [_session()]

    def fake_get(path, params):
        calls.append(path)
        if path == "sessions":
            return sessions
        if path == "laps":
            return LAPS
        if path == "drivers":
            return DRIVERS
        if path == "session_result":
            return []   # "No results found.", what OpenF1 says before the classification is out
        raise AssertionError(path)

    monkeypatch.setenv("USE_OPENF1", "1")
    monkeypatch.setattr(of1, "_get", fake_get)
    of1.clear_caches()
    yield calls
    of1.clear_caches()


def test_openf1_grid_after_the_session(fake_openf1):
    grid = of1.openf1_grid(2026, "United States Grand Prix", "FP2", START,
                           now=START + pd.Timedelta(hours=3))
    assert grid["Abbreviation"].iloc[0] == "LEC"


def test_openf1_grid_refuses_during_the_session(fake_openf1):
    with pytest.raises(of1.NotPublishedYet):
        of1.openf1_grid(2026, "United States Grand Prix", "FP2", START,
                        now=START + pd.Timedelta(minutes=30))
    assert "laps" not in fake_openf1  # didn't even ask for laps


def test_finished_grid_is_only_downloaded_once(fake_openf1):
    later = START + pd.Timedelta(hours=3)
    of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    # every page view asks for this, and OpenF1's free tier is rate limited
    assert fake_openf1.count("laps") == 1


def test_cached_grid_is_a_copy(fake_openf1):
    later = START + pd.Timedelta(hours=3)
    g = of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    g.loc[0, "Abbreviation"] = "XXX"  # a caller scribbling on its copy
    again = of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    assert again["Abbreviation"].iloc[0] == "LEC"


def test_unknown_session_is_unavailable_not_unpublished(fake_openf1):
    # "OpenF1 doesn't know this session" must let FastF1 have a go,
    # "the session isn't over" must not
    with pytest.raises(of1.OpenF1Unavailable):
        of1.openf1_grid(2026, "United States Grand Prix", "FP2", START + pd.Timedelta(days=30),
                        now=START + pd.Timedelta(days=31))


def test_switched_off_means_unavailable(fake_openf1, monkeypatch):
    monkeypatch.setenv("USE_OPENF1", "0")
    with pytest.raises(of1.OpenF1Unavailable):
        of1.openf1_grid(2026, "United States Grand Prix", "FP2", START,
                        now=START + pd.Timedelta(hours=3))
    assert fake_openf1 == []


# ---- get_practice_grid picks the source -----------------------------------------

@pytest.fixture
def no_schedule(monkeypatch):
    """get_practice_grid looks the session's start up in FastF1's schedule, skip that."""
    monkeypatch.setattr(fp, "_session_start_utc", lambda year, race, name: START)
    monkeypatch.setattr(fp, "is_sprint_weekend", lambda race, year=None: False)


def test_practice_grid_comes_from_openf1_first(monkeypatch, no_schedule):
    monkeypatch.setattr(fp.openf1, "openf1_grid", lambda *a, **k: "from openf1")
    monkeypatch.setattr(fp, "_fastf1_practice_grid", lambda *a: pytest.fail("FastF1 shouldn't be tried"))
    assert fp.get_practice_grid(2026, "United States Grand Prix", "FP2") == "from openf1"


def test_practice_grid_falls_back_to_fastf1_when_openf1_cant_help(monkeypatch, no_schedule):
    def unavailable(*a, **k):
        raise of1.OpenF1Unavailable("rate limited")
    monkeypatch.setattr(fp.openf1, "openf1_grid", unavailable)
    from_fastf1 = pd.DataFrame({"Abbreviation": ["LEC"]})
    monkeypatch.setattr(fp, "_fastf1_practice_grid", lambda *a: from_fastf1)
    assert fp.get_practice_grid(2026, "Bahrain Grand Prix", "FP3") is from_fastf1


def test_practice_grid_doesnt_ask_fastf1_about_an_unfinished_session(monkeypatch, no_schedule):
    # FastF1 can't have a session that isn't over either, and asking costs ~8s a time
    def not_yet(*a, **k):
        raise of1.NotPublishedYet("FP3 still running")
    monkeypatch.setattr(fp.openf1, "openf1_grid", not_yet)
    monkeypatch.setattr(fp, "_fastf1_practice_grid", lambda *a: pytest.fail("FastF1 shouldn't be tried"))
    with pytest.raises(of1.NotPublishedYet):
        fp.get_practice_grid(2026, "United States Grand Prix", "FP3")


def test_sprint_quali_grid_comes_from_openf1_first(monkeypatch, no_schedule):
    seen = {}

    def grid(year, race, session, start, **k):
        seen["session"] = session
        return "from openf1"
    monkeypatch.setattr(fp.openf1, "openf1_grid", grid)
    monkeypatch.setattr(fp, "_fastf1_sprint_quali_grid", lambda *a: pytest.fail("FastF1 shouldn't be tried"))
    assert fp.get_sprint_quali_grid(2026, "Singapore Grand Prix") == "from openf1"
    assert seen["session"] == "SQ"


# ---- session_published, which the automatic lock checks before building ----------
#
# It used to ask livetiming directly, which has answered 401 to everything since the
# login change, so /snapshot/auto said "FP3 isn't published yet" forever and the
# GitHub Action could never lock a weekend.

import src.weekend as weekend


@pytest.fixture
def weekend_start(monkeypatch):
    monkeypatch.setattr(weekend, "_session_start_utc", lambda year, race, name: START)


def test_published_once_openf1_has_the_finished_session(monkeypatch, weekend_start):
    monkeypatch.setattr(weekend.openf1, "openf1_grid", lambda *a, **k: "a grid")
    assert weekend.session_published("United States Grand Prix", "FP3") is True


def test_not_published_while_openf1_says_not_yet(monkeypatch, weekend_start):
    def not_yet(*a, **k):
        raise of1.NotPublishedYet("still running")
    monkeypatch.setattr(weekend.openf1, "openf1_grid", not_yet)
    assert weekend.session_published("United States Grand Prix", "FP3") is False


def test_openf1_trouble_is_an_error_not_a_wait(monkeypatch, weekend_start):
    # the Madring lesson: "can't check" must never look like "not out yet", or a broken
    # source just says "waiting" all weekend and nobody notices
    def broken(*a, **k):
        raise of1.OpenF1Unavailable("503 from OpenF1")
    monkeypatch.setattr(weekend.openf1, "openf1_grid", broken)
    with pytest.raises(of1.OpenF1Unavailable):
        weekend.session_published("United States Grand Prix", "FP3")


# ---- the Practice page (RACE DATA > PRACTICE) ------------------------------------
#
# The page asked FastF1 for laps too, so it answered 500 for every race after the
# F1TV login change. Now it gets them from OpenF1 like the model does.

def test_practice_table_rows_like_the_page_expects():
    rows = of1.practice_table(LAPS, DRIVERS)
    assert [r["Abbreviation"] for r in rows] == ["LEC", "ANT", "VER", "HAM"]
    assert rows[0] == {"Position": 1, "Abbreviation": "LEC", "FullName": "Charles Leclerc",
                       "TeamName": "Ferrari", "LapTime": "1:34.900", "GapToPole": 0.0}
    assert rows[1]["GapToPole"] == 0.11
    assert rows[3]["LapTime"] == "1:35.700"


def test_practice_table_name_falls_back_to_the_code():
    drivers = [{"driver_number": 16, "name_acronym": "LEC", "team_name": "Ferrari"}]
    rows = of1.practice_table([{"driver_number": 16, "lap_duration": 94.9}], drivers)
    assert rows[0]["FullName"] == "LEC"


def test_practice_table_with_no_timed_laps_is_not_published():
    with pytest.raises(of1.NotPublishedYet):
        of1.practice_table([{"driver_number": 16, "lap_duration": None}], DRIVERS)


def test_openf1_practice_after_the_session(fake_openf1):
    rows = of1.openf1_practice(2026, "United States Grand Prix", "FP2", START,
                               now=START + pd.Timedelta(hours=3))
    assert rows[0]["Abbreviation"] == "LEC"


def test_openf1_practice_and_grid_share_one_download(fake_openf1):
    later = START + pd.Timedelta(hours=3)
    of1.openf1_practice(2026, "United States Grand Prix", "FP2", START, now=later)
    of1.openf1_practice(2026, "United States Grand Prix", "FP2", START, now=later)
    of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    assert fake_openf1.count("laps") == 1


def test_openf1_practice_refuses_during_the_session(fake_openf1):
    with pytest.raises(of1.NotPublishedYet):
        of1.openf1_practice(2026, "United States Grand Prix", "FP2", START,
                            now=START + pd.Timedelta(minutes=10))
    assert "laps" not in fake_openf1


class _FakeEvent(dict):
    def __init__(self):
        super().__init__(Session1="Practice 1", Session2="Practice 2", Session3="Practice 3",
                         Session4="Qualifying", Session5="Race")


@pytest.fixture
def races_api(monkeypatch):
    import src.api.races as races
    monkeypatch.setattr(races.fastf1, "get_event", lambda year, race: _FakeEvent())
    monkeypatch.setattr(races, "_session_start_utc", lambda year, race, name: START)
    return races


def test_practice_endpoint_uses_openf1(races_api, client, monkeypatch):
    rows = [{"Position": 1, "Abbreviation": "LEC", "FullName": "Charles Leclerc",
             "TeamName": "Ferrari", "LapTime": "1:34.900", "GapToPole": 0.0}]
    monkeypatch.setattr(races_api.openf1, "openf1_practice", lambda *a, **k: rows)
    monkeypatch.setattr(races_api, "_fastf1_practice_rows", lambda *a: pytest.fail("FastF1 shouldn't be tried"))
    r = client.post("/practice-results", json={"race_name": "United States Grand Prix", "session": "FP3"})
    assert r.status_code == 200
    assert r.json() == {"session": "FP3", "available_sessions": ["FP1", "FP2", "FP3"], "results": rows}


def test_practice_endpoint_says_not_over_yet(races_api, client, monkeypatch):
    def not_yet(*a, **k):
        raise of1.NotPublishedYet("United States Grand Prix FP3 isn't over yet")
    monkeypatch.setattr(races_api.openf1, "openf1_practice", not_yet)
    r = client.post("/practice-results", json={"race_name": "United States Grand Prix", "session": "FP3"})
    assert r.status_code == 404
    assert "isn't over yet" in r.json()["detail"]


def test_practice_endpoint_falls_back_to_fastf1(races_api, client, monkeypatch):
    def unavailable(*a, **k):
        raise of1.OpenF1Unavailable("rate limited")
    monkeypatch.setattr(races_api.openf1, "openf1_practice", unavailable)
    monkeypatch.setattr(races_api, "_fastf1_practice_rows", lambda *a: [{"Abbreviation": "VER"}])
    r = client.post("/practice-results", json={"race_name": "United States Grand Prix", "session": "FP2"})
    assert r.status_code == 200
    assert r.json()["session"] == "FP2"
    assert r.json()["results"] == [{"Abbreviation": "VER"}]


def test_an_empty_answer_is_not_remembered(fake_openf1, monkeypatch):
    # OpenF1 can still be filling in laps after the buffer. An empty answer has to be
    # asked again next time, or the lock says "not published" until the server restarts
    answers = iter([[], LAPS])
    real_get = of1._get

    def first_empty(path, params):
        if path == "laps":
            fake_openf1.append("laps")
            return next(answers)
        return real_get(path, params)
    monkeypatch.setattr(of1, "_get", first_empty)
    later = START + pd.Timedelta(hours=3)
    with pytest.raises(of1.NotPublishedYet):
        of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    grid = of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=later)
    assert grid["Abbreviation"].iloc[0] == "LEC"
    rows = of1.openf1_practice(2026, "United States Grand Prix", "FP2", START, now=later)
    assert rows[0]["Abbreviation"] == "LEC"


# ---- OpenF1's odd answers --------------------------------------------------------
#
# Mexico FP3: the laps answered {"detail": "No results found."} for hours, and _get
# treated any dict as "OpenF1 is down", so it went off to FastF1 (401s) instead of
# just saying "no laps yet". And during a live session OpenF1 blocks everything for
# free users, which has to mean "try again later", not "broken".

NO_RESULTS = {"detail": "No results found."}
LIVE_BLOCK = {"detail": "Live F1 session in progress. Global API access (including past sessions) is "
                        "restricted to authenticated users until the session ends. Get an API key here: "
                        "https://buy.stripe.com/eVqcN41BPekP0iIalBcEw02"}


class _FakeResponse:
    def __init__(self, data, status=200):
        self.status_code, self._data = status, data

    def json(self):
        return self._data


@pytest.fixture
def openf1_answers(monkeypatch):
    """Makes OpenF1 answer with whatever you pass in."""
    def _answer(data, status=200):
        monkeypatch.setattr(of1.httpx, "get", lambda *a, **k: _FakeResponse(data, status))
    return _answer


def test_no_results_found_is_an_empty_list_not_openf1_down(openf1_answers):
    openf1_answers(NO_RESULTS)
    assert of1._get("laps", {"session_key": 11399}) == []


def test_live_block_is_try_later_not_openf1_down(openf1_answers):
    openf1_answers(LIVE_BLOCK)
    with pytest.raises(of1.LiveBlocked):
        of1._get("laps", {"session_key": 11399})
    assert issubclass(of1.LiveBlocked, of1.NotPublishedYet)


def test_other_odd_answers_still_mean_unavailable(openf1_answers):
    openf1_answers({"detail": "something else went wrong"})
    with pytest.raises(of1.OpenF1Unavailable):
        of1._get("laps", {})


def test_practice_grid_doesnt_ask_fastf1_during_the_live_block(monkeypatch, no_schedule):
    def blocked(*a, **k):
        raise of1.LiveBlocked("live session")
    monkeypatch.setattr(fp.openf1, "openf1_grid", blocked)
    monkeypatch.setattr(fp, "_fastf1_practice_grid", lambda *a: pytest.fail("FastF1 shouldn't be tried"))
    with pytest.raises(of1.NotPublishedYet):
        fp.get_practice_grid(2026, "Mexico City Grand Prix", "FP3")


def test_live_block_is_try_later_whatever_the_status_code(openf1_answers):
    # we never saw which status OpenF1 sends with the block, so don't depend on it
    openf1_answers(LIVE_BLOCK, status=401)
    with pytest.raises(of1.LiveBlocked):
        of1._get("laps", {"session_key": 11399})


def test_no_results_found_with_its_real_404_is_still_an_empty_list(openf1_answers):
    # checked on 2026-11-03: OpenF1 sends "No results found." with a 404
    openf1_answers(NO_RESULTS, status=404)
    assert of1._get("laps", {"session_key": 11399}) == []


# ---- naming drivers from the whole meeting ---------------------------------------
#
# A session's /drivers can be empty (Monaco FP2, Singapore SQ) or out of date (Mexico
# FP3 had no car 30 LAW, and on the day it had OCO where car 50 HIR drove). So a car
# the session can't name gets looked up in the rest of the weekend, and if nobody can
# name it, it's left out. Never guessed.

import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "openf1"


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


MEX_FP3 = {**_session(key=11399, name="Practice 3"), "meeting_key": 1298}
MEX_FP2 = {**_session(key=11398, name="Practice 2", start=START - pd.Timedelta(hours=20)), "meeting_key": 1298}
OTHER_WEEKEND = {**_session(key=11000, name="Practice 2", start=START - pd.Timedelta(days=7)), "meeting_key": 1290}


@pytest.fixture
def mexico_openf1(monkeypatch):
    """OpenF1 as it looked for Mexico: FP3's driver list has no car 30, FP2's does."""
    answers = {
        ("sessions", None): [MEX_FP2, MEX_FP3, OTHER_WEEKEND],
        ("drivers", 11399): _fixture("mexico_fp3_drivers.json"),
        ("drivers", 11398): _fixture("mexico_fp2_drivers.json"),
        ("drivers", 11000): [{"driver_number": 30, "name_acronym": "WRONG", "team_name": "Nope"}],
        ("laps", 11399): _fixture("mexico_fp3_laps_best.json"),
        ("session_result", 11399): _fixture("mexico_fp3_session_result.json"),
    }

    def fake_get(path, params):
        return answers[(path, params.get("session_key"))]

    monkeypatch.setenv("USE_OPENF1", "1")
    monkeypatch.setattr(of1, "_get", fake_get)
    of1.clear_caches()
    yield answers
    of1.clear_caches()


def _acronyms(drivers):
    return {d["driver_number"]: d["name_acronym"] for d in drivers}


def test_meeting_drivers_fill_in_a_car_missing_from_the_session(mexico_openf1):
    assert 30 not in _acronyms(mexico_openf1[("drivers", 11399)])
    names = _acronyms(of1.meeting_drivers(MEX_FP3))
    assert names[30] == "LAW"          # from FP2, the same weekend
    assert names[50] == "HIR"          # the session's own list


def test_session_drivers_win_over_the_rest_of_the_meeting(mexico_openf1):
    mexico_openf1[("drivers", 11398)] = [{"driver_number": 1, "name_acronym": "OLD", "team_name": "McLaren"}]
    assert _acronyms(of1.meeting_drivers(MEX_FP3))[1] == "NOR"


def test_meeting_drivers_never_look_at_another_weekend(mexico_openf1):
    mexico_openf1[("drivers", 11398)] = []
    assert 30 not in _acronyms(of1.meeting_drivers(MEX_FP3))


def test_grid_with_empty_drivers_list_is_not_published_instead_of_crashing():
    with pytest.raises(of1.NotPublishedYet):
        of1.grid_from_openf1(LAPS, [], "x")


def test_grid_drops_a_car_nobody_can_name():
    grid = of1.grid_from_openf1(LAPS + [{"driver_number": 99, "lap_duration": 90.0}], DRIVERS, "x")
    assert len(grid) == 4
    assert grid.iloc[0]["Abbreviation"] == "LEC"


def test_practice_table_with_empty_drivers_list_is_not_published_instead_of_crashing():
    with pytest.raises(of1.NotPublishedYet):
        of1.practice_table(LAPS, [])


def test_mexico_fp3_grid_names_lawson_from_fp2(mexico_openf1):
    grid = of1.openf1_grid(2026, "Mexico City Grand Prix", "FP3", MEX_FP3["date_start"],
                           now=START + pd.Timedelta(hours=3))
    assert "LAW" in set(grid["Abbreviation"])
    assert "HIR" in set(grid["Abbreviation"])
    assert list(grid["Abbreviation"][:3]) == ["NOR", "ANT", "LEC"]


# ---- the classification backup ---------------------------------------------------
#
# Mexico FP3: no laps for hours, but /session_result had every driver's best lap the
# whole time. Same ranking maths as the laps, so it's a straight backup.

def test_classification_grid_matches_mexico_fp3():
    grid = of1.grid_from_classification(_fixture("mexico_fp3_session_result.json"),
                                        _fixture("mexico_fp3_drivers.json"), "Mexico City Grand Prix")
    assert list(grid["Abbreviation"][:5]) == ["NOR", "ANT", "LEC", "PIA", "VER"]
    assert grid.iloc[1]["GapToPole"] == pytest.approx(0.001, abs=1e-6)
    assert "PER" not in set(grid["Abbreviation"])        # no time, drops out
    assert "HIR" in set(grid["Abbreviation"])            # car 50 really was HIR
    assert list(grid.columns) == list(of1.grid_from_openf1(LAPS, DRIVERS, "x").columns)


def test_classification_grid_takes_the_best_part_of_sprint_quali():
    results = _fixture("sq_session_result.json")
    drivers = [{"driver_number": r["driver_number"], "name_acronym": f"D{r['driver_number']}", "team_name": "Ferrari"}
               for r in results]
    grid = of1.grid_from_classification(results, drivers, "Miami Grand Prix")
    best = {f"D{r['driver_number']}": min(t for t in r["duration"] if t)
            for r in results if r["duration"] and any(r["duration"])}
    assert list(grid["Abbreviation"]) == sorted(best, key=best.get)


def test_classification_with_no_times_is_not_published():
    with pytest.raises(of1.NotPublishedYet):
        of1.grid_from_classification([{"driver_number": 1, "duration": None}], DRIVERS, "x")
    with pytest.raises(of1.NotPublishedYet):
        of1.grid_from_classification([], DRIVERS, "x")


def _mexico_fp3_grid():
    return of1.openf1_grid(2026, "Mexico City Grand Prix", "FP3", MEX_FP3["date_start"],
                           now=START + pd.Timedelta(hours=3))


def test_openf1_grid_falls_back_to_the_classification_when_laps_say_no_results(mexico_openf1):
    mexico_openf1[("laps", 11399)] = []
    mexico_openf1[("session_result", 11399)] = _fixture("mexico_fp3_session_result.json")
    grid = _mexico_fp3_grid()
    assert grid.attrs["lap_source"] == "classification"
    assert list(grid["Abbreviation"][:3]) == ["NOR", "ANT", "LEC"]
    assert "LAW" in set(grid["Abbreviation"])            # named from FP2, like the laps route


def test_classification_grid_is_not_cached_so_laps_can_take_over(mexico_openf1):
    laps = mexico_openf1[("laps", 11399)]
    mexico_openf1[("laps", 11399)] = []
    mexico_openf1[("session_result", 11399)] = _fixture("mexico_fp3_session_result.json")
    assert _mexico_fp3_grid().attrs["lap_source"] == "classification"
    mexico_openf1[("laps", 11399)] = laps
    assert _mexico_fp3_grid().attrs["lap_source"] == "laps"


def test_nothing_anywhere_is_not_published_yet(mexico_openf1):
    mexico_openf1[("laps", 11399)] = []
    mexico_openf1[("session_result", 11399)] = [{"driver_number": 1, "duration": None}]
    with pytest.raises(of1.NotPublishedYet):
        _mexico_fp3_grid()


def test_laps_grid_says_it_came_from_laps(fake_openf1):
    grid = of1.openf1_grid(2026, "United States Grand Prix", "FP2", START, now=START + pd.Timedelta(hours=2))
    assert grid.attrs["lap_source"] == "laps"
    # the cached copy too
    assert of1.openf1_grid(2026, "United States Grand Prix", "FP2", START,
                           now=START + pd.Timedelta(hours=2)).attrs["lap_source"] == "laps"


def test_fastf1_grid_says_it_came_from_fastf1(monkeypatch, no_schedule):
    def unavailable(*a, **k):
        raise of1.OpenF1Unavailable("down")
    monkeypatch.setattr(fp.openf1, "openf1_grid", unavailable)
    monkeypatch.setattr(fp, "_fastf1_practice_grid", lambda *a: pd.DataFrame({"Abbreviation": ["LEC"]}))
    assert fp.get_practice_grid(2026, "Bahrain Grand Prix", "FP3").attrs["lap_source"] == "fastf1"


def test_half_filled_laps_lose_to_a_fuller_classification(mexico_openf1):
    # final review: if OpenF1 fills late laps in a few drivers at a time, a lock built in
    # the middle would only have some of the grid, frozen forever. The classification
    # wins until the laps have everyone it has
    full = mexico_openf1[("laps", 11399)]
    timed = [lap for lap in full if lap.get("lap_duration") is not None]
    mexico_openf1[("laps", 11399)] = timed[:5]
    mexico_openf1[("session_result", 11399)] = _fixture("mexico_fp3_session_result.json")
    grid = _mexico_fp3_grid()
    assert grid.attrs["lap_source"] == "classification"
    assert len(grid) > 5
    # and nothing half filled got remembered: once the laps are all in, they win
    mexico_openf1[("laps", 11399)] = full
    assert _mexico_fp3_grid().attrs["lap_source"] == "laps"


def test_full_laps_still_win_when_the_classification_is_missing(mexico_openf1):
    mexico_openf1[("session_result", 11399)] = []
    assert _mexico_fp3_grid().attrs["lap_source"] == "laps"


def test_rate_limit_backs_off_a_few_times_before_giving_up(monkeypatch):
    # final review: lock day makes a burst of calls with cold caches, and one 2 second
    # retry wasn't much against the free tier's rate limit
    answers = iter([_FakeResponse({}, 429), _FakeResponse({}, 429), _FakeResponse([{"ok": 1}])])
    waits = []
    monkeypatch.setattr(of1.httpx, "get", lambda *a, **k: next(answers))
    monkeypatch.setattr(of1.time, "sleep", waits.append)
    assert of1._get("laps", {}) == [{"ok": 1}]
    assert waits == [2, 4]


def test_rate_limit_still_gives_up_eventually(monkeypatch):
    monkeypatch.setattr(of1.httpx, "get", lambda *a, **k: _FakeResponse({}, 429))
    monkeypatch.setattr(of1.time, "sleep", lambda s: None)
    with pytest.raises(of1.OpenF1Unavailable):
        of1._get("laps", {})
