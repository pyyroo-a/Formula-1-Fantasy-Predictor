# Confidence and reasons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every driver pick on the 3 teams, the 2x pick and the planner's swaps shows a HIGH / MEDIUM / LOW confidence level with a plain reason, and a low confidence top 3 driver's SAFE tag reads CONSIDER, without changing any picks.

**Architecture:** One plain module, `src/confidence.py`, works out each driver's level and reason from the weekend's practice grids (the ones PitWall already loads). The API and the snapshot lock attach it to the driver dicts after the teams are built, so the picks can't change. A script in `scripts/` proves the levels are honest on past weekends before anything shows on the site. The React cards just read the new fields.

**Tech Stack:** Python 3 / pandas / FastAPI / pytest, React + Tailwind (Vite).

**Spec:** `docs/superpowers/specs/2026-10-28-confidence-and-reasons-design.md`

## Global Constraints

- Cutoffs, exactly: flagged if more than 2 places from the teammate (`> 2`), rank spread above 1.5 (`> 1.5`, sample std, `ddof=1`), under 0.05s to the nearest car (`< 0.05`).
- Levels: 0 flags = `"high"`, 1 = `"medium"`, 2 or more = `"low"`. A check that can't be worked out counts as passed and the reason says so.
- It never changes picks: teams, 2x, planner rows and `PickCategory` stay exactly as they are. CONSIDER is display only.
- No confidence on provisional previews (session used is not the lock session), on old snapshots, or on sprint weekends unless `SHOW_ON_SPRINT_WEEKENDS` is switched on by Task 2's result. Missing confidence = the card looks like today.
- Ashen commits and pushes, never Claude. Each task ends with the files to tick in GitHub Desktop, a Summary and a Description, then wait for "committed".
- Tests: `./venv/Scripts/python.exe -m pytest -q` (155 passing before this project). No em or en dashes anywhere (`tests/test_no_dashes.py`).
- Comments and notes in Ashen's plain casual voice. Data true: never tune the cutoffs to make Task 2 look better.
- No backend pushes from FP1 Friday until the race is over (Mexico FP1 is Friday 2026-10-30).

## Review Focus

- An earlier session (FP1 or FP2) fails to load: the level is worked out from the sessions that did load, and the lock or the page never breaks. Test in Task 1 (`test_load_skips_a_failed_earlier_session`) and Task 3 (`test_confidence_failure_never_breaks_the_weekend`).
- A driver in the pool or a team who isn't in the lock session's grid: no label, no crash. Test in Task 1 (`test_attach_leaves_unknown_drivers_without_a_label`).
- A team with a stand in or only one car with a time in the lock session: the teammate check counts as passed and says "no teammate time". Test in Task 1 (`test_missing_checks_count_as_passed`).
- An old snapshot (no confidence fields) still renders exactly as today. Covered by the existing `test_old_snapshot_without_ownership_still_serves` plus the frontend guard in Task 4.
- Two cars on exactly the same time (gap 0.000) count as a tight pack. Test in Task 1 (`test_identical_times_are_a_tight_pack`).

---

### Task 1: The confidence module

**Files:**
- Create: `src/confidence.py`
- Test: `tests/test_confidence.py`

**Interfaces:**
- Consumes: practice grids as returned by `load_grid` / `get_practice_grid` (columns `Abbreviation`, `TeamName`, `GridPosition`, `GapToPole`).
- Produces:
  - constants `MATE_PLACES = 2`, `SPREAD_LIMIT = 1.5`, `PACK_GAP_S = 0.05`, `SHOW_ON_SPRINT_WEEKENDS = False`
  - `sessions_for(lock_session: str) -> list[str]`: `"SQ"` gives `["FP1", "SQ"]`, `"FP3"` gives `["FP1", "FP2", "FP3"]`
  - `load_weekend_sessions(load: Callable[[str], pd.DataFrame], lock_session: str) -> dict[str, pd.DataFrame]`
  - `weekend_confidence(sessions: dict[str, pd.DataFrame], lock_session: str) -> dict[str, dict]`, each value `{"level": str, "flags": int, "reason": str}`
  - `attach_confidence(drivers: list[dict], conf: dict | None) -> list[dict]`, adds `"Confidence"` and `"ConfidenceReason"` (both `None` when unknown), returns new dicts
  - `attach_to_teams(teams: list[dict], conf: dict | None) -> list[dict]`, does each team's `drivers` and its `boost_pick`

- [ ] **Step 1: Write the failing tests** in `tests/test_confidence.py`. Build small grids by hand with a helper `_grid(rows)` taking `(abbr, team, gap_to_pole)` tuples in finishing order (`GridPosition` = order). Use these exact cases (real Austin FP3 shapes):

```python
def test_clean_driver_is_high():
    # LEC P1, HAM P2 (0.083 behind), steady P1/P2/P1 over the weekend
    conf = weekend_confidence(sessions, "FP3")
    assert conf["LEC"]["level"] == "high" and conf["LEC"]["flags"] == 0
    assert conf["LEC"]["reason"] == ("P1 in FP3. Teammate HAM P2 backs it up, "
                                     "steady all weekend and 0.083s clear of the next car.")

def test_three_flags_is_low():
    # VER P4 in FP3, HAD P10, VER was P2 in FP1 and P5 in FP2 (std 1.528), 0.046s to the nearest car
    assert conf["VER"]["level"] == "low" and conf["VER"]["flags"] == 3
    assert conf["VER"]["reason"] == ("P4 in FP3. But teammate HAD was P10, moved around between "
                                     "sessions (P2 to P5) and only 0.046s from the next car.")

def test_one_flag_is_medium(): ...            # only the teammate check fails -> "medium",
                                              # reason has both a positive part and a "But" part
def test_teammate_exactly_2_places_passes(): ...   # P5 and P7 -> no teammate flag
def test_spread_uses_sample_std():
    # two sessions, ranks 1 and 3 -> std 1.414, passes; ranks 1 and 4 -> 2.121, flagged
def test_p1_and_last_use_their_only_neighbour(): ...
def test_gap_of_exactly_005_passes(): ...      # GapToPole 0.000 and 0.050 -> not flagged
def test_identical_times_are_a_tight_pack(): ...    # two cars on the same GapToPole -> flagged
def test_missing_checks_count_as_passed():
    # one session only, driver's teammate has no time -> "high", reason ends
    # "Couldn't check: no teammate time and only one session so far."
def test_sprint_lock_session_label():
    # lock_session "SQ" -> reason starts "P3 in sprint quali."
def test_attach_adds_fields_without_touching_the_input(): ...
def test_attach_leaves_unknown_drivers_without_a_label():
    # driver not in conf -> Confidence None, ConfidenceReason None; conf None -> same for all
def test_attach_to_teams_covers_the_boost_pick(): ...
def test_load_skips_a_failed_earlier_session():
    # load raises for "FP2" -> result has FP1 and FP3 only
def test_load_raises_if_the_lock_session_fails(): ...
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `./venv/Scripts/python.exe -m pytest tests/test_confidence.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'src.confidence'`

- [ ] **Step 3: Implement `src/confidence.py`** with the interfaces above. The rules (copy these, they're what the brainstorm numbers came from):
  - Rank in a session = `GridPosition` (already the fastest lap rank among drivers with a time).
  - Teammate: the other driver with the same `TeamName` in the lock session. Exactly one other, else unknown ("no teammate time"). Flag if `abs(rank - mate_rank) > MATE_PLACES`.
  - Spread: the driver's ranks in every loaded session they appear in. Fewer than 2, unknown ("only one session so far"). Flag if `pd.Series(ranks).std() > SPREAD_LIMIT`.
  - Tight pack: lap gaps from `GapToPole` to the car directly ahead and behind in the lock session, take the smaller, or the only one at P1 / last. No neighbour at all, unknown ("no other car to compare"). Flag if `gap < PACK_GAP_S`.
  - Reason: `f"P{rank} in {label}."`, where `label` is `"sprint quali"` for `"SQ"` and the session name otherwise. Then, if any passed: `" " + capitalised(join(passed)) + "."`. If any flagged: `" But " + join(flagged) + "."`. If any unknown: `" Couldn't check: " + join(unknown) + "."`. `join` gives `"a"`, `"a and b"`, `"a, b and c"`. Passed phrases: `"teammate {T} P{r} backs it up"`, `"steady all weekend"`, `"{gap:.3f}s clear of the next car"`. Flagged phrases: `"teammate {T} was P{r}"`, `"moved around between sessions (P{lo} to P{hi})"`, `"only {gap:.3f}s from the next car"`. Order: teammate, spread, pack.
  - Comment the constants with the evidence (12 FP3 weekends, high 3.06 / medium 3.46 / low 4.56 places off on fantasy points, high beat low 10 of 12), in Ashen's voice.

- [ ] **Step 4: Run the tests**

Run: `./venv/Scripts/python.exe -m pytest tests/test_confidence.py -q` then the whole suite `./venv/Scripts/python.exe -m pytest -q`
Expected: all pass (155 + the new ones).

- [ ] **Step 5: Hand Ashen the commit** (`src/confidence.py`, `tests/test_confidence.py`, plus the spec and this plan if he hasn't committed them yet), with a Summary and a Description. Wait for "committed".

### Task 2: Prove it on past weekends (stop point)

**Files:**
- Create: `scripts/confidence_grade.py`
- Test: `tests/test_confidence_grade.py` (load the script with `importlib.util` like `tests/test_scorecard.py` does)
- Output: `archive/results/confidence_rows_2026.csv` (the per driver rows, so re-runs and the notes can point at them)

**Interfaces:**
- Consumes: `load_weekend_sessions`, `weekend_confidence`, `sessions_for` (Task 1); `load_grid` (`src/weekend.py`); `is_sprint_weekend` (`src/fetch_practice.py`); `data/processed/race_results_2026.csv`; `data/official_points_2026.json` (`[round]["drivers"][abbr]["points"]`).
- Produces: `places_off(rows: pd.DataFrame, target: str, ascending: bool, finishers_only: bool = False) -> pd.Series` and `summarise(rows: pd.DataFrame) -> dict` (per level: `n`, `fpts_off`, `within2`, `finish_off`, `grid_off`; plus `high_beat_low` and `rounds`).

- [ ] **Step 1: Write the failing tests**

```python
def test_places_off_reranks_within_each_round():
    # 2 rounds, 3 drivers each, known lock ranks and fantasy points -> exact places off
def test_places_off_can_skip_non_finishers():
    # Status "Retired" row is dropped and the rest re-ranked before comparing
def test_summarise_counts_rounds_where_high_beat_low(): ...
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `./venv/Scripts/python.exe -m pytest tests/test_confidence_grade.py -q`
Expected: FAIL (script missing).

- [ ] **Step 3: Implement the script.** For every round in `race_results_2026.csv` that has official points: lock session `"SQ"` on sprint weekends, `"FP3"` otherwise; load sessions with `load_weekend_sessions(lambda s: load_grid(race, s, 2026), lock)`; one row per driver in the lock grid with `round`, `kind` (`"normal"` / `"sprint"`), `rank`, `level`, `grid`, `finish`, `status`, `fpts`. Error = places between the lock rank and the target rank, both re-ranked among that round's rows that have the target. Finishers = `Status` starting `"Finished"` or `"+"`, or `"Lapped"`. Write the CSV, print one markdown table per kind (level, driver weekends, places off on fantasy points, within 2 places, places off on finish, places off on grid) and "high beat low on fantasy points in X of Y weekends". A session that won't load gets skipped and printed, never faked.

- [ ] **Step 4: Run tests, then the script**

Run: `./venv/Scripts/python.exe -m pytest tests/test_confidence_grade.py -q` (PASS), then `./venv/Scripts/python.exe scripts/confidence_grade.py`
Expected: normal weekends close to high 3.06 / medium 3.46 / low 4.56 places off on fantasy points and high beating low on about 10 of 12.

- [ ] **Step 5: STOP and show Ashen the numbers.**
  - Normal weekends way off the brainstorm numbers, or high not beating low on most weekends: stop and find out why with Ashen before anything else. No cutoff tuning.
  - Sprint weekends: if high beats low on fantasy points on most sprint weekends and on average, ask Ashen to switch `SHOW_ON_SPRINT_WEEKENDS = True` (with the numbers in its comment). Otherwise it stays off and the comment says why.

- [ ] **Step 6: Hand Ashen the commit** (`scripts/confidence_grade.py`, `tests/test_confidence_grade.py`, `archive/results/confidence_rows_2026.csv`, `src/confidence.py` if the switch changed). Wait for "committed".

### Task 3: Wire it into the weekend, the lock and the planner

**Files:**
- Modify: `src/weekend.py` (new helper, and `build_snapshot`), `src/api/race_weekend.py` (live teams), `src/api/planner.py` (pool), `src/planner.py` (`transfer_ladder` swaps)
- Test: `tests/test_endpoints.py`
- Goldens: re-record only what this changes (expected: `weekend_team_provisional.json`)

**Interfaces:**
- Consumes: Task 1's `load_weekend_sessions`, `weekend_confidence`, `attach_to_teams`, `attach_confidence`, `SHOW_ON_SPRINT_WEEKENDS`.
- Produces:
  - `weekend_confidence_for(race_name: str, session_used: str | None, lock_session: str, year: int = SEASON) -> dict | None` in `src/weekend.py`. `None` when `session_used != lock_session`, when `lock_session == "SQ"` and the sprint switch is off, or when anything inside fails (print it, never raise).
  - Team drivers and `boost_pick` in `/weekend-team` and in new snapshots carry `Confidence` and `ConfidenceReason`.
  - Each driver swap in `/transfer-ladder` rows carries `in_confidence` and `in_confidence_reason` (the incoming driver's, `None` if unknown). Constructor swaps don't get them.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_endpoints.py
def test_weekend_team_shows_confidence_once_the_lock_session_is_in(client, at, empty_snapshots):
    at(SAT_MADRING_BEFORE_QUALI)
    body = client.get("/weekend-team").json()
    for team in body["teams"]:
        for d in team["drivers"]:
            assert d["Confidence"] in ("high", "medium", "low")
            assert d["ConfidenceReason"].startswith(f"P{d['GridPosition']} in FP3.")
        assert team["boost_pick"]["Confidence"] in ("high", "medium", "low")

def test_no_confidence_on_an_earlier_session_preview(client, at, empty_snapshots):
    at(SAT_MADRING_FP3_RUNNING)   # FP3 not over, so the preview is FP2
    body = client.get("/weekend-team").json()
    assert all(d.get("Confidence") is None for t in body["teams"] for d in t["drivers"])

def test_snapshot_saves_confidence_at_the_lock(client): ...   # build_snapshot(_madring_event(), ...)
def test_confidence_failure_never_breaks_the_weekend(client, at, empty_snapshots, monkeypatch):
    # monkeypatch src.confidence.weekend_confidence to raise -> /weekend-team still 200, no labels
def test_transfer_ladder_swaps_carry_the_incoming_drivers_confidence(client, snapshots): ...

def test_sprint_weekends_get_no_confidence_while_switched_off():
    assert weekend_confidence_for("Singapore Grand Prix", "SQ", "SQ") is None
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `./venv/Scripts/python.exe -m pytest tests/test_endpoints.py -q`
Expected: the new tests FAIL (no `Confidence` key / no helper).

- [ ] **Step 3: Implement.** In `build_snapshot` and the live path of `race_weekend.py`, call `weekend_confidence_for` after the teams are built and pass the teams through `attach_to_teams`. In `src/api/planner.py`, attach to `pool["drivers"]` (only when `session_used` is the session the ladder wanted), then `transfer_ladder` adds the two swap fields from the pool driver. Nothing that builds or scores a team reads the new fields.

- [ ] **Step 4: Run the whole suite, re-record the goldens it changes, check the diff**

Run: `UPDATE_GOLDEN=1 ./venv/Scripts/python.exe -m pytest -q`, then `git diff --stat tests/golden` and `git diff tests/golden`
Expected: only `Confidence` / `ConfidenceReason` lines added, no other number moved. Then `./venv/Scripts/python.exe -m pytest -q` passes without `UPDATE_GOLDEN`.

- [ ] **Step 5: Hand Ashen the commit** (the 4 source files, `tests/test_endpoints.py`, the re-recorded goldens). Remind him: backend push only Monday to Thursday. Wait for "committed".

### Task 4: The cards

**Files:**
- Modify: `frontend/src/components/BudgetTeam.jsx` (`BudgetDriverCard`, `BoostPickCard`, new `ConfidencePill`, new `displayCategory`), `frontend/src/components/Overview.jsx` (the main page's own driver rows, around line 95), `frontend/src/components/myteam/TransferPlanner.jsx` (swap lines, around line 96)

**Interfaces:**
- Consumes: `Confidence`, `ConfidenceReason` on drivers and `boost_pick`; `in_confidence`, `in_confidence_reason` on driver swaps (Task 3).
- Produces: `ConfidencePill({ level })` and `displayCategory(driver) -> string` exported from `BudgetTeam.jsx`. `displayCategory` returns `"Consider"` when `PickCategory === "Safe"` and `Confidence === "low"`, otherwise `PickCategory`.

- [ ] **Step 1: Build it like mockup option A** (`.superpowers/brainstorm/1556-1793191297/content/confidence-cards-v2.html`): pill text `HIGH CONFIDENCE` / `MEDIUM CONFIDENCE` / `LOW CONFIDENCE` next to the name (green / amber / red from the existing `pw-` colours), the reason on its own line under the name, the tag from `displayCategory` with a `Consider` badge style (amber, distinct from Risk). One legend line above the team list and above the planner ladder, shown only when some driver has a level: "Confidence = how much to trust a driver's practice spot. It's never a guarantee." No `Confidence` field: render exactly as today.

- [ ] **Step 2: Lint and build**

Run (in `frontend/`): `npm run lint` then `npm run build`
Expected: no errors.

- [ ] **Step 3: Look at it for real.** Copy `data/snapshots` to a scratch folder, build a fresh R18 snapshot into it (`SNAPSHOT_DIR=<scratch> ./venv/Scripts/python.exe scripts/lock_team.py --race "United States Grand Prix" --force`), run the backend with that `SNAPSHOT_DIR` and the frontend dev server, open the main page and the planner in the browser pane and screenshot both. Never touch the real `data/snapshots`. Show Ashen.

- [ ] **Step 4: Hand Ashen the commit** (the 3 jsx files). Frontend only, so it can go any day. Wait for "committed".

### Task 5: Notes and the final review

**Files:**
- Modify: `Fantasy Predictor/Model.md`, `Decisions and evidence.md`, `Roadmap.md`, `README.md`, `API.md`, `Frontend.md`

- [ ] **Step 1: Notes.** Decisions and evidence: the ideal lap and long run checks (tried and dropped, numbers from the spec) and Task 2's real numbers. Model: the confidence section and the known weak spot line about sectors updated. Roadmap: project 4 done, move ideal lap / long runs to closed, add the open task "re-run `scripts/confidence_grade.py` after a few races from Mexico", and "letting confidence steer the 2x" to banked ideas. README: where things stand and the test count. API and Frontend: the new fields and components.

- [ ] **Step 2: Full check**

Run: `./venv/Scripts/python.exe -m pytest -q`
Expected: all pass, including `test_no_dashes.py`.

- [ ] **Step 3: One fresh reviewer** (most capable model) on everything this project changed, against the spec. Fix what holds up, re-run the tests.

- [ ] **Step 4: Hand Ashen the commit** (notes plus any review fixes). Wait for "committed".
