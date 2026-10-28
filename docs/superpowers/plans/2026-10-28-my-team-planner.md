# My team planner: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A My Team page that saves up to 3 of Ashen's real teams and shows, for any one, a transfer ladder (best team for 0 transfers up to the free ones plus one paid) with expected points, plain facts and a practice reason per swap, proven on real points before it ships.

**Architecture:** The ladder maths is a plain module (`src/planner.py`) that works on the existing driver pool (`get_race_pool`), so it scores exactly like the Manual Team page. A replay module (`src/planner_replay.py`) plays a season three ways (keep, free only, with hits) on walk forward forecasts and official points, run by `scripts/planner_grade.py`. A FastAPI endpoint serves the ladder live and a React page under My Team calls it.

**Tech Stack:** Python 3.13, pandas, FastAPI, pytest; React + Vite + Tailwind. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-28-my-team-planner-design.md`

## Global Constraints

- Never `git commit` or `git push`. Each "Commit" step: hand Ashen the files to tick, a Summary and a Description, wait for "committed".
- Tests: `./venv/Scripts/python.exe -m pytest -q` from the repo root, green at the end of every task. Frontend: `npm run build` passes in `frontend/`, `npm run lint` adds no new errors (7 old ones exist).
- No backend pushes from FP1 Friday until the race is over. Frontend only pushes are fine any day.
- Facts, not orders: no "do this", "you should", "recommended" anywhere in the ladder's text.
- Every row's team is legal: 5 different drivers, 2 different constructors, all in this weekend's pool, cost no more than the team's budget. The keep row is the only exception (it's whatever you have).
- Per driver and per constructor numbers come from `get_race_pool`, so they match the Manual Team page. A row's total = its 5 drivers' `FantasyValue` + its 2 constructors' `score` + the 2x driver's `FantasyValue` again (2x from `pick_boost_driver`), minus 10 per paid transfer.
- Rows: 0 up to the free transfers, plus 1 paid row while `SHOW_PAID_ROW` is True. Each row is the best team with exactly that many transfers, found independently (not nested).
- Free, no new dependencies, no em or en dashes (the dash test covers code and notes), comments in Ashen's casual voice. Keep it simple, no extra cleverness.

## Review Focus

- **A saved team with a driver who isn't in this weekend's field** (left the grid, or no practice laps): the keep row still shows, he scores 0, a fact names him, nothing crashes. Pinned in Task 1 (`test_ladder_flags_a_driver_not_in_this_weekends_field`).
- **A budget lower than the saved team's cost** (typed wrong, or prices rose): the keep row still shows, every other row stays within the budget, or the row says no legal team. Pinned in Task 1 (`test_ladder_rows_stay_within_budget_even_if_keep_does_not`).
- **The same driver or constructor twice** after a swap must never happen. Pinned in Task 1 (`test_best_with_transfers_never_repeats_a_pick`).
- **Free transfers outside 1 to the cap** in a request: refused with a clear 422, not a silent clamp. Pinned in Task 3 (`test_transfer_ladder_refuses_bad_free_transfers`).
- **A locked weekend** must use the session it locked on and say it isn't provisional. Pinned in Task 3 (`test_transfer_ladder_uses_the_locked_session`).

---

### Task 1: The rollover rule and the ladder maths

**Files:**
- Create: `src/planner.py`, `tests/test_planner.py`

**Interfaces:**
- Consumes: `get_race_pool` output from `src/fantasy.py` (`{"drivers": [{"Abbreviation", "TeamName", "GridPosition", "Predicted", "FantasyValue", "Price", ...}], "constructors": [{"name", "price", "score"}]}`), `pick_boost_driver(drivers: list[dict]) -> dict` from `src/fantasy.py`.
- Produces in `src/planner.py`:
  - `FREE_PER_RACE = 2`, `MAX_FREE_TRANSFERS = <confirmed in Step 1>`, `TRANSFER_HIT = 10`, `SHOW_PAID_ROW = True` (measured in Task 2)
  - `next_free_transfers(free_now: int, used: int) -> int`: `min(MAX_FREE_TRANSFERS, max(free_now - used, 0) + FREE_PER_RACE)`
  - `team_cost(drivers: list[str], constructors: list[str], prices: dict) -> float` (a pick with no price counts 0)
  - `score_team(drivers: list[str], constructors: list[str], pool: dict) -> dict`: `{"expected": float, "boost": str | None, "missing": list[str]}` (picks not in the pool score 0 and are listed in `missing`, the 2x is picked among drivers that are in the pool)
  - `best_with_transfers(current: dict, pool: dict, prices: dict, budget: float, k: int) -> dict | None`: the best legal team with exactly `k` swaps from `current` (`{"drivers": [5], "constructors": [2]}`), as `{"drivers", "constructors", "swaps": [{"out": str, "in": str, "kind": "driver" | "constructor"}], "boost", "expected", "cost"}`, or None if no legal team
  - `transfer_ladder(current: dict, pool: dict, prices: dict, budget: float, free_transfers: int, session: str = "FP3") -> dict`: `{"rows": [...], "facts": [str], "missing": [str]}`. Each row: `{"transfers": k, "paid": max(0, k - free), "drivers", "constructors", "swaps" (each with a "reason" str), "boost", "expected" (after hits), "vs_keep", "cost"}` or `{"transfers": k, "paid": ..., "none": True}` when no legal team.

- [ ] **Step 1: Confirm the rollover rule.** Read the official 2026 F1 Fantasy rules (fantasy.formula1.com game rules / FAQ, free) for how unused free transfers carry over and the cap. Set `MAX_FREE_TRANSFERS` from it with a comment quoting where it came from and the date. If the rule isn't "2 a race, unused carry over, cap 3", stop and tell Ashen before going on: the facts and the replay depend on it.

- [ ] **Step 2: Failing tests** in `tests/test_planner.py`, on a small made up pool (8 drivers on 4 teams with known `FantasyValue`, `GridPosition`, prices chosen so the answers are obvious by hand):

```python
def test_next_free_transfers_rolls_one_over():
    assert planner.next_free_transfers(2, 1) == 3   # Ashen's case: use 1 of 2, get 3 next week
    assert planner.next_free_transfers(2, 0) == 3   # capped
    assert planner.next_free_transfers(2, 2) == 2
    assert planner.next_free_transfers(2, 3) == 2   # a paid one doesn't make it worse

def test_keep_row_is_your_team_with_its_2x(): ...            # row 0 == current team, expected = 5 + 2 + 2x, vs_keep 0
def test_best_with_transfers_takes_the_best_swap(): ...      # k=1 on a hand made pool, exact out/in asserted
def test_rows_are_independent_not_nested(): ...              # pool where the best pair doesn't contain the best single swap; row 2's swaps asserted
def test_paid_row_has_the_hit_taken_off(): ...               # free=2: row 3 expected == its team's expected - 10, paid == 1
def test_no_paid_row_when_switched_off(monkeypatch): ...     # SHOW_PAID_ROW False -> rows 0..free only, and the facts still say "Transfer 3 costs -10."
def test_ladder_rows_stay_within_budget_even_if_keep_does_not(): ...
def test_best_with_transfers_never_repeats_a_pick(): ...
def test_ladder_flags_a_driver_not_in_this_weekends_field(): ...   # "GONE" in missing, scores 0, a fact contains "GONE"
def test_swaps_say_why_in_practice_positions(): ...          # driver: "PER P19 to BOR P9 in FP3"; constructor: "Haas P14 and P17 to Mercedes P2 and P4 in FP3"
def test_facts_are_facts_not_orders(): ...                   # see below
```

`test_facts_are_facts_not_orders` asserts, for a hand made ladder with free=2 where row 2 is highest and the 2nd transfer adds +3: the facts include `"The highest expected total is with 2 transfers (211)."`, `"Transfer 2 adds +3."`, `"Skip transfer 2 and you'd have 3 free transfers next week."`, `"Transfer 3 adds +6 but costs -10."`, and no fact contains "should", "do this" or "recommend". (Use the pool's real numbers in place of 211 / +3 / +6.)

- [ ] **Step 3: Run**, expect FAIL (no module).
- [ ] **Step 4: Implement `src/planner.py`.** Brute force: for exactly k swaps, every split into a driver swaps and k-a constructor swaps (constructors at most 2), every choice of who goes out and who comes in from the pool (drivers not already in the team), keep the legal ones within budget, best by `expected` (ties to the cheaper team). Score with `score_team`. The reasons use `GridPosition` from the pool and the `session` argument.
- [ ] **Step 5: Run**, expect PASS, then the full suite green.
- [ ] **Step 6: Commit.** Files: `src/planner.py`, `tests/test_planner.py`. Summary `the transfer ladder maths, facts not orders`.

---

### Task 2: Prove it on real points (stop and show Ashen)

**Files:**
- Create: `src/planner_replay.py`, `scripts/planner_grade.py`, `tests/test_planner_replay.py`
- Modify: `src/backtest.py` (add `predicted_for_round`, leave `run_backtest` alone), `src/planner.py` (`SHOW_PAID_ROW` value and its measured comment)

**Interfaces:**
- Consumes: Task 1's `transfer_ladder`, `team_cost`, `next_free_transfers`, `TRANSFER_HIT`; `team_points` and `load_official_points` from `src/official_points.py`; `deadline_grid`, `_predict_race` from `src/backtest.py`; `get_race_pool`, `build_budget_teams` from `src/fantasy.py`.
- Produces:
  - `src/backtest.py`: `predicted_for_round(rnd: int, df_previous: pd.DataFrame, df_current: pd.DataFrame) -> tuple[str, pd.DataFrame | None, str | None]`: (race name, the walk forward predicted table for that round from the deadline grid, session used), the same steps `run_backtest` does for one round with `use_practice=True`.
  - `src/planner_replay.py`: `play_season(rounds: list[dict], start: dict, start_bank: float, strategy: str) -> dict`. Each round dict: `{"round": int, "pool": dict | None, "prices": dict, "points": dict}` (points = that round's official points). `strategy` is `"keep"`, `"free_only"` or `"with_hits"`. Returns `{"per_round": [{"round", "points", "transfers", "paid", "free_before"}], "average": float, "hits": int}`.
- Rules in `play_season`: the first round scores the start team with no transfers. From the second round, free transfers start at `FREE_PER_RACE` and follow `next_free_transfers`. Budget each round = `team_cost(current team, that round's prices) + bank`, bank after = budget - cost of the new team. `keep` never transfers (its 2x is still picked each round from the pool). `free_only` takes the highest `expected` row with `paid == 0`. `with_hits` takes the highest `expected` row of all, the paid row computed even if `SHOW_PAID_ROW` is False. Real points per round = `team_points(...)` of the team and its 2x minus `TRANSFER_HIT` per paid transfer. A round with `pool` None keeps the team and its last 2x.

- [ ] **Step 1: Failing tests** in `tests/test_planner_replay.py`, 3 made up rounds:

```python
def test_keep_never_changes_the_team(): ...
def test_free_only_never_pays_a_hit(): ...
def test_with_hits_pays_when_the_paid_row_is_highest(): ...   # points that round = team_points - 10
def test_rollover_gives_three_after_using_one(): ...          # free_before goes 2 -> 3
def test_budget_follows_team_value_plus_bank(): ...           # a price rise lets a kept team stay legal and the bank carries
def test_round_without_a_pool_keeps_the_team(): ...
```

- [ ] **Step 2: Run**, FAIL. **Step 3: Implement** `play_season` and `predicted_for_round`. **Step 4: Run**, PASS, full suite green.
- [ ] **Step 5: The grade script.** `scripts/planner_grade.py` builds rounds 3 to 18 of 2026 with `predicted_for_round` + `get_race_pool` (prices from `official[rnd]["prices"]`), starts from PitWall's team 1 at R3 (`build_budget_teams(...)[0]`, $100M, bank = 100 - its cost), plays all three strategies and prints a markdown table: average real points per race, races won head to head (free only vs keep, with hits vs free only), hits paid. It also prints a line if any round fell back from the deadline session (re-run if so, OpenF1 sometimes drops a session).
- [ ] **Step 6: Run it.** Expected: three averages and two head to heads, all 16 rounds present.
- [ ] **Step 7: STOP and show Ashen the table.** The two bars from the spec: (1) free only must beat keep, or the project stops here and the result gets written down; (2) with hits must beat free only, or `SHOW_PAID_ROW = False`. Write the numbers in the comment above `SHOW_PAID_ROW`, like the project 2 switches.
- [ ] **Step 8: Commit.** Files: the new files, `src/backtest.py`, `src/planner.py`. Summary `planner graded on real points`. Description: the table.

---

### Task 3: The endpoint

**Files:**
- Create: `src/api/planner.py`
- Modify: `src/api/schemas.py`, `main.py` (add `planner` to the router loop), `tests/test_endpoints.py`

**Interfaces:**
- Consumes: Task 1's `transfer_ladder`, `MAX_FREE_TRANSFERS`. The live forecast path the Manual Team page uses (`predict_upcoming_race`, `get_race_pool(..., dnf_probs=upcoming_dnf_probs(...))`, `state.current_prices`), `find_snapshot` for the locked session, `weekend_grid` / `first_available_practice` for the grid.
- Produces: `POST /transfer-ladder` with `TransferLadderRequest(race_name: str, drivers: list[str], constructors: list[str], budget: float, free_transfers: int)` (pydantic: exactly 5 drivers, 2 constructors, `1 <= free_transfers <= MAX_FREE_TRANSFERS`, else 422). Response: `{"race_name", "session_used", "provisional": bool, **transfer_ladder(...)}`. Locked weekend: the snapshot's `session_used` and `provisional: False`. Not locked: the latest available session, `provisional: True`. No practice yet: 400 with a plain message.

- [ ] **Step 1: Failing tests** in `tests/test_endpoints.py` (same `client` fixture, Madring is locked in the frozen snapshots):

```python
def test_transfer_ladder_uses_the_locked_session(client):
    r = client.post("/transfer-ladder", json={"race_name": MADRING, "drivers": MADRING_TEAM_DRIVERS,
        "constructors": MADRING_TEAM_CONSTRUCTORS, "budget": 100.0, "free_transfers": 2})
    body = r.json()
    assert r.status_code == 200 and body["provisional"] is False and body["session_used"] == "FP3"
    assert [row["transfers"] for row in body["rows"]] == [0, 1, 2, 3]
    assert body["rows"][0]["vs_keep"] == 0

def test_transfer_ladder_matches_the_manual_team_numbers(client): ...   # each pick's FantasyValue/score in a row equals /upcoming-race-pool's for the same race and session
def test_transfer_ladder_refuses_bad_free_transfers(client): ...        # free_transfers 0 and MAX+1 -> 422; 4 drivers -> 422
```

- [ ] **Step 2: Run**, FAIL (404). **Step 3: Implement.** **Step 4: Run**, PASS, full suite green, existing goldens untouched.
- [ ] **Step 5: Commit** (backend, Monday to Thursday only). Files: `src/api/planner.py`, `src/api/schemas.py`, `main.py`, `tests/test_endpoints.py`. Summary `transfer ladder endpoint`.

---

### Task 4: The page, with 3 saved teams

**Files:**
- Create: `frontend/src/components/myteam/TransferPlanner.jsx`, `frontend/src/plannerTeams.js`
- Modify: `frontend/src/App.jsx` (a "Planner" tab in `MYTEAM_TABS`, rendered like `ManualTeamBuilder`)

**Interfaces:**
- Consumes: Task 3's `POST /transfer-ladder`, `GET /prices` for the pickers, `upcomingRaces` the way `ManualTeamBuilder` gets them.
- Produces: `plannerTeams.js` with `loadTeams() -> [team, team, team]` and `saveTeams(teams)`, localStorage key `pitwall_planner_teams`, each team `{name, drivers: [5], constructors: [2], budget, freeTransfers}`. Bad or missing storage gives 3 empty teams, never a crash (same try/catch care as `teamCache.js`).

- [ ] **Step 1: The storage helper** `plannerTeams.js` (no frontend test runner exists, so check it by hand in Step 4).
- [ ] **Step 2: The page.** Team 1/2/3 switcher with an editable name, pickers for 5 drivers and 2 constructors from the current price list, budget and free transfers inputs (1 to the cap), then the ladder table (layout A from the mockup: Transfers, Change, Expected, vs keeping), each swap's reason under it, the facts list under the table, the 2x per row, a "provisional, locks after FP3" note when `provisional`, and the missing picks called out. Plain labels: "Keep your team", "1 transfer", "2 transfers (both free)", "3 transfers (one costs -10)". Totals labelled as including the 2x.
- [ ] **Step 3: Wire the tab** in `App.jsx`.
- [ ] **Step 4: Check.** `npm run build` passes, `npm run lint` shows no new errors. Run backend and frontend locally, enter Ashen's US GP team (LEC 2x, ANT, LIN, HUL, PER, Ferrari, Haas), switch teams, reload the page (teams still there), put junk in `pitwall_planner_teams` (page still loads with empty teams).
- [ ] **Step 5: Commit** (frontend only, any day). Summary `planner page with 3 saved teams`.

---

### Task 5: Notes

**Files:**
- Create: `Fantasy Predictor/Planner.md`
- Modify: `Fantasy Predictor/README.md` (link Planner), `Roadmap.md` (project 3 done, the graded numbers), `API.md` (`/transfer-ladder`), `Frontend.md` (the Planner tab, `pitwall_planner_teams`), `Decisions and evidence.md` (the two bars and their numbers), `README.md` (repo, a short Planner section)

- [ ] **Step 1:** Write how the ladder works, the confirmed rollover rule and where it came from, the graded numbers, and what's left for the redesign (labels Ashen found confusing at first glance). Vault lint 0 errors, full suite green (the dash test covers the notes).
- [ ] **Step 2: Commit.** Summary `notes for the planner`.
