# Chip history by track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An INSIGHTS > CHIPS tab showing, per track, what 3x, Limitless and No Negative would really have been worth in 2025 and 2026, best tracks per chip, plain lines for Wildcard, Final Fix and Autopilot, with an honest check of whether 2025 predicted 2026.

**Architecture:** A light module `src/chip_history.py` turns each weekend's points into chip values and groups them by track. `scripts/chip_history.py` builds `data/chip_history.json` (plus the proving check), the Monday Action rebuilds it, `GET /chip-history` serves it, a React tab shows it. Same pattern as the track record (project 5).

**Tech Stack:** Python / pandas / FastF1 schedule (cached) / FastAPI / pytest, React + Tailwind.

**Spec:** `docs/superpowers/specs/2026-10-28-chip-history-design.md`

## Global Constraints

- Seasons 2025 and 2026 only. 2026 points from `data/official_points_2026.json`, 2025 from our own scoring (said on the page).
- 3x = top driver's weekend points (race + quali + sprint). No Negative = 7 x mean over every driver and constructor of max(0, -points). Limitless = no cap best (top 5 drivers + top driver again for the 2x + top 2 constructors) minus `simple_picks.hindsight_best_team` at $100M; 2026 only (needs prices).
- Track key = FastF1 schedule `Location`, with `TRACK_ALIASES = {"Monte Carlo": "Monaco"}`. Kuala Lumpur stays its own track.
- Typical = median. Every value carries who scored it for 3x ("ANT P19 to P1").
- Ashen commits and pushes, each task ends with files, Summary, Description. Tests `./venv/Scripts/python.exe -m pytest -q` (193 before). No em or en dashes. Casual voice. Data true, never fake a missing sprint.

## Review Focus

- A 2025 sprint weekend whose sprint results won't load: its 3x and No Negative are marked "no sprint data" and left out of medians, never scored as if no sprint happened. Test in Task 1 (`test_weekend_missing_its_sprint_is_marked_not_faked`).
- A track raced in only one season: shows "1 season", ranks on that one value, flagged. Test in Task 1 (`test_one_season_track_says_so`).
- The proving check only uses tracks raced in both seasons. Test in Task 1 (`test_rank_check_uses_tracks_in_both_seasons`).
- No chip history file yet: endpoint returns an empty history, page says so. Test in Task 3.
- Ties in a best tracks list: stable order (by track name). Test in Task 1 (`test_best_tracks_ties_are_stable`).

---

### Task 1: The chip values module

**Files:** Create `src/chip_history.py`, `tests/test_chip_history.py`. Move `_actual_driver_points` and `_actual_constructor_points` from `src/backtest.py` into `src/fantasy.py` as `actual_driver_points` / `actual_constructor_points` (backtest imports them back under the old names), so the Monday job never imports the model.

**Produces:**
- `TRACK_ALIASES`, `track_key(location: str) -> str`
- `weekend_values(driver_pts: dict, constructor_pts: dict, prices: dict | None, starts: dict, finishes: dict, sprint_missing: bool = False) -> dict`: `{"3x": {"value", "who"} | None, "No Negative": float | None, "Limitless": float | None}` (None for Limitless without prices; 3x and No Negative None when `sprint_missing`).
- `track_table(weekends: list[dict]) -> list[dict]`: weekends are `{"season", "round", "track", "name", "sprint", "values"}`; one row per track with, per chip, `{"median", "values": [{"season", "value", "who"}], "seasons"}`.
- `best_tracks(table: list[dict], chip: str, n: int = 3) -> dict`: `{"top": [...], "worst": {...}}` by median, ties by track name.
- `rank_check(weekends: list[dict], chip: str, past: int = 2025, future: int = 2026) -> dict`: `{"tracks", "spearman", "top5_hits"}` over tracks raced in both.

- [ ] Failing tests on hand made weekends: `test_three_x_is_the_top_driver_with_who`, `test_no_negative_is_what_an_average_team_gets_back` (e.g. 6 assets at -20, 0, 0, 0, 5, 10 plus... worked out by hand), `test_limitless_needs_prices`, `test_weekend_missing_its_sprint_is_marked_not_faked`, `test_monte_carlo_is_monaco_and_kuala_lumpur_is_its_own`, `test_one_season_track_says_so`, `test_best_tracks_ties_are_stable`, `test_rank_check_uses_tracks_in_both_seasons`. Watch them fail.
- [ ] Implement, move the two scoring helpers, run the new tests, `tests/test_scorecard.py` and the full suite.
- [ ] Hand Ashen the commit.

### Task 2: Real data and the proving check (stop point)

**Files:** Create `scripts/chip_history.py`, `data/processed/sprint_results_2025.csv` (one-off fetch with `src.fetch_results.update_sprint_results(2025, ...)`), `data/chip_history.json` (generated).

- [ ] Fetch the 2025 sprints. Any that won't load stay missing (the module marks them).
- [ ] The script: 2026 weekends from the official points file (drivers, constructors, prices) and the 2026 results file (starts and finishes for "who"); 2025 weekends from `race_results_2025.csv` and `sprint_results_2025.csv` scored with `actual_driver_points` / `actual_constructor_points`; track names from the cached FastF1 schedules. Writes `{"updated", "tracks": track_table(...), "best": {chip: best_tracks(...)}, "check": {chip: rank_check(...)}}`. Prints the table and the check.
- [ ] Run it. Sanity: 2026 values match the brainstorm (China 3x 68, Limitless +88; Miami Limitless +167; Monaco +15; Monza 3x 93 "ANT P19 to P1").
- [ ] **STOP and show Ashen** the best tracks lists and the proving check (rank correlation and top 5 hits for 3x and No Negative). A chip whose check is no better than chance gets the "hasn't predicted much so far" line on the page. No tuning.
- [ ] Hand Ashen the commit.

### Task 3: Monday job and endpoint

**Files:** Create `src/api/chip_history.py`. Modify `main.py`, `.github/workflows/update-race-data.yml` (run `python scripts/chip_history.py` with `continue-on-error: true` after the track record, `git add data/chip_history.json`), `tests/test_endpoints.py`.

- [ ] Failing tests `test_chip_history_serves_the_file`, `test_chip_history_without_a_file` (`CHIP_HISTORY_PATH` env override, empty `{"updated": None, "tracks": [], "best": {}, "check": {}}`). Implement, pass, full suite.
- [ ] Hand Ashen the commit.

### Task 4: The CHIPS tab

**Files:** Create `frontend/src/components/ChipHistory.jsx`. Modify `frontend/src/App.jsx` (`INSIGHTS_TABS` gets `{ id: "chips", label: "CHIPS" }`).

- [ ] Like mockup A (`.superpowers/brainstorm/2247-1793194346/content/chips-history.html`): the track table (typical value, each season's value with who, sprint marker, "1 season" flag), the three best tracks boxes (with the check's line when a chip didn't predict), the Wildcard / Final Fix / Autopilot lines, the note (2025 is our own scoring, 2026 official, best possible picks, facts not advice).
- [ ] `npm run lint` (no new errors) and `npm run build`, look at it in the browser pane desktop and phone width, show Ashen.
- [ ] Hand Ashen the commit.

### Task 5: Notes and final review

- [ ] Chips (the history and how to read it), Decisions and evidence (the proving check numbers), Roadmap (project 6 done, the plain Obsidian code tour note is next per Ashen), README, API, Frontend, Race weekend flow (Monday job).
- [ ] Full suite, one lean reviewer on the strongest model, fix Critical/Important test first.
- [ ] Hand Ashen the commit.
