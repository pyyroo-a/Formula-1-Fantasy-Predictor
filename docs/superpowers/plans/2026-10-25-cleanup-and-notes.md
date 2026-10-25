# PitWall cleanup and Fantasy Predictor vault: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Same predictions and same website, but with a test suite that passes, one team scoring path, no leftovers, no dashes, smaller files, and an Obsidian vault that explains the project.

**Architecture:** Behaviour-preserving refactor guarded by the golden tests (`tests/golden/*.json`, compared in `tests/conftest.py::golden`). Fix the stale goldens first, prove they're data-only, then keep all tests green after every task. The vault is plain markdown in `Fantasy Predictor/`, linted with the obsidian-notes plugin.

**Tech Stack:** Python 3.13, FastAPI, pandas, pytest (backend on Render via Docker). React 19 + Vite + Tailwind (frontend on Vercel). Obsidian.

**Spec:** `docs/superpowers/specs/2026-10-25-cleanup-and-notes-design.md`

## Global Constraints

- Never `git commit` or `git push`. Every "Commit" step means: hand Ashen the files to tick in GitHub Desktop, a Summary and a Description, then wait for "committed" before the next task.
- Tests: `./venv/Scripts/python.exe -m pytest -q` from the repo root (the venv doesn't stay activated between shell calls). After Task 1 the suite must be fully green at the end of every task.
- No prediction changes. The only golden re-records allowed after Task 1 are the text-only ones in Task 4.
- No backend pushes from Friday FP1 until the race is over. Backend commits go out Monday to Thursday (Mexico FP1 is Friday 2026-10-30).
- No em dashes (U+2014) or en dashes (U+2013) anywhere written or touched. Casual plain voice in comments, notes and commit text.
- Free hosting and data only. No new dependencies.
- Routes, URLs, request and response shapes stay identical.
- Before deleting or moving a file, grep for it in `Dockerfile`, `.dockerignore`, `.github/workflows/`, `main.py`, `src/`, `scripts/`, `frontend/src/`, `frontend/index.html`.

## Review Focus

- **Render boots after the backend split.** `python -c "import main"` and a local `uvicorn main:app` must work, and every route in `main.py` must still be registered. Owned by Task 5 (route list test).
- **`/snapshot/auto` still reports the last build result after the split.** `_last_snapshot_result` is reassigned with `global`, so a `from x import _last_snapshot_result` copy would freeze it at `{}`. Owned by Task 5 (characterisation test written before the move).
- **The Avoid quirk doesn't get "fixed" by accident.** Goldens only show the 2 chosen constructors per team, so a changed constructor score for an unchosen team can slip through. Owned by Task 2 (direct test).
- **Switching tabs keeps your selections.** Today all tab state lives in `App`, so switching from Practice to Qualifying and back keeps the chosen race. Moving state into tab components would reset it. Owned by Task 6 (state stays in hooks called from `App`, checked by hand).
- **Files keep their UTF-8 encoding on Windows.** Bulk dash replacement must not add a BOM or re-encode, or the site shows garbled text again. Owned by Task 4 (dash scan test reads every file as strict UTF-8).

---

### Task 1: Prove the stale goldens are data-only, then re-record them

**Files:**
- Modify: the 11 stale files in `tests/golden/` (re-recorded, not hand-edited)

**Interfaces:**
- Produces: a fully green suite (74 passed) that every later task keeps green.

- [ ] **Step 1: Copy HEAD's code with the old data into the scratchpad**

```bash
CHECK="$SCRATCH/golden-check"   # $SCRATCH = this session's scratchpad dir
mkdir -p "$CHECK" && git archive HEAD | tar -x -C "$CHECK"
for f in $(git ls-tree --name-only ede3bef data/processed/); do git show "ede3bef:$f" > "$CHECK/$f"; done
cmd //c mklink //J "$(cygpath -w "$CHECK/data/cache")" "$(cygpath -w "$PWD/data/cache")"
```

ede3bef is where the goldens were last recorded. This leaves Ashen's working tree alone.

- [ ] **Step 2: Run the suite there with the old data**

Run: `cd "$CHECK" && "<repo>/venv/Scripts/python.exe" -m pytest -q`
Expected: 74 passed. That proves today's code gives the recorded answers on the recorded data, so the 11 failures are caused by the new race data only.
If anything fails: STOP. Show Ashen which goldens moved and the diff, don't re-record.

- [ ] **Step 3: Stop `waiting_before_fp3` from rotting**

It's one of the 11, and not for a harmless reason: Baku's results landed, so the endpoint now answers `refused` and a plain re-record would turn the "waiting" test into a second "refused" test (same rot as the Singapore self-lock test). In `test_snapshot_auto_states` (`tests/test_endpoints.py` ~171), for that case only, make the race look unraced:

```python
    if name == "waiting_before_fp3":
        # Baku's results are in the data now, pretend they aren't so this keeps testing "waiting"
        monkeypatch.setattr(race_weekend, "results_already_in_data", lambda race: False)
```

(`import src.api.race_weekend as race_weekend` at the top. Task 5 moves this target to `weekend_lock`.)

- [ ] **Step 4: Re-record in the real repo and look at the diff**

Run: `UPDATE_GOLDEN=1 ./venv/Scripts/python.exe -m pytest -q`, then `git diff --stat tests/golden`
Expected: only the stale goldens change, and `snapshot_auto_waiting_before_fp3.json` doesn't change at all. Skim each diff for new rounds, new results, shifted predictions from more training data. Also check every re-recorded golden still shows the state its name says (provisional is still provisional, and so on). If one flipped, treat it like Step 3 and tell Ashen.

- [ ] **Step 5: Normal run**

Run: `./venv/Scripts/python.exe -m pytest -q`
Expected: `74 passed`

- [ ] **Step 6: Clean up and commit**

Remove the junction first (`cmd //c rmdir "<check>\data\cache"`, which only removes the link), then delete `$CHECK`. Hand Ashen: the re-recorded golden files and `tests/test_endpoints.py`. Summary `re-recorded the golden tests for the new race data`. Description: they were recorded at ede3bef and every race since added data, checked by running today's code on the old data (74/74), so nothing in the logic moved. The "waiting for FP3" test now pretends Baku is unraced so new results can't quietly turn it into a different test.

---

### Task 2: One team scoring path in `src/fantasy.py`

**Files:**
- Modify: `src/fantasy.py` (`build_budget_team` ~368-507, `build_budget_teams` ~510-685, `get_race_pool` ~688-749, delete `evaluate_fantasy_picks` ~752-end)
- Test: `tests/test_helpers.py`

**Interfaces:**
- Produces (all private to `src/fantasy.py`, the public functions keep their signatures):
  - `_priced_race_table(fantasy_table, race_name, prices, dnf_probs=None, dnf_weight=DNF_WEIGHT) -> tuple[pd.DataFrame, set[str]]`: race rows filtered, `calculate_fantasy_score`, `GridGap`, `Price` mapped, unpriced dropped, `PickCategory` set (Safe = 3 lowest Predicted, Value >= 75th pct, Avoid <= 25th pct, else Risk). Returns `(race_df, safe_abbrevs)`. Avoid rows are NOT dropped here.
  - `_constructor_scores(race_df, constructor_prices, *, drop_avoid: bool, with_bonus: bool) -> dict[str, float]`: per constructor in `constructor_prices`, sum of `FantasyValue`, plus the existing Q2/Q3 and top-team bonus when `with_bonus`, rounded to 3. With `drop_avoid`, Avoid rows are removed before EVERYTHING (sums, grids, team average), which is today's team-builder behaviour.
  - `_driver_out(d: dict, with_dnf: bool) -> dict`: the driver dict the API returns. `with_dnf=False` omits `DNFProb` (that's what `build_budget_team` returns today).
- Callers: `build_budget_team` and `build_budget_teams` use `drop_avoid=True, with_bonus=True`. `get_race_pool` uses `drop_avoid=False, with_bonus=False`. `_team_risk` and the combination loops stay where they are.
- `src/fantasy.py` itself doesn't get split in this plan. It drops by about 100 lines here, its functions are imported from 6 files, and the planner (project 3) will reshape the team builders anyway, so a split now would only get redone.

- [ ] **Step 1: Write the quirk-pinning test**

```python
def test_constructor_scores_keep_the_avoid_quirk_for_now():
    # the team builders drop Avoid drivers before adding up constructors, the pool
    # doesn't. project 2 fixes this with measurement, the cleanup must not move it
    df = pd.DataFrame({
        "TeamName": ["Cadillac", "Cadillac", "Ferrari", "Ferrari"],
        "Abbreviation": ["PER", "BOT", "LEC", "HAM"],
        "FantasyValue": [-5.1, -3.7, 38.0, 29.7],
        "PickCategory": ["Avoid", "Risk", "Safe", "Safe"],
        "GridPosition": [21, 22, 1, 2],
    })
    prices = {"Cadillac": 3.0, "Ferrari": 28.2}
    builder = fantasy._constructor_scores(df, prices, drop_avoid=True, with_bonus=True)
    pool = fantasy._constructor_scores(df, prices, drop_avoid=False, with_bonus=False)
    assert builder["Cadillac"] == pytest.approx(-3.7)   # Bottas only, one car so no Q bonus
    assert pool["Cadillac"] == pytest.approx(-8.8)
    assert builder["Ferrari"] == pytest.approx(70.7)    # both in Q3: +3, no TeamAvgPosition: +0
    assert pool["Ferrari"] == pytest.approx(67.7)
```

(`import src.fantasy as fantasy` at the top of the test file if it isn't there.)

- [ ] **Step 2: Run it, expect FAIL**

Run: `./venv/Scripts/python.exe -m pytest tests/test_helpers.py -q -k avoid_quirk`
Expected: FAIL, `_constructor_scores` doesn't exist.

- [ ] **Step 3: Add the three helpers and switch the three callers to them**

Keep each caller's exact output keys (constructors from `build_budget_teams` still carry `dnf_risk` and `double_dnf_risk`). Put a short comment at the `drop_avoid=True` and `with_bonus=False` call sites pointing at project 2. Delete `evaluate_fantasy_picks`. Fix the comments you touch so they have no dashes.

- [ ] **Step 4: Full suite**

Run: `./venv/Scripts/python.exe -m pytest -q`
Expected: `75 passed`, no golden changes (`git status tests/golden` clean).

- [ ] **Step 5: Commit**

Hand Ashen: `src/fantasy.py`, `tests/test_helpers.py`. Summary `team scoring lives in one place now`. Description: the three team builders each had their own copy of the scoring and the copies disagreed, now one shared copy with the same numbers coming out (goldens untouched), plus a test that keeps the Avoid quirk where it is until project 2. Removed `evaluate_fantasy_picks`, nothing used it.

---

### Task 3: Leftovers, archive, ignore files

**Files:**
- Delete: `driver-cards/`, `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg`, `frontend/src/assets/hero.png`, `frontend/public/icons.svg`
- Move (`git mv`): `notebooks/` to `archive/notebooks/`, `results/` to `archive/results/`
- Modify: `scripts/measure_grid_error.py` (docstring line ~39 and output path ~131 to `archive/results/grid_error_{year}.csv`), `frontend/README.md` (replace), `.dockerignore`, `.gitignore`

**Interfaces:** none.

- [ ] **Step 1: Grep every path above** (see Global Constraints). Expected: no hits apart from `measure_grid_error.py` and the `driver-cards/` line in `.dockerignore`. Any other hit: keep that file and tell Ashen.
- [ ] **Step 2: Delete and move the files**, update `measure_grid_error.py`.
- [ ] **Step 3: `frontend/README.md`**: 5 lines max. What the frontend is, `npm install` / `npm run dev` / `npm run build`, `VITE_API_URL` if `src/api.js` reads it, and a link to `../Fantasy Predictor/Frontend.md`.
- [ ] **Step 4: Ignore files.** `.dockerignore`: drop `driver-cards/`, add `archive/` and `Fantasy Predictor/` (replace the old `notebooks/` and `results/` lines). `.gitignore`: add `.superpowers/` and `Fantasy Predictor/.obsidian/workspace*.json`.
- [ ] **Step 5: Verify**

Run: `./venv/Scripts/python.exe -m pytest -q` (expect `75 passed`) and `cd frontend && npm run build` (expect a successful build).

- [ ] **Step 6: Commit**

Hand Ashen everything above as one commit. Summary `cleared out old files and archived the notebooks`. Description: lists what went and why (driver-cards was a copy of frontend/public/drivers, Vite template files nobody used), notebooks and old results kept in archive/ as the model's history.

---

### Task 4: No more dashes

**Files:**
- Create: `tests/test_no_dashes.py`
- Modify: every tracked text file with U+2014 or U+2013 outside `venv/`, `frontend/node_modules/`, `data/`, `tests/golden/`, `archive/` (28 files at planning time). Includes `Dockerfile`, workflows, `src/`, `scripts/`, `frontend/src/`, docs, README.
- Modify: goldens whose text contains the boost reasons (text-only re-record)

**Interfaces:** none.

- [ ] **Step 1: Write the scan test**

```python
SCAN = ["src", "scripts", "tests", "frontend/src", "docs", "Fantasy Predictor", ".github"]
FILES = ["main.py", "README.md", "Dockerfile", "frontend/index.html", "frontend/README.md"]
SUFFIXES = {".py", ".js", ".jsx", ".css", ".md", ".yml", ".html", ".json", ""}

def test_no_em_or_en_dashes_anywhere():
    # Ashen's rule, and the 2x reason was showing up on the site as garbled text
    bad = []
    for path in _files():   # walks SCAN + FILES, skips tests/golden, missing paths are fine
        text = path.read_text(encoding="utf-8")   # strict: a re-encoded file fails here
        for n, line in enumerate(text.splitlines(), 1):
            if "\u2014" in line or "\u2013" in line:
                bad.append(f"{path}:{n}")
    assert not bad, "dashes found:\n" + "\n".join(bad)
```

Golden files are skipped by the scan but get covered by Step 5's re-record.

- [ ] **Step 2: Run it, expect FAIL** listing about 28 files.
- [ ] **Step 3: Replace the dashes by hand-reasoned rewording, not a blind swap.** Usually a comma, colon, full stop or "to" for ranges ("15 to 30 seconds"). Edit with the Edit tool so files stay UTF-8 with no BOM. While in these lines, fix two stale texts: the loading messages in `frontend/src/App.jsx` ("Fetching practice pace from FastF1" is now OpenF1, say "Fetching practice pace") and the `/snapshot/auto` docstring (it's the GitHub Action every 30 minutes now, not cron-job.org every 10).
- [ ] **Step 4: Run the scan test**, expect PASS. Then the full suite: the goldens that contain boost reasons fail.
- [ ] **Step 5: Text-only re-record**

Run: `UPDATE_GOLDEN=1 ./venv/Scripts/python.exe -m pytest -q`, then `git diff -U0 tests/golden | grep '^[-+] '`
Expected: every changed line is a `reason` string where only the dash wording changed. Any number changed: STOP and tell Ashen.

- [ ] **Step 6: Full suite** (`76 passed`) and `cd frontend && npm run build`.
- [ ] **Step 7: Commit**

Hand Ashen: all edited files, the re-recorded goldens, `tests/test_no_dashes.py`. Hold the push until Monday if it's race weekend (backend files are included). Summary `got rid of every em dash`. Description: also fixes the garbled 2x reason on the site, a test now fails if one sneaks back in, the golden changes are the reason text only.

---

### Task 5: Split `src/api/race_weekend.py`

**Files:**
- Create: `src/api/weekend_common.py`, `src/api/weekend_lock.py`, `src/api/finishes.py`
- Modify: `src/api/race_weekend.py`, `main.py:22,88`
- Test: `tests/test_endpoints.py`

**Interfaces:**
- `src/api/weekend_common.py`: `load_schedule()`, `next_race(schedule, now)`, `weekend_grid(race_name, final_session) -> tuple[pd.DataFrame | None, str | None]` (today's `_load_schedule`, `_next_race`, `_weekend_grid`, bodies unchanged).
- `src/api/weekend_lock.py`: `router` with `POST /snapshot/auto`; module globals `_snapshot_build_lock`, `_last_snapshot_result`; `should_self_lock(race_name, session_used, final_session) -> bool`; `start_snapshot_build(event, background_tasks) -> bool`; `_build_and_save_snapshot(event)`.
- `src/api/finishes.py`: `router` with `GET /weekend-finishes`; `attach_actual_results(snapshot) -> dict`; `_held_finishes() -> dict | None`.
- `src/api/race_weekend.py`: `router` with `GET /weekend-team` and `GET /last-team`, `_team_payload`, and `from src.api.weekend_lock import should_self_lock, start_snapshot_build` (the existing tests import `should_self_lock` from here).
- `main.py` registers `races, prices, teams, race_weekend, finishes, weekend_lock, dev`.
- Anything that reads `_last_snapshot_result` outside `weekend_lock.py` must read it as `weekend_lock._last_snapshot_result`, never `from ... import _last_snapshot_result`.

- [ ] **Step 1: Characterisation tests, written against today's module**

```python
EXPECTED_ROUTES = {("GET", "/weekend-team"), ("GET", "/last-team"),
                   ("GET", "/weekend-finishes"), ("POST", "/snapshot/auto")}

def test_weekend_routes_are_all_registered(client):
    have = {(m, r.path) for r in client.app.routes for m in getattr(r, "methods", [])}
    assert EXPECTED_ROUTES <= have

def test_snapshot_auto_reports_the_last_failed_build(client, at, monkeypatch, empty_snapshots):
    lock = importlib.import_module("src.api.race_weekend")   # Step 4 changes this to src.api.weekend_lock
    monkeypatch.setenv("SNAPSHOT_SECRET", "test-secret")
    monkeypatch.setattr(lock, "fetch_prices", lambda rnd: {"drivers": {"LEC": 24.1}})
    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(lock, "build_snapshot", boom)
    monkeypatch.setattr(lock, "_last_snapshot_result", {})
    monkeypatch.setattr(lock, "results_already_in_data", lambda race: False)
    lock._snapshot_build_lock.acquire()
    lock._build_and_save_snapshot({"EventName": "Test Grand Prix", "RoundNumber": 99})
    at(BAKU_THURSDAY)   # a "waiting" answer, which carries last_result
    r = client.post("/snapshot/auto", headers={"X-Snapshot-Secret": "test-secret"}).json()
    assert r["last_result"]["status"] == "error"
    assert r["last_result"]["detail"] == "boom"
    assert not lock._snapshot_build_lock.locked()
```

(Import `BAKU_THURSDAY` from `tests/conftest.py` the way the other tests get their times.)

- [ ] **Step 2: Run them, expect PASS** (they describe today's behaviour).
- [ ] **Step 3: Move the code** into the files above. Bodies unchanged apart from the renamed helpers and imports. Update the module docstrings (no dashes, no `docs/SNAPSHOTS.md` link, point at `Fantasy Predictor/Snapshots.md` instead).
- [ ] **Step 4: Point the second test at `src.api.weekend_lock`, and the Task 1 `waiting_before_fp3` patch at `weekend_lock.results_already_in_data`**, then run the full suite. Expected: `78 passed`, goldens untouched.
- [ ] **Step 5: Boot check**

Run: `./venv/Scripts/python.exe -c "import main"`, then `./venv/Scripts/python.exe -m uvicorn main:app --port 8001` in the background and `curl -s localhost:8001/weekend-team | head -c 300` and `curl -s localhost:8001/weekend-finishes | head -c 300`.
Expected: both answer with JSON (whatever weekend it is). Stop the server.

- [ ] **Step 6: Commit**

Hand Ashen: the three new files, `src/api/race_weekend.py`, `main.py`, `tests/test_endpoints.py`, all in ONE commit (Render needs them together). Push Monday to Thursday only. Summary `split race_weekend.py into smaller files`. Description: weekend team, predicted finishes and the auto lock each have their own file now, same URLs and answers, plus a test that every route is still there and one that the auto lock still reports a failed build.

---

### Task 6: Split `frontend/src/App.jsx` and share the form styles

**Files:**
- Create: `frontend/src/styles.js`, `frontend/src/teamCache.js`, `frontend/src/hooks/useRaceData.js`, `frontend/src/components/racedata/RaceResultsTab.jsx`, `frontend/src/components/racedata/PracticeTab.jsx`, `frontend/src/components/racedata/QualifyingTab.jsx`, `frontend/src/components/myteam/TeamOptimizerTab.jsx`, `frontend/src/components/ManualTeamParts.jsx`
- Modify: `frontend/src/App.jsx`, `frontend/src/components/ManualTeamBuilder.jsx`, any other component that repeats the same class strings (grep for `focus:border-pw-red/50`)

**Interfaces:**
- `styles.js`: `INPUT_CLS`, `PRIMARY_BTN_CLS`, `SECTION_HEAD_CLS`. Exactly today's strings (App's `inputCls`/`primaryBtn`/`sectionHead` are identical to ManualTeamBuilder's `SELECT_CLS`/`BTN_CLS`/`HEAD_CLS`).
- `teamCache.js`: `cacheTeam(d)`, `readCachedTeam()`, `pickNewer(cached, fromServer)`, with today's comments and try/catch kept.
- `hooks/useRaceData.js`: `useRaceResults()`, `usePractice()`, `useQualifying()`, `useBudgetTeams()`. Each returns the state, setters and fetch function App has today for that tab. **They're called in `App`**, and the result is passed to the tab component as one prop, so the state survives tab switches like it does now.
- Tab components render exactly today's JSX for their block.
- `ManualTeamParts.jsx`: `SelectedDriverSlot`, `SelectedConstructorSlot`, `PoolDriverCard`, `PoolConstructorCard`, moved unchanged.

- [ ] **Step 1: Baseline**: `cd frontend && npm run build && npm run lint`, and write down the lint result (it may already have warnings, the split must not add new ones).
- [ ] **Step 2: Do the moves.** No visual or text changes (Task 4 already did the wording).
- [ ] **Step 3: Build and lint**: same result as Step 1, no new lint problems.
- [ ] **Step 4: Click-through against the local backend.** Start the backend (Task 5 Step 5) and `npm run dev` with the API pointed at it. Check: Overview (live or held team, 3-team switcher), My Team > Team Optimizer (pick a race, build, switch teams), Manual Team, Chip Advisor, Race Data > Practice (pick a race, switch FP1/FP2/FP3), Qualifying, Race Results, Insights. Then pick a race in Practice, go to Qualifying and back: the Practice race must still be selected. Compare with the live site. Use the browser tool if one is available, otherwise ask Ashen to click through and say what looks different.
- [ ] **Step 5: Commit**

Hand Ashen the frontend files as one commit (Vercel only, safe any day). Summary `split App.jsx into smaller pieces`. Description: each Race Data tab and the Team Optimizer have their own file, the form styles are shared instead of copied, nothing on the site should look or act different.

---

### Task 7: The Fantasy Predictor vault

**Files:**
- Create: `Fantasy Predictor/` with `Start here.md`, `Race weekend flow.md`, `Model.md`, `Fantasy scoring.md`, `Chips.md`, `Prices.md`, `Snapshots.md`, `API.md`, `Frontend.md`, `Decisions and evidence.md`, `Gotchas.md`, `How-tos.md`, `Roadmap.md`, `Future plans.md`, `Working rules.md`, plus the vault's shared `.obsidian/` config if the plugin sets one up
- Delete (merged in): `ROADMAP.md`, `docs/FUTURE_PLANS.md`, `docs/MODEL.md`, `docs/SNAPSHOTS.md`
- Modify: `README.md` (link to the vault near the top, fix links to the deleted docs)

**Interfaces:** none.

- [ ] **Step 1: Invoke the `obsidian-notes:obsidian-notes` skill** and follow it for setting up the vault and the link style (relative markdown links that work in Obsidian, GitHub and VS Code; the folder name has a space).
- [ ] **Step 2: Write the notes.** Sources: the four docs above, `README.md`, the code itself, and Claude's memory files in `C:\Users\Ashen\.claude\projects\C--Users-Ashen\memory\` (`project_f1_predictor.md`, `project_pitwall_backlog.md`, `project_fp3_results_win.md`, `project_sprint_chip_tuning.md`). What goes in each note is in the spec's Part 2. Every claim about the code gets checked against the code as it is after Tasks 2 to 6, not copied from old docs. `Roadmap.md` holds the 7 projects (spec bottom section) plus the banked ideas from `ROADMAP.md`, and links to `../docs/superpowers/specs/` and `plans/`. `Future plans.md` is `docs/FUTURE_PLANS.md` (the career framing). `Start here.md` is written so a new chat can be told "read Fantasy Predictor/Start here.md" and get caught up.
- [ ] **Step 3: Lint the vault** with the plugin's `scripts/vault_lint.py`. Expected: no broken links, no orphans. Then grep the repo for links to the deleted docs (`docs/MODEL.md`, `docs/SNAPSHOTS.md`, `ROADMAP.md`, `FUTURE_PLANS`) and fix them.
- [ ] **Step 4: Full suite** (the dash test now scans the vault too). Expected: `78 passed`.
- [ ] **Step 5: Commit**

Hand Ashen: `Fantasy Predictor/`, the deleted docs, `README.md`, any file whose links got fixed. Summary `project notes live in an obsidian vault now`. Description: Fantasy Predictor/ opens in Obsidian and reads fine on GitHub, Start here.md is the way in, the old docs and roadmap got merged into it.

---

### Task 8: Trim Claude's memory to pointers

**Files (outside the repo, no commit):**
- Modify: `C:\Users\Ashen\.claude\projects\C--Users-Ashen\memory\project_f1_predictor.md`, `project_pitwall_backlog.md`, `MEMORY.md`

- [ ] **Step 1:** Cut `project_f1_predictor.md` and `project_pitwall_backlog.md` down to a few lines each: where the vault is, "read `Fantasy Predictor/Start here.md` first", and anything that isn't in the repo (like Ashen's league and no chips this season, already in `user_profile.md`). Update the hooks in `MEMORY.md` to match.
- [ ] **Step 2:** Tell Ashen what was cut and that it now lives in the vault.

---

### Final check (after Task 8)

- [ ] `./venv/Scripts/python.exe -m pytest -q`: all pass, 78 tests.
- [ ] `cd frontend && npm run build`: succeeds.
- [ ] `git status`: nothing left uncommitted apart from `.superpowers/` (ignored).
- [ ] After Ashen pushes the backend commits: live `/weekend-team` and `/weekend-finishes` answer the same as before the push.
