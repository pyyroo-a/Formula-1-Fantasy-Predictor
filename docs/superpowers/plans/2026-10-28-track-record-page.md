# Track record page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A TRACK RECORD tab under INSIGHTS showing what PitWall's locked team 1 really scored each locked weekend against copy the FP3 order, most expensive, crowd and hindsight, in official points, updated every Monday.

**Architecture:** The scorecard's simple pick grading moves into `src/track_record.py`, shared by `scripts/scorecard.py` and a new `scripts/track_record.py` that writes `data/track_record_2026.json`. The Monday Action runs it. `GET /track-record` serves the file, a new React tab shows it.

**Tech Stack:** Python / pandas / FastAPI / pytest, React + Tailwind, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-28-track-record-page-design.md`

## Global Constraints

- Numbers must equal the scorecard's for Locked, FP3 order, Most expensive, Crowd, Hindsight best (same code).
- Only rounds with a snapshot AND official points. PitWall = locked team 1.
- Beat counts only over races where both numbers exist; a tie is not a win.
- Ashen commits and pushes; each task ends with files, Summary, Description, wait for "committed".
- Tests `./venv/Scripts/python.exe -m pytest -q` (183 before). No em or en dashes. Casual voice. Data true.
- No backend pushes from FP1 Friday until the race is over.

## Review Focus

- No track record file yet (fresh deploy): endpoint returns an empty record, page says "no locked weekends graded yet". Test in Task 2 (`test_track_record_without_a_file`).
- A locked weekend whose practice grid won't load: FP3 order is "-" with a reason, the other columns still show. Test in Task 1 (`test_round_without_a_grid_still_grades_the_rest`).
- A round locked but not raced yet (no official points): left out, never a 0. Test in Task 1 (`test_unraced_locked_round_is_left_out`).
- Ties (PitWall equals a pick): neither green nor counted as a win. Test in Task 1 (`test_summary_counts_wins_not_ties`).
- The scorecard's output must not move. Existing `tests/test_scorecard.py` passes untouched.

---

### Task 1: Shared grading module

**Files:** Create `src/track_record.py`, `tests/test_track_record.py`. Modify `scripts/scorecard.py` (`grade_round` uses the module), `src/backtest.py` and `src/fetch_practice.py` (move `deadline_grid`, backtest keeps importing it).

**Produces:**
- `SIMPLE_COLUMNS = ["Locked", "FP3 order", "Most expensive", "Crowd", "Hindsight best"]`
- `grade_simple(round_points: dict, prices: dict, grid, snapshot: dict | None, entry: list[str] | None) -> tuple[dict, dict, dict]` returning `(cells, why, teams)` for those columns, exactly the logic now in `grade_round`.
- `build_rows(official: dict, rounds: list[tuple[int, str, list[str]]], load_grid, find_snapshot) -> list[dict]`, rows `{"round", "race", "cells", "why"}` only for rounds with a snapshot and official points.
- `summarise(rows: list[dict]) -> dict`: per column `{"avg", "races"}`, and for each pick column `{"beaten", "of"}` (PitWall's Locked strictly higher).

- [ ] Write failing tests on a tiny made up price pool (3 or 4 cheap drivers and constructors so brute force is instant): `test_round_without_a_grid_still_grades_the_rest`, `test_unraced_locked_round_is_left_out`, `test_unlocked_round_is_left_out`, `test_summary_counts_wins_not_ties`, `test_summary_averages_only_races_with_a_number`. Run, watch them fail.
- [ ] Implement, refactor `grade_round` onto `grade_simple`, move `deadline_grid`. Run the new tests and `tests/test_scorecard.py` (must pass unchanged), then the full suite.
- [ ] Hand Ashen the commit.

### Task 2: The file, the Action and the endpoint

**Files:** Create `scripts/track_record.py`, `src/api/track_record.py`, `data/track_record_2026.json` (generated). Modify `main.py` (router), `.github/workflows/update-race-data.yml`, `tests/test_endpoints.py`.

- `scripts/track_record.py` writes `{"updated": "YYYY-MM-DD", "rows": [...], "summary": {...}}` to `data/track_record_2026.json` using `build_rows(..., deadline_grid, find_snapshot)` over the rounds in the season results file.
- `GET /track-record` reads `TRACK_RECORD_PATH` (default the file above, env override for tests) and returns it, or `{"updated": None, "rows": [], "summary": {}}` when missing.
- Action: run `python scripts/track_record.py` after `update_data.py`, add the JSON to `git add`.

- [ ] Failing tests: `test_track_record_serves_the_file`, `test_track_record_without_a_file`. Watch them fail, implement, pass.
- [ ] Run the script for real. Expected: R13 to R18 equal to the scorecard note (Locked 147, 145, 99, 212, 265, 183; FP3 order 205, 129, 88, 231, 227, 242; most expensive 205.0, 88.1, 101.3, 175.0, 117.5, 121.2; hindsight 428, 199, 270, 339, 298, 276). Any difference: stop and find out why.
- [ ] Full suite, hand Ashen the commit (backend: push Monday to Thursday).

### Task 3: The page

**Files:** Create `frontend/src/components/TrackRecord.jsx`. Modify `frontend/src/App.jsx` (INSIGHTS sub tabs: PREDICTED FINISHES, TRACK RECORD).

- [ ] Build it like mockup A (`.superpowers/brainstorm/2247-1793194346/content/track-record.html`): tiles, table with green / amber cells for the pick columns, the notes. Empty record: one line, "No locked weekends graded yet."
- [ ] `npm run lint` (no new errors, 7 already exist) and `npm run build`.
- [ ] Look at it in the browser pane against a local backend, desktop and phone width. Show Ashen.
- [ ] Hand Ashen the commit.

### Task 4: Notes and final review

- [ ] Scorecard (points at the page), Roadmap (project 5 done), README, API, Frontend, Snapshots/How-tos if the Monday job description lives there.
- [ ] Full suite, one fresh reviewer on the strongest model, fix Critical/Important test first.
- [ ] Hand Ashen the commit.
