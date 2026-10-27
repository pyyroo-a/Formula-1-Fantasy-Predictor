# Accuracy bar and real scoring: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grade PitWall with the game's official points against model-free picks, and fix the forecast rules, keeping each fix only if it scores more real points.

**Architecture:** A referee module reads official per-round points from the F1 Fantasy feed into a committed JSON file. A scorecard script replays every 2026 round (walk-forward, via `src/backtest.py`) for PitWall and four model-free strategies, grades all of them with the referee, and writes `Fantasy Predictor/Scorecard.md`. Each forecast fix lands behind a switch that starts OFF, gets measured on the scorecard, and only the winners are switched on together at the end.

**Tech Stack:** Python 3.13, pandas, httpx, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-27-accuracy-bar-and-real-scoring-design.md`

## Global Constraints

- Never `git commit` or `git push`. Each "Commit" step: hand Ashen the files to tick, a Summary and a Description, wait for "committed".
- Tests: `./venv/Scripts/python.exe -m pytest -q` from the repo root. The suite is green at the end of every task.
- No backend pushes between FP1 Friday and the end of the race. Mexico FP1 is 2026-10-30, so Tasks 1 and 2 should be committed and pushed by Thursday 2026-10-29. Tasks 3 to 5 don't change live picks (switches start OFF). Task 6 changes live picks and is pushed Monday to Thursday only.
- Every number in the scorecard comes from the official feed or real data. Nothing guessed, tuned or filled in. A round without official points is shown as missing, never as 0.
- Walk-forward everywhere: anything used to predict round N comes only from rounds before N.
- Every forecast switch gets its measured numbers in a comment next to it, like `DNF_WEIGHT` in `src/fantasy.py`.
- Budget $100M for every scorecard column. Each race is a fresh team (no transfer limits).
- Free only, no new dependencies, no em or en dashes (the dash test enforces it), comments in Ashen's casual voice.
- Golden files only change in Task 6, re-recorded with the measured reason in the commit.

## Review Focus

- **A driver listed twice in an old round's feed** (moved teams mid season) must count once, using the active row, the same trap as prices. Pinned in Task 1 (`test_duplicate_driver_rows_use_the_active_one`).
- **A round that hasn't happened yet** has every `GamedayPoints` at 0 in its feed. The backfill must not store that as a real result. Pinned in Task 1 (`test_unraced_round_is_not_stored`).
- **The feed being down on a Monday** must not stop race results being added. Pinned in Task 2 (`test_update_data_survives_official_points_failure`).
- **Constructor extras leaking the future**: extras for round N use rounds before N only. Pinned in Task 5 (`test_constructor_extras_only_use_earlier_rounds`).
- **Old snapshots without ownership** (R13 to R18) must still load on the site and in the scorecard. Pinned in Task 2 (`test_old_snapshot_without_ownership_still_serves`) and Task 3.

---

### Task 1: The points referee

**Files:**
- Create: `src/official_points.py`, `scripts/backfill_official_points.py`, `data/official_points_2026.json`, `tests/test_official_points.py`, `tests/fixtures/feed_r18.json`

**Interfaces:**
- Produces:
  - `parse_official_points(items: list[dict]) -> dict`: returns `{"drivers": {TLA: {"points", "qualifying", "race", "sprint"}}, "constructors": {full_name: {...same}}}`, all floats (empty string means 0.0). One entry per driver code, preferring the `IsActive == "1"` row. Constructors keyed by `FUllName` (same names as `parse_price_feed`).
  - `fetch_official_points(round_number: int) -> dict`: fetches `<round>_en.json` via the same `F1_FANTASY_BASE` as `fetch_prices`, returns `parse_official_points(...)` plus `"prices"` from `parse_price_feed`.
  - `is_raced(round_points: dict) -> bool`: False when every driver's `points` is 0.0.
  - `load_official_points(path: str = OFFICIAL_POINTS_PATH) -> dict[int, dict]` and `save_official_round(round_number: int, round_points: dict, path: str = OFFICIAL_POINTS_PATH) -> None`. `OFFICIAL_POINTS_PATH = "data/official_points_2026.json"`, JSON keys are round numbers as strings.
  - `team_points(drivers: list[str], constructors: list[str], boost: str | None, round_points: dict) -> float`: sum of official points, the boost driver counted twice.

- [ ] **Step 1: Save the real fixture.** Download `https://fantasy.formula1.com/feeds/drivers/18_en.json`, keep `Data.Value` only, save to `tests/fixtures/feed_r18.json`.
- [ ] **Step 2: Write the failing tests**

```python
def test_team_points_matches_the_app_for_ashens_us_gp_team():
    pts = official_points.parse_official_points(_fixture("feed_r18.json"))
    total = official_points.team_points(
        ["LEC", "ANT", "PER", "LIN", "HUL"], ["Ferrari", "Haas F1 Team"], "LEC", pts)
    assert total == 238.0   # Ashen's real score in the app

def test_points_split_into_qualifying_and_race():
    pts = official_points.parse_official_points(_fixture("feed_r18.json"))
    assert pts["drivers"]["LEC"] == {"points": 53.0, "qualifying": 7.0, "race": 46.0, "sprint": 0.0}
    assert pts["constructors"]["Ferrari"]["points"] == 81.0

def test_duplicate_driver_rows_use_the_active_one():
    items = [_row("LAW", 15.1, active="0", pts="0"), _row("LAW", 9.3, active="1", pts="12")]
    assert official_points.parse_official_points(items)["drivers"]["LAW"]["points"] == 12.0

def test_unraced_round_is_not_stored(tmp_path):
    zeros = {"drivers": {"LEC": {"points": 0.0, "qualifying": 0.0, "race": 0.0, "sprint": 0.0}}, "constructors": {}}
    assert official_points.is_raced(zeros) is False
```

(`_fixture` and `_row` are small helpers in the test file. `_row` builds a minimal feed item.)

- [ ] **Step 3: Run them**, expect FAIL (module missing).
- [ ] **Step 4: Implement `src/official_points.py`** per the Interfaces. Network calls only in `fetch_official_points`.
- [ ] **Step 5: Run them**, expect PASS.
- [ ] **Step 6: Backfill script.** `scripts/backfill_official_points.py [--rounds 1-18]`: for each round, `fetch_official_points`, skip and print if `not is_raced(...)`, else `save_official_round`. Run it for rounds 1 to 18.
  Expected: 18 rounds saved (print any that weren't, don't hide them). Spot check: round 18 Ferrari 81, round 13 Mercedes 128, round 17 Leclerc 43.
- [ ] **Step 7: Full suite**, expect 83 passed.
- [ ] **Step 8: Commit.** Files: the five above. Summary `the game's own points for every race this season`. Description: official points straight from the F1 Fantasy feed, backfilled for rounds 1 to 18, checked against my real US GP score (238 in the app, 238 from the feed).

---

### Task 2: Ownership at every lock, official points every Monday

Goes before the measuring work on purpose: the crowd column needs ownership saved at the Mexico lock, so this has to be pushed by Thursday.

**Files:**
- Modify: `src/official_points.py` (add ownership), `src/weekend.py` (`build_snapshot` ~275), `scripts/update_data.py`, `tests/conftest.py`
- Test: `tests/test_official_points.py`, `tests/test_endpoints.py`

`tests/conftest.py` gets an autouse fixture that makes `official_points.fetch_official_points` and `official_points.fetch_ownership` raise, so no test ever reaches the live feed (same idea as `USE_OPENF1=0`). Tests that need them patch in their own fakes.

**Interfaces:**
- Produces:
  - `parse_ownership(items: list[dict]) -> dict`: `{"drivers": {TLA: {"selected_pct": float, "captain_pct": float}}, "constructors": {name: {"selected_pct": float, "captain_pct": float}}}`, active row preferred.
  - `fetch_ownership(round_number: int) -> dict`.
  - Snapshots gain an optional top level key `"ownership"` (that dict) and `"ownership_fetched_at"` (UTC ISO string). Missing on old snapshots.
- Consumes: Task 1's `fetch_official_points`, `is_raced`, `save_official_round`.

- [ ] **Step 1: Failing tests**

```python
def test_ownership_parsed_from_feed():
    own = official_points.parse_ownership(_fixture("feed_r18.json"))
    assert own["drivers"]["LEC"] == {"selected_pct": 26.0, "captain_pct": 14.0}

def test_snapshot_keeps_building_when_ownership_fetch_fails(monkeypatch):
    # build_snapshot with fetch_ownership raising: snapshot still built, no "ownership" key

def test_old_snapshot_without_ownership_still_serves(client, at, snapshots):
    # serve R14's snapshot (no ownership key) at SAT_MADRING_BEFORE_QUALI, /weekend-team answers 200, locked

def test_update_data_survives_official_points_failure(monkeypatch):
    # run scripts/update_data.py's main logic with fetch_official_points raising: results still saved, a ::warning:: printed
```

(Write the bodies from the comments. `update_data.py` is a script with top level code: wrap its body in `def main():` with an `if __name__ == "__main__":` guard so the test can call it.)

- [ ] **Step 2: Run them**, expect FAIL.
- [ ] **Step 3: Implement.** `build_snapshot` calls `fetch_ownership(rnd)` in a try/except. A failure just leaves the key out. `update_data.py`, after results: for the latest finished round, fetch official points and save if raced, inside its own try/except with a `::warning::` like prices.
- [ ] **Step 4: Run tests**, expect PASS. Full suite expect 87 passed, goldens untouched (snapshot goldens use a monkeypatched or failing fetch, so the check that nothing changed holds; if a golden moves, stop and find why).
- [ ] **Step 5: Commit, push by Thursday.** Files: `src/official_points.py`, `src/weekend.py`, `scripts/update_data.py`, `tests/conftest.py`, both test files. Summary `save who owns what at every lock, and official points every monday`.

---

### Task 3: The scorecard, with today's rules

**Files:**
- Create: `src/simple_picks.py`, `scripts/scorecard.py`, `tests/test_simple_picks.py`, `Fantasy Predictor/Scorecard.md` (generated)
- Modify: `src/backtest.py` (grade with the referee), `Fantasy Predictor/README.md` (link the Scorecard note)

**Interfaces:**
- Consumes: Task 1's `load_official_points`, `team_points`. Task 2's snapshot `"ownership"`.
- Produces (all return a team dict `{"drivers": [{"Abbreviation"}], "constructors": [{"name"}], "boost_pick": {"Abbreviation"}}`, or None if nothing fits, all at `budget: float = 100.0`):
  - `fp3_order_team(grid: pd.DataFrame, prices: dict, budget) -> dict`: the legal team (5 drivers, 2 constructors, under budget) with the lowest sum of drivers' grid positions plus constructors' best car grid position. Ties go to the cheaper team. Boost: the owned driver with the best grid position. Uses only `grid["Abbreviation", "TeamName", "GridPosition"]` and prices, never `FantasyValue`.
  - `most_expensive_team(prices: dict, budget) -> dict`: the highest total price. Boost: the priciest driver.
  - `crowd_team(ownership: dict, prices: dict, budget) -> dict`: the highest total `selected_pct`. Boost: the highest `captain_pct` owned.
  - `hindsight_best_team(round_points: dict, prices: dict, budget) -> dict`: the highest `team_points` including the boost (boost = its top scoring driver).
  - `src/backtest.py`: `run_backtest(..., official: dict[int, dict] | None = None)`. When given, every score comes from `team_points` instead of `_score_team`/`_actual_*_points`, and each race row gains `"official_missing": True` when that round isn't in `official`.
  - `scripts/scorecard.py [--rules NAME]` writes `Fantasy Predictor/Scorecard.md` (or prints with `--stdout`).

- [ ] **Step 1: Failing tests** in `tests/test_simple_picks.py`, on a small made up pool (6 drivers, 3 constructors, prices chosen so the answer is obvious):

```python
def test_fp3_order_team_takes_the_fastest_that_fit(): ...
def test_fp3_order_team_never_reads_fantasy_value(): ...  # pass a grid with FantasyValue = nonsense, same answer
def test_most_expensive_team_spends_the_most_under_budget(): ...
def test_crowd_team_maximises_ownership_and_boosts_most_captained(): ...
def test_hindsight_best_counts_the_boost(): ...           # a cheap 2x driver beats a pricier one
def test_nothing_fits_returns_none(): ...                  # budget 5.0
```

Each asserts the exact drivers, constructors and boost.

- [ ] **Step 2: Run**, expect FAIL. **Step 3: Implement** `src/simple_picks.py` (brute force over combinations like `build_budget_teams`, fine for 22 drivers). **Step 4: Run**, expect PASS.
- [ ] **Step 5: Backtest grades with the referee.** Failing test in `tests/test_helpers.py`: `test_backtest_scores_with_official_points` (feed `run_backtest` a stubbed one round setup via monkeypatch and an `official` dict, assert the race's `model_score` equals `team_points` of its team). Then implement. The old `_actual_*` stay for `official=None` callers only.
- [ ] **Step 6: The scorecard script.** Columns per race: Race | Locked (R13+, from `data/snapshots`, team 1) | PitWall replay | FP3 order | Most expensive | Crowd | Hindsight best. Then rows: average per race (over races where that column exists), races where PitWall replay beat each simple column. Missing values show as `-` with a footnote why (no snapshot, no ownership yet, no official points). Header line: which rules ran (`--rules`), the date, and "all points are official F1 Fantasy points".
- [ ] **Step 7: Run it with today's rules** (`--rules current`). This is the honest starting number. Paste the summary rows into the commit description.
- [ ] **Step 8: Full suite** expect 94 passed, goldens untouched.
- [ ] **Step 9: Commit.** Files: the new files, `src/backtest.py`, `tests/test_helpers.py`, the README note link. Summary `season scorecard graded with the game's real points`.

---

### Task 4: Real qualifying rules and constructor bonuses (switches OFF)

**Files:**
- Modify: `src/fantasy.py` (`qualifying_score` ~112, `_constructor_scores` bonus ~442), `src/weekend.py` (`evaluate_team_chips` back row ~228), `scripts/scorecard.py` (`--rules` names)
- Test: `tests/test_helpers.py`

**Interfaces:**
- Produces in `src/fantasy.py`: `REAL_QUALI_RULES = False` and `REAL_CONSTRUCTOR_QUALI_BONUS = False`, read at call time (so the scorecard can flip them with monkeypatching or a context helper `rules(**switches)` in `scripts/scorecard.py`).
- `--rules` names: `current`, `quali`, `bonus`, `quali+bonus`.

- [ ] **Step 1: Failing tests**

```python
def test_real_quali_rules_give_zero_from_p11(monkeypatch):
    monkeypatch.setattr(fantasy, "REAL_QUALI_RULES", True)
    assert [fantasy.qualifying_score(p) for p in (1, 10, 11, 16, 22)] == [10, 1, 0, 0, 0]

def test_old_quali_rules_unchanged_while_switched_off():
    assert fantasy.qualifying_score(16) == -5

def test_real_constructor_bonus_values(monkeypatch):
    monkeypatch.setattr(fantasy, "REAL_CONSTRUCTOR_QUALI_BONUS", True)
    # grids (1, 2) -> +10, (3, 14) -> +5, (11, 12) -> +3, (12, 18) -> +1, (17, 19) -> -1, via _constructor_scores with with_bonus=True and no TeamAvgPosition

def test_no_negative_ignores_back_row_with_real_quali_rules(monkeypatch): ...  # points_at_risk has no +5 per P16+ driver
```

- [ ] **Step 2: Run**, FAIL. **Step 3: Implement** the switches. The top team bonus (+1.5 / +0.5) stays as it is in both modes. **Step 4: Run**, PASS. Full suite green, goldens untouched (switches OFF).
- [ ] **Step 5: Measure.** `scripts/scorecard.py --rules quali`, `--rules bonus`, `--rules quali+bonus`, `--stdout`. Write the averages and races won into the comment above each switch (like `DNF_WEIGHT`), leaving the value False.
- [ ] **Step 6: Commit.** Summary `real qualifying rules and constructor bonuses, measured, still switched off`. Description: the measured numbers vs `current`.

---

### Task 5: Constructor scoring fixed, and expected pit stop points (switches OFF)

**Files:**
- Modify: `src/fantasy.py` (`_constructor_scores` and its 3 callers), `scripts/scorecard.py`
- Create: `src/constructor_extras.py`, `tests/test_constructor_extras.py`
- Test: `tests/test_helpers.py` (the quirk test gains a switched on twin)

**Interfaces:**
- Produces:
  - `FIX_CONSTRUCTOR_QUIRKS = False` in `src/fantasy.py`: when True every caller uses `drop_avoid=False, with_bonus=True`.
  - `constructor_extras(official: dict[int, dict], results: pd.DataFrame, before_round: int) -> dict[str, float]` in `src/constructor_extras.py`: per constructor, the average over rounds `< before_round` of (official constructor points minus its two drivers' official points minus the real qualifying bonus their real grid earned). Real grid from `results["GridPosition"]`.
  - `USE_CONSTRUCTOR_EXTRAS = False` in `src/fantasy.py`: when True, the scoring path adds `extras[team]` to each constructor's score (passed in by the caller, `{}` when unavailable).
  - `--rules` names add `quirks`, `extras`, and `all` (every switch on).

- [ ] **Step 1: Failing tests**

```python
def test_constructor_extras_only_use_earlier_rounds(): ...   # official data for rounds 3, 4, 5, before_round=5 averages 3 and 4 only
def test_constructor_extras_subtract_drivers_and_quali_bonus(): ...  # hand built round: Ferrari 81, LEC 53 + HAM 20, both Q3 (+10) -> extras -2.0
def test_constructor_extras_empty_before_any_history(): ...  # before_round=1 -> {}
def test_fixed_quirks_count_avoid_drivers_and_add_bonus(monkeypatch): ...  # the Cadillac/Ferrari frame from the existing quirk test: builder Cadillac -8.8, pool Ferrari 70.7
```

- [ ] **Step 2: Run**, FAIL. **Step 3: Implement.** **Step 4: Run**, PASS, full suite green, goldens untouched.
- [ ] **Step 5: Measure** `--rules quirks`, `--rules extras`, `--rules all`. Numbers into the comments next to both switches, values stay False.
- [ ] **Step 6: Commit.** Summary `constructor scoring fix and expected pit stop points, measured, still switched off`.

---

### Task 6: Switch on what won

**Files:**
- Modify: `src/fantasy.py` (switch values and comments), `tests/golden/*` (re-record), `tests/test_helpers.py` (the quirk pin test follows whatever ships)

- [ ] **Step 1: Pick the winners.** From Tasks 4 and 5's numbers: a switch goes on only if, on the replay, it raises PitWall's average real points AND doesn't lose more races than it wins vs `current`. Then run every winner together (`--rules` with the chosen set) and confirm the combination beats each winner alone. If no switch wins, none go on, and that result gets written down just the same. **Stop and show Ashen the table before changing any value.**
- [ ] **Step 2: Flip the agreed switches**, update their comments to "on since 2026-..., measured ...".
- [ ] **Step 3: Re-record goldens** (`UPDATE_GOLDEN=1`), read the diff: only scores, teams and chip numbers move, no route or shape changes. Full suite green.
- [ ] **Step 4: Regenerate `Fantasy Predictor/Scorecard.md`** with the shipped rules.
- [ ] **Step 5: Commit, push Monday to Thursday only.** Summary `switched on the scoring fixes that scored more real points`. Description: the before and after table.

---

### Task 7: Notes

**Files:**
- Modify: `Fantasy Predictor/Fantasy scoring.md`, `Decisions and evidence.md`, `Chips.md`, `Gotchas.md`, `Roadmap.md`, `README.md` (vault), `README.md` (repo, the 25.8% scoring cliff claim and the P16 -5 rule), `Prices.md` (round 14 is back)

- [ ] **Step 1:** Write what changed and the measured numbers. Remove the fake P15/P16 cliff and its 25.8% number everywhere (repo README "Why off by 2 places is worse than it sounds", Decisions and evidence), or rewrite it around the real P10/P11 edge if the numbers support it. Note the Monday job works after the login wall (fixes the "at risk" text in Gotchas, Roadmap and the vault README). Add to the Roadmap: the one UI redesign at the end using the frontend design plugin. Mark project 2 done.
- [ ] **Step 2:** Vault lint (obsidian-notes `vault_lint.py` on `Fantasy Predictor`), 0 errors. Full suite green (the dash test covers the notes).
- [ ] **Step 3: Commit.** Summary `notes for real scoring and the scorecard`.
