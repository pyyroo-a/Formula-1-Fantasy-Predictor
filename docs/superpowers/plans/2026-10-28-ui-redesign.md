# The one UI redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the whole PitWall site one look (dark timing tower, Archivo), working on a
phone, with the page changes from the design, and fix the broken Practice endpoint.

**Architecture:** Shared look pieces go in `frontend/src/ui/`, pure logic (grouping,
sorting, labels, maths for display) goes in `frontend/src/lib/` with tests run by Node's
own test runner (no new npm package). Pages are rebuilt one task each on top of those.
The one backend task switches `/practice-results` to OpenF1 like the model already is.

**Tech Stack:** React 19, Vite 8, Tailwind 3, Node 22 `node --test`; FastAPI, pytest.

**Spec:** `docs/superpowers/specs/2026-10-28-ui-redesign-design.md` (read it with the
mockups in `docs/superpowers/specs/2026-10-28-ui-redesign-mockups/`).

## Global Constraints

- No change to any number, pick, 2x pick, chip verdict, confidence level or rounding rule. Show what the server sends.
- No new backend endpoints. No new npm packages. Archivo comes from Google Fonts: `family=Archivo:wdth,wght@62..125,400..800`.
- Colours: bg `#0F1217`, panel `#141821`, raised `#181C24`, line `#1E232C`/`#232833`, text `#E9ECF1`, muted `#8B93A3`, red `#FF4D4D`, safe `#5BE38A`, caution `#F2C94C`, low `#FF7A7A`, info `#7FA6FF`. Chart: PitWall `#F0504F`, FP3 order `#5B8DEF`, most expensive `#B08A22`.
- Works at 375px wide with no sideways scroll and no badly wrapped names.
- Sentence case labels, no letter spaced all caps (except the logo and verdict tags).
- No em or en dashes anywhere (`tests/test_no_dashes.py`). Comments in Ashen's plain casual voice.
- localStorage keys and shapes unchanged: `pitwall_planner_teams`, `pitwall_budget`, `pitwall_last_team`.
- Checks for every task: `cd frontend && npm run build` passes, `npm run lint` has no more than the 7 old errors, `npm test` passes; backend `./venv/Scripts/python.exe -m pytest -q` passes.
- **Never git commit or push.** At the end of each task give Ashen the files to tick in GitHub Desktop, a Summary and a Description, then wait for "committed".
- Task 1 (backend) must be pushed before FP1 on Friday 30 Oct, or wait until the Mexico race is over. The rest can go any day.

## Review Focus

1. **The server answers with a non JSON page** (a Render 500 "Internal Server Error", or asleep). Expect a plain error line, never a black page. Pinned by `fetchJson` tests (Task 2) and the error boundary (Task 2).
2. **A saved Garage team with a driver who isn't in the price list any more** (an old code like `DOO`). Expect it kept and shown as "not in the price list", never silently dropped. Pinned in Task 5 (`teamFromSaved` test).
3. **A weekend with no confidence** (sprint weekend, old snapshot). Expect no pills and no key line at all. Pinned in Task 3 (`showConfidenceKey` test).
4. **A ladder row that says `none: true`** (no team fits the budget with that many transfers). Expect that step to say "no team fits your budget", not a 0 or broken bar. Pinned in Task 5 (`ladderSteps` test).
5. **Missing numbers** (Crowd `null`, a quali time `null`, points `null`). Expect a plain "-" or the row left out, never "NaN" or "null". Pinned in Task 2 (`fmt1`) and Task 7 (`raceVerdict`).

---

### Task 1: Practice from OpenF1 (backend)

**Files:**
- Modify: `src/openf1.py` (add the practice table, share the session lookup and a raw laps cache)
- Modify: `src/api/races.py:201-280` (`get_practice_results` tries OpenF1 first)
- Test: `tests/test_openf1.py`

**Interfaces:**
- Produces: `openf1.practice_table(laps: list, drivers: list) -> list[dict]`, rows with `Position`, `Abbreviation`, `FullName`, `TeamName`, `LapTime` (`"1:34.900"`), `GapToPole` (seconds, 3 dp), fastest first.
- Produces: `openf1.openf1_practice(year: int, race_name: str, session: str, start_utc, now=None) -> list[dict]`, raises `NotPublishedYet` / `OpenF1Unavailable` exactly like `openf1_grid`.
- The endpoint's response shape stays `{"session", "available_sessions", "results"}`.

- [ ] **Step 1: Write the failing tests** in `tests/test_openf1.py`, reusing `LAPS`, `DRIVERS`, `_session`, `START`. Add `first_name` and `last_name` to each entry in `DRIVERS` (`"Charles"`, `"Leclerc"` etc.; OpenF1's `full_name` is `"Charles LECLERC"` style, so we build the name from the two parts instead; `grid_from_openf1` ignores the extra keys).

```python
def test_practice_table_rows_like_the_page_expects():
    rows = of1.practice_table(LAPS, DRIVERS)
    assert [r["Abbreviation"] for r in rows] == ["LEC", "ANT", "VER", "HAM"]
    assert rows[0] == {"Position": 1, "Abbreviation": "LEC", "FullName": "Charles Leclerc",
                       "TeamName": "Ferrari", "LapTime": "1:34.900", "GapToPole": 0.0}
    assert rows[1]["GapToPole"] == 0.11
    assert rows[3]["LapTime"] == "1:35.700"

def test_practice_table_with_no_timed_laps_is_not_published():
    with pytest.raises(of1.NotPublishedYet):
        of1.practice_table([{"driver_number": 16, "lap_duration": None}], DRIVERS)

def test_openf1_practice_fetches_once_and_reuses(monkeypatch):
    # fake _get: sessions -> [_session()], laps -> LAPS, drivers -> DRIVERS, counting laps calls
    # USE_OPENF1=1 for this test, now = START + 2h
    # call openf1_practice twice -> same rows, laps fetched once
    ...

def test_openf1_practice_unfinished_session_is_not_published(monkeypatch):
    # now = START + 10 min -> raises NotPublishedYet
    ...
```

The two `...` tests follow the fake `_get` pattern the file already uses for `openf1_grid`; copy it, don't invent a new one. Call `of1.clear_caches()` first in each.

Add an endpoint test in `tests/test_openf1.py`:

```python
def test_practice_endpoint_uses_openf1_when_it_has_the_session(monkeypatch, client):
    # monkeypatch src.api.races so fastf1.get_event(...) returns an event whose Session1..3
    # are "Practice 1/2/3", and openf1.openf1_practice returns two fake rows
    # POST /practice-results {"race_name": "United States Grand Prix", "session": "FP3"}
    # -> 200, session "FP3", available_sessions ["FP1","FP2","FP3"], results == the fake rows
    ...

def test_practice_endpoint_says_not_over_yet(monkeypatch, client):
    # openf1_practice raises NotPublishedYet("... isn't over yet") -> 404 with that detail
    ...
```

Use the `client` fixture from `conftest.py`.

- [ ] **Step 2: Run them to see them fail**

Run: `./venv/Scripts/python.exe -m pytest -q tests/test_openf1.py`
Expected: FAIL, `practice_table` / `openf1_practice` not defined.

- [ ] **Step 3: Implement in `src/openf1.py`**

`practice_table` ranks like `grid_from_openf1` (fastest lap per `driver_number`, merged with `name_acronym`, `team_name`, `first_name`, `last_name`), formats `LapTime` as `m:ss.mmm`, team names through `normalize_team_names` like the grid. `FullName` is `"{first_name} {last_name}"`, the acronym when either is missing. Pull the "find the session, check it's over" part of `openf1_grid` into one private helper both use, and cache the raw `(laps, drivers)` per `session_key` so the grid and the table share one download (keep `_grid_cache` behaviour for the grid, `clear_caches` clears the new cache too).

- [ ] **Step 4: Implement in `src/api/races.py`**

Keep the `available` sessions part (FastF1's schedule still loads). Then: `start = fetch_practice._session_start_utc(year, race_name, openf1.SESSION_NAMES[session_name])`, try `openf1.openf1_practice(...)`; `NotPublishedYet` -> `HTTPException(404, detail=str(e))`; `OpenF1Unavailable` -> the existing FastF1 code, moved into a private `_fastf1_practice_rows(year, race_name, session_name)` (unchanged behaviour, so the goldens with `USE_OPENF1=0` stay the same). Comment in Ashen's voice why (F1TV login, same as the model).

- [ ] **Step 5: Run all backend tests**

Run: `./venv/Scripts/python.exe -m pytest -q`
Expected: all pass (205 old plus the new ones), the `practice_results_madring_*` goldens unchanged.

- [ ] **Step 6: Check it against the live data locally**

Run the backend locally (How-tos.md "run it locally") and `POST /practice-results` for the United States Grand Prix with `"session": "FP3"`. Expected: 200, 22 rows, LEC P1 (the same order `/weekend-finishes` lists as `baseline_pos`). Show Ashen the first 5 rows.

- [ ] **Step 7: Hand over the commit**

Files: `src/openf1.py`, `src/api/races.py`, `tests/test_openf1.py`. Summary: `practice page gets its laps from OpenF1`. Description in Ashen's voice: the page still asked FastF1, which needs an F1TV login since October, so it answered 500 for every race; now it uses OpenF1 like the model, FastF1 only as the backup. Remind him: push before FP1 Friday or after the race. Wait for "committed".

---

### Task 2: The look, the shell and the shared pieces

**Files:**
- Modify: `frontend/index.html` (Google Fonts link), `frontend/tailwind.config.js` (new `pw` colours, `fontFamily.sans` Archivo, drop the mono default), `frontend/src/index.css` (body font and colours, no monospace), `frontend/package.json` (`"test": "node --test \"src/lib/*.test.js\""`)
- Create: `frontend/src/lib/format.js`, `frontend/src/lib/format.test.js`, `frontend/src/lib/api.js`, `frontend/src/lib/api.test.js`
- Create: `frontend/src/ui/` with `Switcher.jsx`, `TowerRow.jsx`, `Confidence.jsx`, `StatBox.jsx`, `VerdictTag.jsx`, `Panel.jsx`, `Loading.jsx`, `ErrorBoundary.jsx`
- Modify: `frontend/src/App.jsx` (header, nav, phone bottom bar, sub tabs, error boundary round the page, drop the Team Optimizer tab)
- Delete: `frontend/src/components/myteam/TeamOptimizerTab.jsx`; remove `useBudgetTeams` from `hooks/useRaceData.js` if nothing else uses it
- Modify: `frontend/src/styles.js` (new input, button and heading classes)

**Interfaces (Produces):**
- `fmt1(n: number|null|undefined) -> string`: one decimal, `"-"` for null/undefined/NaN. `money(n) -> "$24.1M"`, `"-"` for missing. `pts(n) -> "38.0 pts"`.
- `surname(code: string) -> string`: last word of `DRIVER_NAMES[code]`, the code itself if unknown.
- `fetchJson(url: string, options?: object) -> Promise<{ok: true, data} | {ok: false, error: string}>`. Never throws. `error` is the server's `detail` when it's a string, `"The server sent something odd (HTTP 500). It might be waking up, try again in a minute."` when the body isn't JSON, `"Couldn't reach the server. It might be waking up, try again in a minute."` on a network failure.
- `verdictLabel(rec: string) -> string`: `"POST-QUALI"` -> `"AFTER QUALI"`, others unchanged. Lives in `lib/format.js`.
- UI pieces (props): `Switcher({options: [{id, label, sub?}], value, onChange})`, `TowerRow({spot, color, name, sub, right, rightSub, faded?, onClick?})`, `ConfidencePill({level})`, `ConfidenceKey({short?})`, `StatBox({label, value, sub?})`, `VerdictTag({rec})`, `Panel({title?, children})`, `Loading({text})` (grey blocks plus the line), `ErrorBoundary({children})`.

- [ ] **Step 1: Write the failing tests** `src/lib/format.test.js` and `src/lib/api.test.js` (`import { test } from "node:test"; import assert from "node:assert/strict";`):

```js
test("fmt1 always shows one decimal", () => {
  assert.equal(fmt1(38), "38.0"); assert.equal(fmt1(-3.7), "-3.7"); assert.equal(fmt1(0), "0.0");
});
test("fmt1 shows a plain dash for missing numbers", () => {
  for (const v of [null, undefined, NaN]) assert.equal(fmt1(v), "-");
});
test("money and pts", () => {
  assert.equal(money(3), "$3.0M"); assert.equal(money(24.1), "$24.1M"); assert.equal(pts(-3.7), "-3.7 pts");
});
test("surname", () => {
  assert.equal(surname("HUL"), "Hülkenberg"); assert.equal(surname("ANT"), "Antonelli"); assert.equal(surname("XYZ"), "XYZ");
});
test("verdictLabel", () => {
  assert.equal(verdictLabel("POST-QUALI"), "AFTER QUALI"); assert.equal(verdictLabel("PLAY"), "PLAY");
});
// api.test.js: pass a fake fetch as options.fetchImpl
test("fetchJson gives the data", ...);              // 200 + JSON -> {ok:true, data}
test("fetchJson gives the server's detail", ...);   // 400 {"detail":"No practice data yet..."} -> {ok:false, error:"No practice data yet..."}
test("fetchJson survives an HTML 500", ...);        // 500 body "Internal Server Error" -> the "sent something odd (HTTP 500)" text
test("fetchJson survives a network failure", ...);  // fetchImpl rejects -> the "Couldn't reach the server" text
```

`fetchJson` takes `options.fetchImpl` (default `fetch`) so the tests need no network. `lib/` files must not import anything that uses `import.meta.env` (so `api.js` takes full URLs; callers pass `${API}/...`).

- [ ] **Step 2: Run them to see them fail**

Run: `cd frontend && npm test`
Expected: FAIL, modules not found.

- [ ] **Step 3: Implement `lib/format.js` and `lib/api.js`**, then the `ui/` pieces from the Interfaces above and the look in the Global Constraints. `ErrorBoundary` is a small class component: on a render error it shows "Something on this page broke. Try another tab or reload." plus the error message, so a crash is never a black page. `TowerRow` keeps the right column fixed width and lets the name truncate only as a last resort. `ConfidenceKey` copy: long "How sure we are about the predicted spot: high, medium, low (about the spot, not whether he's a good pick)", short "high, medium, low = how sure we are about the spot". Move `ConfidencePill` out of `BudgetTeam.jsx` into `ui/Confidence.jsx` and re-export or update its imports.

- [ ] **Step 4: Restyle `App.jsx`**

Header: `PITWALL` logo, the four sections (sentence case: Overview, My team, Race data, Insights), the countdown. Below `sm`: the sections move to a fixed bottom bar, the page gets bottom padding so nothing hides under it. Sub tabs: My team = `manual` "Manual team", `planner` "Garage" (keep the ids for now, Task 5 swaps the content), and leave the Chip advisor tab in until Task 5. Default `myTeamTab` becomes `"manual"`. Wrap `<main>` in `ErrorBoundary`. Remove the Team Optimizer tab, its import and the `budget` hook. Other pages keep their old insides for now (they get rebuilt in later tasks).

- [ ] **Step 5: Run the checks**

Run: `cd frontend && npm test && npm run build && npm run lint`
Expected: tests pass, build passes, lint shows only the 7 old errors.

- [ ] **Step 6: Look at it**

Create `frontend/.env.local` (already gitignored) with `VITE_API_URL=https://formula-1-fantasy-predictor.onrender.com`, add a `.claude/launch.json` entry for `npm run dev` in `frontend` (port 5173), open it in the browser pane at desktop and at 375 x 812 (`resize_window` mobile). Screenshot the header and the bottom bar for Ashen. Reset the size after.

- [ ] **Step 7: Hand over the commit** (all files above, plus the deleted optimizer file). Summary: `new look: Archivo, the colours, the shell and the shared pieces`. Wait for "committed".

---

### Task 3: Overview

**Files:**
- Modify: `frontend/src/components/Overview.jsx`, `AutoChipAdvisor.jsx`, `WeatherWidget.jsx`, `CountdownWidget.jsx`, `BudgetTeam.jsx` (whatever Overview still uses)
- Create: `frontend/src/lib/overview.js`, `frontend/src/lib/overview.test.js`

**Interfaces:**
- Consumes: `ui/*`, `fmt1`, `money`, `verdictLabel`, `displayCategory` (`confidence.js`).
- Produces: `showConfidenceKey(drivers: object[]) -> boolean` (true only if any driver has `Confidence`); `finishLine(p: {model_pos, actual_pos, actual_status}, resultsAvailable: boolean) -> {spot: "P1", finished: "finished P2" | "DNF" | null, close: boolean}` (`finished` is null unless `resultsAvailable`; `close` means within 1 place).

- [ ] **Step 1: Write the failing tests** in `overview.test.js`:

```js
test("no key when nobody has a confidence", () => {
  assert.equal(showConfidenceKey([{Abbreviation: "LEC"}, {Abbreviation: "HAM", Confidence: null}]), false);
  assert.equal(showConfidenceKey([{Confidence: "high"}]), true);
  assert.equal(showConfidenceKey(undefined), false);
});
test("finishLine hides the real result until results are in", () => {
  assert.deepEqual(finishLine({model_pos: 1, actual_pos: 2, actual_status: "Finished"}, false),
                   {spot: "P1", finished: null, close: false});
});
test("finishLine after the race", () => {
  assert.deepEqual(finishLine({model_pos: 1, actual_pos: 2, actual_status: "Finished"}, true),
                   {spot: "P1", finished: "finished P2", close: true});
  assert.equal(finishLine({model_pos: 7, actual_pos: 11, actual_status: "Finished"}, true).close, false);
  assert.equal(finishLine({model_pos: 20, actual_pos: null, actual_status: "DNF"}, true).finished, "DNF");
});
```

- [ ] **Step 2: Run to see them fail** (`npm test`, expected FAIL: not defined).

- [ ] **Step 3: Implement `lib/overview.js`, then rebuild `Overview.jsx`** per the spec's Overview section and mockup 1: hold banner, big race name with round and lock line, Team 1/2/3 `Switcher`, the new 2x box (`boost_pick` name via `DRIVER_NAMES`, its `reason` as sent), `ConfidenceKey` only when `showConfidenceKey`, the team as `TowerRow`s (predicted spot, team colour, full name, team and pill, price over points), the constructors, the three `StatBox`es (expected points, cost, left over), chips in a 3 by 2 grid with `VerdictTag`, then the right column (predicted finish with `finishLine` and the existing arrow as a small marker, driver prices, constructor prices). Every state that exists today (live, provisional, locked, held, loading, error) still shows, with today's wording made plain.

- [ ] **Step 4: Run the checks** (`npm test && npm run build && npm run lint`, same expectations as Task 2).

- [ ] **Step 5: Look at it**: desktop and 375px, the held US GP team, all three teams. Compare every number on Team 1, 2 and 3 with the live site (https://formula-1-fantasy-predictor.vercel.app) before handing over: prices, points, totals, chips, predicted finish. Screenshots for Ashen.

- [ ] **Step 6: Hand over the commit.** Summary: `overview redesign: 2x box, confidence key, finished P2 after the race`. Wait for "committed".

---

### Task 4: Manual team and the shared picker

**Files:**
- Modify: `frontend/src/components/ManualTeamBuilder.jsx`, `ManualTeamParts.jsx`
- Create: `frontend/src/ui/TeamPicker.jsx`, `frontend/src/lib/picker.js`, `frontend/src/lib/picker.test.js`

**Interfaces:**
- Produces: `groupByTeam(drivers: {Abbreviation, TeamName}[]) -> {team: string, drivers: object[]}[]`, teams A to Z by name, drivers inside a team in the order given; a driver with no team goes in a last group `"Other"`.
- Produces: `sortDrivers(drivers, by: "team"|"points"|"price") -> object[]` (points uses `FantasyValue` high to low, price uses `Price` high to low, ties by surname).
- Produces: `sortConstructors(constructors: {name}[]) -> object[]` A to Z.
- Produces: `pickTeam1(weekendTeam, pool) -> {drivers: object[], constructors: object[]}`: the pool entries matching Team 1's codes and constructor names, skipping any not in the pool.
- Produces: `TeamPicker({drivers, constructors, picked: {drivers: string[], constructors: string[]}, onToggleDriver(code), onToggleConstructor(name), sort, onSort, showPoints})`. Drivers have `{Abbreviation, TeamName, Price, FantasyValue?, Predicted?}`, constructors `{name, price, score?}`. Team colour on every card (`teamAccent`).

- [ ] **Step 1: Write the failing tests** in `picker.test.js`:

```js
const D = [{Abbreviation:"LEC",TeamName:"Ferrari",Price:24.4,FantasyValue:38},{Abbreviation:"GAS",TeamName:"Alpine",Price:9.6,FantasyValue:4.6},
           {Abbreviation:"HAM",TeamName:"Ferrari",Price:24.7,FantasyValue:29.7},{Abbreviation:"NEW",TeamName:null,Price:1,FantasyValue:0}];
test("groupByTeam puts teams A to Z and teammates together", () => {
  assert.deepEqual(groupByTeam(D).map(g => [g.team, g.drivers.map(d => d.Abbreviation)]),
                   [["Alpine",["GAS"]],["Ferrari",["LEC","HAM"]],["Other",["NEW"]]]);
});
test("sortDrivers by points and by price", () => {
  assert.deepEqual(sortDrivers(D,"points").map(d=>d.Abbreviation), ["LEC","HAM","GAS","NEW"]);
  assert.deepEqual(sortDrivers(D,"price").map(d=>d.Abbreviation), ["HAM","LEC","GAS","NEW"]);
});
test("constructors A to Z", () => {
  assert.deepEqual(sortConstructors([{name:"Williams"},{name:"Alpine"},{name:"Haas F1 Team"}]).map(c=>c.name), ["Alpine","Haas F1 Team","Williams"]);
});
test("pickTeam1 copies Team 1 and skips what the pool doesn't have", () => {
  const team = {teams:[{drivers:[{Abbreviation:"LEC"},{Abbreviation:"XXX"}],constructors:[{name:"Ferrari"}]}]};
  const pool = {drivers:D, constructors:[{name:"Ferrari",price:28.5,score:71.2}]};
  const r = pickTeam1(team, pool);
  assert.deepEqual(r.drivers.map(d=>d.Abbreviation), ["LEC"]); assert.deepEqual(r.constructors.map(c=>c.name), ["Ferrari"]);
});
```

- [ ] **Step 2: Run to see them fail.**

- [ ] **Step 3: Implement `lib/picker.js` and `ui/TeamPicker.jsx`.**

- [ ] **Step 4: Rebuild `ManualTeamBuilder.jsx`** per the spec's Manual team section and mockup 2 (layout A): race box (defaults to `upcomingRaces[0]`) and budget box side by side; loads by itself: on mount and on race change, fetch sessions, and if any FP is available fetch the pool straight away (same request body as today: FP3, FP1 on sprint weekends); before FP1 the "No practice yet for {race}. This fills in by itself after FP1" line with the existing once a minute check, which now also loads the pool when practice appears. Use `fetchJson`. Then `TeamPicker` (sort By team first), the sticky team panel (a bar stuck to the bottom on a phone, sitting above the section bar), and today's score maths unchanged (my score, vs optimal %, rating, the 2x tag on the highest scorer). "Start from PitWall Team 1" button uses `pickTeam1` with the weekend team App already has (pass it in as a prop); only shown when that team's race is the race picked. The "Load driver pool" button goes.

- [ ] **Step 5: Run the checks.**

- [ ] **Step 6: Look at it**: Mexico before practice (the "no practice yet" line), and with a race that has practice if one is listed. Desktop and 375px. Compare the score numbers with the live site for the same picks if practice exists. Screenshots.

- [ ] **Step 7: Hand over the commit.** Summary: `manual team loads by itself, drivers by team, constructors A to Z`. Wait for "committed".

---

### Task 5: Garage (Planner and Chip Advisor in one)

**Files:**
- Create: `frontend/src/components/myteam/Garage.jsx`, `frontend/src/components/myteam/GarageEditor.jsx`, `frontend/src/lib/garage.js`, `frontend/src/lib/garage.test.js`
- Modify: `frontend/src/App.jsx` (Garage tab, drop the Chip advisor tab, pass `finishes`)
- Delete: `frontend/src/components/ChipAdvisor.jsx`, `frontend/src/components/myteam/TransferPlanner.jsx`
- Keep: `frontend/src/plannerTeams.js` (same key, same shape)

**Interfaces:**
- Consumes: `TeamPicker`, `groupByTeam`, `sortConstructors` (Task 4), `fetchJson`, `ui/*`, `loadTeams` / `saveTeams` / `emptyTeam`.
- Produces: `driverTeamMap(finishes) -> {[code]: team}` from `finishes.predictions[].{abbreviation, team}`, `{}` when missing.
- Produces: `pickerDrivers(prices, teamMap) -> {Abbreviation, TeamName, Price}[]` for every code in `prices.drivers`; `TeamName` null when not in the map (so it lands in "Other").
- Produces: `teamFromSaved(saved, prices) -> {drivers: {code, known: boolean}[], constructors: {name, known: boolean}[]}`, keeping codes and names that aren't in `prices` with `known: false`.
- Produces: `isComplete(team) -> boolean` (5 drivers, 2 constructors, all non empty).
- Produces: `ladderSteps(rows: object[]) -> {transfers, label, sub, expected: number|null, vsKeep: number|null, best: boolean, height: number, none: boolean}[]`. `expected` is `Math.round(row.expected)`, `vsKeep` is `Math.round(row.expected) - Math.round(rows[0].expected)` (null for the keep row and `none` rows), `best` is true on the highest rounded `expected` (first one wins a tie), `height` is that step's expected over the highest, from 0.4 to 1 (so Keep never vanishes), `none` rows get `height` 0.4, `expected` null.
- Produces: `stepLabel(row, free) -> {label, sub}`: `{ "Keep your team", "no changes" }`, `{ "1 transfer", "free" }`, `{ "2 transfers", "both free" }`, `{ "3 transfers", "all 3 free" }`, a paid row `{ "N transfers", "one costs 10 points" }`. Phone short labels are the component's job.
- Produces: `chipOrder(chips) -> [key, data][]`: PLAY first, then CONSIDER, then the rest, inside each in `CHIP_META` order, skipping `my_team_score`.

- [ ] **Step 1: Write the failing tests** in `garage.test.js` with the real US GP answers from the spec's brainstorm (example team ANT, HAM, HUL, GAS, BOT, Mercedes, Cadillac, $110M):

```js
const ROWS = [{transfers:0,paid:0,expected:128.2},{transfers:1,paid:0,expected:155.0},
              {transfers:2,paid:0,expected:188.5},{transfers:3,paid:0,expected:205.1}];
test("ladderSteps rounds like today's ladder", () => {
  const s = ladderSteps(ROWS);
  assert.deepEqual(s.map(x => x.expected), [128,155,189,205]);
  assert.deepEqual(s.map(x => x.vsKeep), [null,27,61,77]);
  assert.deepEqual(s.map(x => x.best), [false,false,false,true]);
  assert.equal(s[3].height, 1); assert.ok(s[0].height >= 0.4 && s[0].height < 1);
});
test("a row where no team fits", () => {
  const s = ladderSteps([{transfers:0,paid:0,expected:128.2},{transfers:1,paid:0,none:true}]);
  assert.equal(s[1].none, true); assert.equal(s[1].expected, null); assert.equal(s[1].vsKeep, null); assert.equal(s[0].best, true);
});
test("stepLabel says it plainly", () => {
  assert.deepEqual(stepLabel({transfers:0,paid:0},2), {label:"Keep your team", sub:"no changes"});
  assert.deepEqual(stepLabel({transfers:2,paid:0},2), {label:"2 transfers", sub:"both free"});
  assert.deepEqual(stepLabel({transfers:1,paid:0},2), {label:"1 transfer", sub:"free"});
  assert.deepEqual(stepLabel({transfers:3,paid:0},3), {label:"3 transfers", sub:"all 3 free"});
  assert.deepEqual(stepLabel({transfers:3,paid:1},2), {label:"3 transfers", sub:"one costs 10 points"});
});
test("teamFromSaved keeps a driver who left the price list", () => {
  const prices = {drivers:{LEC:24.4}, constructors:{Ferrari:28.5}};
  const t = teamFromSaved({drivers:["LEC","DOO","","",""], constructors:["Ferrari","RB F1 Team"]}, prices);
  assert.deepEqual(t.drivers.slice(0,2), [{code:"LEC",known:true},{code:"DOO",known:false}]);
  assert.deepEqual(t.constructors[1], {name:"RB F1 Team", known:false});
});
test("driver to team map and the Other group", () => {
  const m = driverTeamMap({predictions:[{abbreviation:"LEC",team:"Ferrari"}]});
  assert.deepEqual(pickerDrivers({drivers:{LEC:24.4,NEW:1}}, m).map(d=>[d.Abbreviation,d.TeamName]), [["LEC","Ferrari"],["NEW",null]]);
  assert.deepEqual(driverTeamMap(null), {});
});
test("chips best first", () => {
  const chips = {my_team_score:98.5, autopilot:{recommendation:"SAVE"}, x3_boost:{recommendation:"CONSIDER"},
                 limitless:{recommendation:"PLAY"}, final_fix:{recommendation:"POST-QUALI"}, wildcard:{recommendation:"PLAY"}};
  assert.deepEqual(chipOrder(chips).map(([k]) => k), ["limitless","wildcard","x3_boost","final_fix","autopilot"]);
});
```

- [ ] **Step 2: Run to see them fail.**

- [ ] **Step 3: Implement `lib/garage.js`.**

- [ ] **Step 4: Build `Garage.jsx` and `GarageEditor.jsx`** per the spec's Garage section and mockups 3 and 4: three team slots from `loadTeams()` (empty ones say "Add team", the first visit copy from mockup 4), the editor (name, budget, a 1/2/3 `Switcher` for free transfers with the "You get 2 free transfers a week, pick 3 if you saved one last week" line, `TeamPicker` fed by `pickerDrivers(prices, driverTeamMap(finishes))` and `prices.constructors` A to Z, unknown picks shown as "not in the price list", a bottom bar with 5/5, 2/2 and cost vs budget, "Save team" disabled until `isComplete`), and the results: on save or when a complete team is selected, call `/transfer-ladder` (same body as today's planner) and `/chip-advisor` (`{race_name, my_drivers, my_constructors}` with the saved names, which are the server's own) with `fetchJson`. The steps from `ladderSteps` (tap a step on a phone to show its swaps, all swaps listed on desktop), "Mercedes out, Ferrari in" with the server's `reason`, the 2x, the facts box, then the chips by `chipOrder` with `VerdictTag` and the server's reason and number. "No practice yet, this fills in by itself after FP1" when the answer is a 400 about practice, checking again once a minute; the server's `detail` for any other error. Race box defaults to the next race.

- [ ] **Step 5: Wire it in `App.jsx`**: My team tabs become Manual team and Garage only. Delete `ChipAdvisor.jsx` and `TransferPlanner.jsx`.

- [ ] **Step 6: Run the checks.**

- [ ] **Step 7: Look at it**: empty Garage (clear `pitwall_planner_teams` in the pane only), add the example team, Mexico before practice (the waiting line), then with a race that has practice if one is in `upcomingRaces`, 3 free transfers. Desktop and 375px. Check the ladder and chip numbers match what `/transfer-ladder` and `/chip-advisor` return for the same team (curl them). Screenshots.

- [ ] **Step 8: Hand over the commit** (new files, App.jsx, the two deletions). Summary: `the Garage: your teams, the transfer steps and the chips in one place`. Description mentions the constructor name bug it fixes. Wait for "committed".

---

### Task 6: Race data on one page

**Files:**
- Modify: `frontend/src/hooks/useRaceData.js` (one hook for the page), `frontend/src/App.jsx`
- Create: `frontend/src/components/racedata/RaceDataPage.jsx`, `frontend/src/lib/racedata.js`, `frontend/src/lib/racedata.test.js`
- Delete: `racedata/PracticeTab.jsx`, `QualifyingTab.jsx`, `RaceResultsTab.jsx`, `PracticeTable.jsx`, `QualifyingTable.jsx`, `RaceResultsTable.jsx` once nothing imports them
- Keep: `Backtest.jsx` (dev only, a small "Backtest" switch under the page when `import.meta.env.DEV`)

**Interfaces:**
- Produces: `qualiTag(row: {Q1, Q2, Q3}) -> {time: string, tag: "Q3"|"out in Q2"|"out in Q1"}`; time is the furthest part's time, `"-"` if there are no times at all (tag "out in Q1").
- Produces: `sessionOptions(availablePractice: string[]|null) -> string[]`: `[...availablePractice, "Quali", "Race"]`, with `["FP1","FP2","FP3"]` while it's not known yet.
- Produces: `raceChange(row: {PositionChange, Status, GridPosition}) -> {text: "+2"|"-1"|"same"|"", tone: "up"|"down"|"same"|"none", from: "from P4"|""}`; DNF gives `text ""`, `tone "none"`, keeps `from`.
- Produces: `useRaceWeekend() -> {race, setRace, session, setSession, data, loading, error, available}` called in `App` (so the picked race survives switching away), caching each `race|session` answer so going back to a session doesn't refetch. Picking a race fetches Race (the default view) and Practice auto (for `available_sessions`) together.

- [ ] **Step 1: Write the failing tests** in `racedata.test.js`, using real US GP rows:

```js
test("qualiTag", () => {
  assert.deepEqual(qualiTag({Q1:"1:35.390",Q2:"1:34.278",Q3:"1:34.035"}), {time:"1:34.035", tag:"Q3"});
  assert.deepEqual(qualiTag({Q1:"1:35.662",Q2:"1:35.058",Q3:null}), {time:"1:35.058", tag:"out in Q2"});
  assert.deepEqual(qualiTag({Q1:"1:36.531",Q2:null,Q3:null}), {time:"1:36.531", tag:"out in Q1"});
  assert.deepEqual(qualiTag({Q1:null,Q2:null,Q3:null}), {time:"-", tag:"out in Q1"});
});
test("sessionOptions", () => {
  assert.deepEqual(sessionOptions(null), ["FP1","FP2","FP3","Quali","Race"]);
  assert.deepEqual(sessionOptions(["FP1"]), ["FP1","Quali","Race"]);
});
test("raceChange", () => {
  assert.deepEqual(raceChange({PositionChange:2,Status:"Finished",GridPosition:4}), {text:"+2",tone:"up",from:"from P4"});
  assert.deepEqual(raceChange({PositionChange:-3,Status:"Finished",GridPosition:3}), {text:"-3",tone:"down",from:"from P3"});
  assert.deepEqual(raceChange({PositionChange:0,Status:"Lapped",GridPosition:9}), {text:"same",tone:"same",from:"from P9"});
  assert.deepEqual(raceChange({PositionChange:-1,Status:"DNF",GridPosition:19}), {text:"",tone:"none",from:"from P19"});
});
```

- [ ] **Step 2: Run to see them fail.**

- [ ] **Step 3: Implement `lib/racedata.js` and `useRaceWeekend`.**

- [ ] **Step 4: Build `RaceDataPage.jsx`** per the spec's Race data section and mockup 7: race box, `Switcher` of `sessionOptions`, then `TowerRow`s: practice (best lap, gap `+0.110`, the top lap highlighted), quali (`qualiTag`, tap a row to show all three times), race (`raceChange`, DNFs faded at the bottom as the server already orders them). Errors via `fetchJson` text. Wire it into `App.jsx` (Race data has no sub tabs any more, apart from the dev only Backtest switch).

- [ ] **Step 5: Run the checks.**

- [ ] **Step 6: Look at it**: US GP, Race then Quali then FP3 then back to Race (no refetch), switch to Overview and back (race still picked), a sprint weekend race if one is listed (only FP1 in the strip). If Task 1 isn't deployed yet, Practice shows the server's error line, not a crash; check practice properly against a local backend. Desktop and 375px. Screenshots.

- [ ] **Step 7: Hand over the commit** (new files, hook, App.jsx, deletions). Summary: `race data on one page with a session strip`. Wait for "committed".

---

### Task 7: Insights

**Files:**
- Modify: `frontend/src/components/TrackRecord.jsx`, `PredictedFinishes.jsx`, `ChipHistory.jsx`
- Create: `frontend/src/lib/insights.js`, `frontend/src/lib/insights.test.js`

**Interfaces:**
- Consumes: `finishLine` (Task 3), `fmt1`, `ui/*`, `fetchJson`.
- Produces: `raceVerdict(cells: {Locked, "FP3 order"}) -> {text: "183 lost to FP3's 242" | "145 beat FP3's 129" | "", won: boolean|null}` (empty text and `won` null if either is null). Whole points as sent (`fmt` with no forced decimal is fine here, the server sends 183.0 so show `183`).
- Produces: `honestLine(summary) -> string`: `"Copying the FP3 order scored a bit more so far."` when FP3 order's avg is higher than Locked's, `"PitWall scored more than copying the FP3 order so far."` when lower, `""` if either avg is null.
- Produces: `dotX(value: number, max: number) -> number` (0 to 100, clamps), `chartMax(rows) -> number` (the highest `Hindsight best` rounded up to the next 50).

- [ ] **Step 1: Write the failing tests** in `insights.test.js` with the real `/track-record` rows (R13: Locked 147, FP3 205; R14: 145 vs 129) and summary (Locked 175.2, FP3 order 187.0):

```js
test("raceVerdict", () => {
  assert.deepEqual(raceVerdict({Locked:147,"FP3 order":205}), {text:"147 lost to FP3's 205", won:false});
  assert.deepEqual(raceVerdict({Locked:145,"FP3 order":129}), {text:"145 beat FP3's 129", won:true});
  assert.deepEqual(raceVerdict({Locked:145,"FP3 order":null}), {text:"", won:null});
});
test("honestLine follows the averages", () => {
  assert.equal(honestLine({Locked:{avg:175.2},"FP3 order":{avg:187.0}}), "Copying the FP3 order scored a bit more so far.");
  assert.equal(honestLine({Locked:{avg:190},"FP3 order":{avg:187}}), "PitWall scored more than copying the FP3 order so far.");
  assert.equal(honestLine({Locked:{avg:null},"FP3 order":{avg:187}}), "");
});
test("chart scale", () => {
  assert.equal(chartMax([{cells:{"Hindsight best":428}},{cells:{"Hindsight best":199}}]), 450);
  assert.equal(dotX(225, 450), 50); assert.equal(dotX(999, 450), 100); assert.equal(dotX(-5, 450), 0);
});
```

- [ ] **Step 2: Run to see them fail.**

- [ ] **Step 3: Implement `lib/insights.js`.**

- [ ] **Step 4: Rebuild the three pages** per the spec's Insights section and mockups 5 and 6.
  - Track record: headline, `honestLine` plus today's 28 Oct fixes sentence, four `StatBox`es with "beat it 3 of 6" from `summary`, Crowd's box and dots only when `summary.Crowd.races > 0` (today's note text when not), then one line per race: dots on a 0 to `chartMax` line (PitWall `#F0504F`, FP3 order `#5B8DEF`, most expensive `#B08A22`, a 2px ring in the panel colour round each dot), the best possible as a grey tick, a legend, `raceVerdict` on the right (on a phone above the line), hover and tap show the dot's name and number, and a "Show as a table" toggle with the same numbers as plain text. Phone: boxes 2 by 2.
  - Predicted finishes: rows instead of the table, predicted spot, "practice order P4" under the name, `finishLine` on the right, the accuracy summary restyled, same held and live states.
  - Chips: three cards from `best` (top 3 and worst with small bars, 3x shows each track's `who` from `tracks`), then every track as a list (no sideways table), the existing line each on Wildcard, Final Fix and Auto Pilot, then the folding "How we picked these tracks" box with this copy: "For every track we worked out what the chip would really have been worth there, from the game's official points after the race. Then we ranked the tracks from highest to lowest. The top 3 are shown, plus the lowest so you know where not to use it. Once there's more than one season, each track uses its middle value across seasons, so one wild race can't decide it on its own. The catch: it's one season so far, so we can't check yet if a track that was good for a chip stays good the next year." Track names exactly as the server sends them (the garbled Montreal is a backend fix, not hidden here).

- [ ] **Step 5: Run the checks.**

- [ ] **Step 6: Look at it**: all three tabs, desktop and 375px, every track record number against `/track-record`, hover and tap a dot, the table toggle, fold the box. Screenshots.

- [ ] **Step 7: Hand over the commit.** Summary: `insights redesign: honest track record chart, finishes as rows, chips with how we picked`. Wait for "committed".

---

### Task 8: Tidy up, notes, the final check

**Files:**
- Modify: `Fantasy Predictor/Frontend.md` (pages, files, `ui/` and `lib/`, `npm test`), `Fantasy Predictor/README.md` (where things stand), `Fantasy Predictor/API.md` (`/predict-budget` no longer called by the site; `/practice-results` uses OpenF1), `Fantasy Predictor/Code tour.md` (a short "The redesign" section), `Fantasy Predictor/Roadmap.md` (redesign done, the 2x card idea done, new banked ideas: reasons behind Limitless and No Negative tracks, the garbled Montreal in `chip_history.json`), `Fantasy Predictor/Planner.md` (the planner lives in the Garage now)
- Remove anything now unused (old `BudgetTeam.jsx` parts, `REC_STYLE` / `CAT_BADGE` if unused, old `styles.js` classes) only after a search shows nothing imports them

- [ ] **Step 1: Search for dead code** with Grep for each export in `BudgetTeam.jsx`, `ManualTeamParts.jsx`, `styles.js`, `constants.js`; delete what nothing uses.

- [ ] **Step 2: Update the notes** in Ashen's voice, links relative like the rest of the vault.

- [ ] **Step 3: Run everything**

Run: `cd frontend && npm test && npm run build && npm run lint`, then `./venv/Scripts/python.exe -m pytest -q` from the repo root.
Expected: all pass, lint only the 7 old errors, the no dash test included.

- [ ] **Step 4: The full walk** in the browser pane at desktop and 375 x 812: every section and tab, Overview teams 1 to 3, Manual team, Garage empty and filled, Race data every session, Insights every tab. Check there's no sideways scroll on any page at 375px (`document.documentElement.scrollWidth <= 375` in the javascript tool). Reset the size after. Screenshots for Ashen.

- [ ] **Step 5: One lean fresh reviewer** on the whole change (superpowers:requesting-code-review, one reviewer, most capable model): spec coverage, the Review Focus list, numbers unchanged. Fix what it finds that's real, with Ashen's okay for anything outside the plan.

- [ ] **Step 6: Hand over the last commit.** Summary: `notes for the redesign and a tidy up`. Wait for "committed".
