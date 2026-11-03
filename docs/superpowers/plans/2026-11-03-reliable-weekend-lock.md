# Reliable weekend lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Brazil and every weekend after it locks by itself before quali, the Garage keeps working once a weekend is locked, and Render stays awake.

**Architecture:** `src/openf1.py` learns to read OpenF1's odd answers, name drivers from the whole meeting and fall back to the classification when laps are missing. The lock saves the full forecast pool and the Garage endpoints read it. The lock Action becomes a long running loop, the backend gets a `/health` page, and `scripts/lock_team.py` gets a dry run.

**Tech Stack:** Python 3.13, FastAPI, pandas, httpx, pytest, GitHub Actions (bash).

**Spec:** `docs/superpowers/specs/2026-11-03-reliable-weekend-lock-design.md`

## Global Constraints

- Backend pushed before Brazil FP1, Fri 6 Nov 2026 15:30 UTC (18:30 for Ashen).
- Free only. No paid OpenF1 key, no F1TV, no formula1.com or F1 account scraping.
- Tests first. All 216 backend tests and 48 frontend tests keep passing, `tests/test_no_dashes.py` too, `npm run lint` no worse than the 4 old errors.
- Tests never call OpenF1 for real. Recorded answers live in `tests/fixtures/openf1/`.
- No em dashes or en dashes anywhere. Comments and notes in Ashen's plain casual voice ("we", "basically", short why).
- Ashen commits and pushes, never Claude. Each "Commit" step means: hand Ashen the files to tick in GitHub Desktop, a Summary and a Description, then wait for "committed".
- Wait for FP3 (or SQ on sprint weekends). Never lock from an earlier session. A late FP3 lock is flagged `built_after_quali_start`.
- A car number we can't name gets left out and logged, never guessed. Nothing automatic ever overwrites a lock.

## Review Focus

1. Laps answer `{"detail": "No results found."}` while the classification has times (Mexico FP3 on the day): the grid must come from the classification, not skip to FastF1. Pinned in Task 3.
2. OpenF1's live block in the middle of a lock attempt: `/snapshot/auto` answers `waiting`, not 502, and FastF1 isn't tried. Pinned in Task 1.
3. A classification car that isn't in the session's `/drivers` (Mexico's car 50) but is in another session of the meeting gets that name. One that's nowhere gets dropped. Pinned in Task 2.
4. A session where every classified `duration` is null (Madrid FP1 style) and laps are empty: not published yet, try later. Pinned in Task 3.
5. An old snapshot with no pool (every lock before this change): the Garage still works the old live way and `/weekend-team` doesn't change shape. Pinned in Task 4.

---

### Task 1: Read OpenF1's "no results" and live block answers properly

**Files:**
- Create: `tests/record_openf1_fixtures.py`, `tests/fixtures/openf1/` (recorded json)
- Modify: `src/openf1.py` (`_get`, exceptions), `src/fetch_practice.py` (`_openf1_then_fastf1` docstring only if needed)
- Test: `tests/test_openf1.py`, `tests/test_endpoints.py`

**Interfaces:**
- Produces: `class LiveBlocked(NotPublishedYet)` in `src/openf1.py`. `_get(path, params) -> list` returns `[]` when OpenF1 answers `{"detail": "No results found."}`, raises `LiveBlocked` when the detail starts with "Live F1 session in progress", and keeps raising `OpenF1Unavailable` for anything else.
- Produces: recorded fixtures, each a json list exactly as OpenF1 sent it:
  `mexico_fp3_session_result.json` (session 11399), `mexico_fp3_drivers.json` (11399, has 50 HIR),
  `mexico_fp2_drivers.json` (11398), `mexico_fp3_laps_best.json` (11399 laps trimmed to each
  driver's laps that have a time, plus a few null ones), `sq_session_result.json` (one 2026 sprint
  quali, list durations), `madrid_fp1_session_result.json` (whatever Madrid FP1 returns now),
  `monaco_fp2_drivers.json` (empty or whatever it returns now). Also two literal dicts in the test
  file for the "No results found." and live block answers (copy the live block text from the spec).

- [ ] **Step 1: Write `tests/record_openf1_fixtures.py`** like `tests/record_fixtures.py`: plain httpx GETs to `https://api.openf1.org/v1`, 1 second between calls, writes the files above. Session keys come from `/sessions?year=2026` matched on location and session name. Run it once (free, read only). Check the files are lists, not dicts.

- [ ] **Step 2: Write the failing tests** in `tests/test_openf1.py`, swapping `httpx.get` for a fake response object:

```python
def test_no_results_found_is_an_empty_list_not_openf1_down(...):
    assert of1._get("laps", {"session_key": 11399}) == []

def test_live_block_is_try_later_not_openf1_down(...):
    with pytest.raises(of1.LiveBlocked):
        of1._get("laps", {"session_key": 11399})
    assert issubclass(of1.LiveBlocked, of1.NotPublishedYet)

def test_other_odd_answers_still_mean_unavailable(...):
    with pytest.raises(of1.OpenF1Unavailable):
        of1._get("laps", {})    # e.g. {"detail": "something else"}

def test_practice_grid_doesnt_ask_fastf1_during_the_live_block(monkeypatch, no_schedule):
    # openf1_grid raises LiveBlocked -> get_practice_grid re-raises, FastF1 never called
```

  And in `tests/test_endpoints.py`, next to `test_snapshot_auto_states`:

```python
def test_snapshot_auto_waits_during_the_live_block(client, at, monkeypatch, empty_snapshots):
    # FP3 finished, openf1_grid raises LiveBlocked -> 200 with status "waiting"
```

- [ ] **Step 3: Run them, expect FAIL** (`LiveBlocked` doesn't exist, `_get` raises on the dict).
  Run: `./venv/Scripts/python.exe -m pytest -q tests/test_openf1.py tests/test_endpoints.py -k "no_results or live_block or odd_answers"`

- [ ] **Step 4: Implement** in `_get`: check the dict's `detail` before raising. `session_published` already turns `NotPublishedYet` into False and `_openf1_then_fastf1` already re-raises it, so `LiveBlocked` being a `NotPublishedYet` is what makes both behave. Comment why, in Ashen's voice, mentioning Mexico.

- [ ] **Step 5: Run the whole suite, expect PASS** (216 + new).
  Run: `./venv/Scripts/python.exe -m pytest -q`

- [ ] **Step 6: Commit** `src/openf1.py`, `tests/test_openf1.py`, `tests/test_endpoints.py`, `tests/record_openf1_fixtures.py`, `tests/fixtures/openf1/`.

### Task 2: Name drivers from the whole meeting

**Files:**
- Modify: `src/openf1.py` (`_laps_and_drivers`, `grid_from_openf1`, `practice_table`)
- Test: `tests/test_openf1.py`

**Interfaces:**
- Consumes: `_get` from Task 1, the Mexico drivers fixtures.
- Produces: `meeting_drivers(session: dict) -> list[dict]`: the session's own `/drivers`, plus any car number found only in `/drivers` of other sessions with the same `meeting_key` (sessions list from `_sessions(year)`). This session's entry wins when both have the number. Cached like `_sessions`.
- Produces: `grid_from_openf1(laps, drivers, race_name)` and `practice_table(laps, drivers)` no longer crash on an empty `drivers` list. Laps from a car with no name get dropped with a `print` saying which number. Same output columns as now.
- `_laps_and_drivers(key)` gets the session dict (or key plus session) so it can call `meeting_drivers`. Exact shape is the builder's call.

- [ ] **Step 1: Write the failing tests**

```python
def test_meeting_drivers_fill_in_a_car_missing_from_the_session():
    # session drivers = mexico_fp3_drivers minus car 50, other session has 50 HIR
    assert {"driver_number": 50, "name_acronym": "HIR"} items appear in result

def test_session_drivers_win_over_the_rest_of_the_meeting(): ...

def test_grid_with_empty_drivers_list_has_no_rows_instead_of_crashing():
    with pytest.raises(of1.NotPublishedYet):   # no named laps = nothing to rank yet
        of1.grid_from_openf1(LAPS, [], "x")

def test_grid_drops_a_car_nobody_can_name():
    grid = of1.grid_from_openf1(LAPS + [{"driver_number": 99, "lap_duration": 90.0}], DRIVERS, "x")
    assert 99 not in what's ranked and grid.iloc[0]["Abbreviation"] == "LEC"
```

- [ ] **Step 2: Run, expect FAIL** (`meeting_drivers` missing, KeyError on empty drivers).
- [ ] **Step 3: Implement.** Keep the merge on `driver_number`, just guard the empty frame and log the dropped numbers.
- [ ] **Step 4: Run the whole suite, expect PASS.**
- [ ] **Step 5: Re-run the scorecard** (`./venv/Scripts/python.exe scripts/scorecard.py`) and note PitWall's pts/race and the FP3 order's before and after. If they moved, write both numbers in `Fantasy Predictor/Decisions and evidence.md` with one line why. Read only network calls, free.
- [ ] **Step 6: Commit** `src/openf1.py`, `tests/test_openf1.py`, plus the notes file if it changed.

### Task 3: Classification backup, and the lock remembers where its order came from

**Files:**
- Modify: `src/openf1.py` (`openf1_grid`, new `grid_from_classification`), `src/weekend.py` (`build_snapshot`), `src/fetch_practice.py` (FastF1 grids get a source too)
- Test: `tests/test_openf1.py`, `tests/test_endpoints.py`

**Interfaces:**
- Consumes: `meeting_drivers` (Task 2), `_get` (Task 1).
- Produces: `grid_from_classification(results: list, drivers: list, race_name: str) -> pd.DataFrame`, same columns and maths as `grid_from_openf1` (rank by best time, `GapToPole`, `GapToTeammate`, `normalize_team_names`). Best time = `duration` when it's a number, the smallest non null item when it's a list. Rows with no time drop out. No named rows raises `NotPublishedYet`.
- Produces: `openf1_grid(...)` tries laps first. If laps have no timed laps (empty list or all null), it builds from `/session_result`. If neither has times, `NotPublishedYet`. Grids built from laps are cached as now. Grids built from the classification are NOT cached, so laps take over once they turn up.
- Produces: every grid carries `grid.attrs["lap_source"]` = `"laps"`, `"classification"` or `"fastf1"`. `build_snapshot` saves it as `snap["lap_source"]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_classification_grid_matches_mexico_fp3():
    grid = of1.grid_from_classification(mexico_fp3_session_result, mexico_fp3_drivers, "Mexico City Grand Prix")
    assert list(grid["Abbreviation"][:5]) == ["NOR", "ANT", "LEC", "PIA", "VER"]
    assert grid.iloc[1]["GapToPole"] == pytest.approx(0.001, abs=1e-6)
    assert "PER" not in set(grid["Abbreviation"])        # no time, drops out
    assert "HIR" in set(grid["Abbreviation"])            # car 50, named from the fixture
    assert list(grid.columns) == the same columns grid_from_openf1 gives

def test_classification_grid_takes_the_best_part_of_sprint_quali(): ...   # sq_session_result fixture

def test_openf1_grid_falls_back_to_the_classification_when_laps_say_no_results(fake_openf1):
    # fake_get returns [] for laps, the Mexico classification for session_result
    grid = of1.openf1_grid(...)
    assert grid.attrs["lap_source"] == "classification"

def test_classification_grid_is_not_cached_so_laps_can_take_over(fake_openf1): ...

def test_nothing_anywhere_is_not_published_yet(fake_openf1):
    # laps [] and every duration null (madrid style) -> NotPublishedYet

def test_snapshot_records_where_its_order_came_from(client, monkeypatch):
    # build_snapshot with a grid whose attrs say "classification" -> snap["lap_source"] == "classification"
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** Make sure `predict_upcoming_race` or a `.copy()` doesn't lose `attrs` before `build_snapshot` reads it: read `lap_source` straight off the grid `load_grid` returned. Add `"fastf1"` in the FastF1 builders in `src/fetch_practice.py`.
- [ ] **Step 4: Run the whole suite, expect PASS.** Golden files must not change.
- [ ] **Step 5: Commit** `src/openf1.py`, `src/weekend.py`, `src/fetch_practice.py`, the two test files.

### Task 4: The lock saves the full forecast, the Garage reads it

**Files:**
- Modify: `src/weekend.py` (`build_snapshot`), `src/api/planner.py`, `src/api/teams.py` (`get_chip_advisor`)
- Test: `tests/test_endpoints.py`

**Interfaces:**
- Consumes: `build_snapshot` from Task 3.
- Produces: new snapshot keys. `snap["pool"]` = the `get_race_pool` result with confidence attached to `pool["drivers"]` (`attach_confidence(pool["drivers"], conf)`), `snap["optimal_score"]` and `snap["limitless_score"]` (the numbers the chips already compare against).
- Produces: `/transfer-ladder`: when `find_snapshot(race)` has `"pool"`, use it and `snap["session_used"]`, `provisional: False`, no practice data loaded at all. Otherwise exactly today's code.
- Produces: `/chip-advisor`: same rule with `snap["pool"]`, `optimal_score`, `limitless_score`. With no pooled snapshot it loads practice through `weekend_grid(race, wanted)` with `wanted` worked out like the planner does (lock session, else SQ on sprint weekends, else FP3) instead of the hard coded FP3.
- `/weekend-team` and `/last-team` don't send the pool (they build their payload by hand already, the test just pins it).

- [ ] **Step 1: Write the failing tests**

```python
def test_snapshot_saves_the_pool_and_chip_scores(client): ...
    # build_snapshot(...) -> "pool" with drivers and constructors, each driver has FantasyValue, Price, confidence key

def test_transfer_ladder_reads_the_locked_pool_without_practice_data(client, snapshots, monkeypatch):
    # write a snapshot with a pool, make weekend_grid / first_available_practice fail if called
    # -> 200, provisional False, keep row expected matches the pool's numbers by hand

def test_chip_advisor_reads_the_locked_pool_without_practice_data(client, snapshots, monkeypatch): ...

def test_old_snapshot_without_a_pool_still_works_live(client, snapshots):
    # the existing Madring snapshots have no pool -> ladder and chips answer like before (goldens unchanged)

def test_weekend_team_doesnt_send_the_pool(client, at, snapshots): ...
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** In `build_snapshot`, reuse the `pool`, `optimal_score` and `limitless_score` it already works out for the chips, and attach confidence after `conf` is known.
- [ ] **Step 4: Run the whole suite, expect PASS.** `chip_advisor_madring.json` golden must not change.
- [ ] **Step 5: Commit** `src/weekend.py`, `src/api/planner.py`, `src/api/teams.py`, `tests/test_endpoints.py`.

### Task 5: Lock Action that stays awake, and `/health`

**Files:**
- Modify: `.github/workflows/lock-snapshot.yml`, `main.py`
- Test: `tests/test_endpoints.py`

**Interfaces:**
- Produces: `GET` and `HEAD` `/health` answering 200 `{"status": "ok"}` straight away, no data loaded (`@app.api_route("/health", methods=["GET", "HEAD"])`).
- Produces: the workflow. Starts: `"0 0,6,12,18 * * 5,6"` and `"0 0,6 * * 0"` (UTC) plus `workflow_dispatch`. `concurrency: { group: lock-snapshot, cancel-in-progress: false }`. `timeout-minutes: 355`. One bash step that loops until 345 minutes have passed: POST `/snapshot/auto` (same curl as now, `--max-time 180 --retry 3`), append the answer to the run summary, then:
  - `status` is `already_locked`, `idle` or `refused`: stop, green.
  - 401: stop, red, same message as now.
  - `waiting`, `locked`, any 5xx or `000`: sleep 300 and go again.
  - Out of time: stop green with a summary line saying it ran out of time still waiting.

- [ ] **Step 1: Write the failing test**

```python
def test_health_answers_get_and_head(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.head("/health").status_code == 200
```

- [ ] **Step 2: Run, expect FAIL** (404).
- [ ] **Step 3: Implement `/health` in `main.py`.** Update the comment block at the top of the workflow to say why it loops now (GitHub ran the 30 minute timer every 4 to 6 hours on Mexico weekend, and OpenF1 only gives us about 90 minutes between FP3 and the quali block).
- [ ] **Step 4: Run the whole suite, expect PASS.** Check the workflow is valid YAML: `./venv/Scripts/python.exe -c "import yaml,sys;yaml.safe_load(open('.github/workflows/lock-snapshot.yml'))"`. Lint the bash part by reading it once more for the exit paths above.
- [ ] **Step 5: Commit** `main.py`, `.github/workflows/lock-snapshot.yml`, `tests/test_endpoints.py`.
- [ ] **Step 6: After Ashen pushes,** he presses Run workflow once. Brazil is under 5 days away so it should answer `waiting` every 5 minutes. Check the run summary shows that, then he can cancel it (or leave it, it stops by itself).

### Task 6: `lock_team.py` dry run, notes, and the uptime checker

**Files:**
- Modify: `scripts/lock_team.py`, `Fantasy Predictor/How-tos.md`, `Fantasy Predictor/README.md`, `Fantasy Predictor/Gotchas.md`, `Fantasy Predictor/Race weekend flow.md`, `Fantasy Predictor/Snapshots.md`, `Fantasy Predictor/API.md`, `Fantasy Predictor/Roadmap.md`

**Interfaces:**
- Consumes: everything above.
- Produces: `python scripts/lock_team.py --dry-run [--race "..."]` builds and prints the 3 teams, each team's 2x, the predicted finish and `lap_source`, and saves nothing. Without `--dry-run` it saves as now with `source: "manual"` and `note: "locked by hand with scripts/lock_team.py"`. `--force` unchanged.

- [ ] **Step 1: Add `--dry-run` and the note.** Check it by hand: `./venv/Scripts/python.exe scripts/lock_team.py --dry-run --race "Sao Paulo Grand Prix"` should say FP3 isn't out yet (Brazil hasn't run), and `git status` shows nothing new in `data/snapshots/`. Use the exact event name from the schedule (it prints with an accent).
- [ ] **Step 2: Notes.** How-tos (dry run first, then save, then commit), Gotchas (OpenF1's live block, late laps, stand-ins like HIR, GitHub's late timers, "No results found." being a dict), Race weekend flow (the loop and the classification backup), Snapshots (`pool`, `lap_source`, `optimal_score`, `limitless_score`), API (`/health`, Garage reads the lock), README "where things stand", Roadmap (this done, the later items from the spec's non goals). Run `tests/test_no_dashes.py`.
- [ ] **Step 3: Full check.** `./venv/Scripts/python.exe -m pytest -q`, `cd frontend && npm test && npm run build && npm run lint` (4 old errors only).
- [ ] **Step 4: Commit** the script and notes.
- [ ] **Step 5: Ashen sets up the uptime checker** (UptimeRobot or cron-job.org, his account) on `https://formula-1-fantasy-predictor.onrender.com/health` every 5 minutes, once Task 5 is live. Check a few minutes later that `/health` answers fast, and look at Render's free hours in a week.
