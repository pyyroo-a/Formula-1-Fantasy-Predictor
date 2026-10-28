# The one UI redesign

Date: 2026-10-28. The last big piece after projects 1 to 6: one consistent look for the
whole site, instead of the piecemeal UI changes we kept putting off. Brainstormed with
mockups, they're in [`2026-10-28-ui-redesign-mockups/`](2026-10-28-ui-redesign-mockups/)
(open them in a browser). Where a mockup and this doc disagree, this doc wins (the
mockups were made along the way, so some show old tab names).

## Why

On a race weekend I sit on the main page looking at the 3 picked teams, then go to
Manual Team to build my own from them. That's basically the whole site for me. The rest
either confused me ("2 (free)", "high confidence" on a back marker), didn't fit my phone
(sideways tables, long names), or I never used because it seemed broken (Chip Advisor,
Practice). The redesign should make the main flow fast and clear, make the pages I
skipped worth opening, and look like one site.

## Goals

- One look everywhere: today's dark timing tower feel (A in the brainstorm) with the
  Archivo font (B). Mockup 1 is the reference.
- Every page works on a phone (375px wide) with no sideways scrolling.
- The main page shows the 2x pick and explains confidence once with a key.
- Manual Team loads by itself and is quick to pick from.
- Planner and Chip Advisor become one tab, **Garage**, built around my saved teams.
- Insights tells the story honestly, and says how it worked things out.
- Practice works again (the one backend task, see below).

## Non goals

- No change to any number, pick, 2x pick, chip verdict, confidence level or rounding
  rule. The pages show exactly what the server sends, just laid out better.
- No new backend endpoints. Reasons for Limitless and No Negative tracks (would need the
  backend to save what caused each number) are a later idea, not this.
- No per team budgets in anything that's PitWall's own teams (that's on the Roadmap with
  "measure first").
- Project 7 (Reddit) stays parked.

## Anti goals (fails even if it technically works)

- A number on screen that differs from what the same page shows today.
- Anything made up to fill a gap: no fake reasons, no placeholder numbers, no
  confidence pill where the server sent none.
- Text that has to be scrolled sideways, or names cut off, at phone width.
- Em or en dashes anywhere (the test enforces it).

## Constraints

- React 19 + Vite + Tailwind 3 in `frontend/`, Vercel. Free only. No new npm packages
  unless really needed (fonts come from a Google Fonts link in `index.html`).
- `npm run build` passes, `npm run lint` has no new errors (7 old ones exist), backend
  tests pass (`./venv/Scripts/python.exe -m pytest -q`, 205 now).
- Frontend pushes any day. The backend task has to be pushed before FP1 on Friday
  30 Oct, or wait until the Mexico race is over.
- I commit, task by task. Comments in my plain voice.
- Saved browser data keeps working: `pitwall_planner_teams`, `pitwall_budget`,
  `pitwall_last_team` keep their names and shapes.

## The look

Colours (Tailwind `pw` palette, updated in `tailwind.config.js`):

| Name | Hex | Used for |
|---|---|---|
| bg | `#0F1217` | page |
| panel | `#141821` | panels, cards |
| raised | `#181C24` | switchers, input boxes, stat boxes |
| line | `#1E232C` / `#232833` | row dividers, borders |
| text | `#E9ECF1` | main text |
| muted | `#8B93A3` | small text, labels |
| red | `#FF4D4D` | the one accent: logo, active tab, 2x, best step, buttons |
| safe / high | `#5BE38A` | high confidence, PLAY, gains, "within 1 place" |
| caution / medium | `#F2C94C` | medium confidence, CONSIDER, "lost to" |
| low / loss | `#FF7A7A` | low confidence, places lost, transfers out |
| info | `#7FA6FF` | AFTER QUALI |

Team colours stay in `constants.js` (`TEAM_COLORS`, `teamAccent`), used as the 4px
stripe on every driver and constructor row. Chart colours (Track record) were checked
for colourblind safety on the panel colour: PitWall `#F0504F`, FP3 order `#5B8DEF`,
most expensive `#B08A22`, best possible as a grey tick.

Type: **Archivo** everywhere (variable, width 62 to 125, weight 400 to 800). Condensed
(width about 62 to 78) and bold for names, numbers and headings, normal width for small
text. Numbers use tabular figures. The old monospace font goes. No all caps labels with
letter spacing (today's "YOUR BUDGET" style), sentence case instead, except the logo
and the chip verdicts (PLAY, HOLD...) which stay as short tags.

Shared pieces (build once, use everywhere):

- **Tower row**: spot (P1, or DNF), team stripe, full name with team under it, the right
  hand numbers (price over points, or time over tag). Names never wrap or get cut on a
  phone: the right column is fixed and the name truncates only as a last resort.
- **Switcher**: the segmented control (Team 1/2/3, FP1 to Race, 1/2/3 free transfers).
- **Confidence pill**: dot plus `high` / `medium` / `low`, colours above. Only when the
  server sent a confidence. One key line above the list: "How sure we are about the
  predicted spot: high, medium, low (about the spot, not whether he's a good pick)".
  On a phone the shorter "= how sure we are about the spot".
- **Chip card**: name, verdict tag, one line, the number.
- **Stat box**: small label over a big condensed number.
- **Loading**: "the free server can take up to 30 seconds to wake up" in plain words,
  grey placeholder blocks where the answer will go.

## Navigation

Four sections like now: Overview, My team, Race data, Insights. Desktop: in the header.
**Phone: a bar at the bottom** with the four sections (my call, easy to undo). Sub tabs
under the header like now.

- My team: **Manual team**, **Garage** (Team Optimizer is dropped, see below)
- Race data: one page with a session switcher instead of three tabs (Backtest stays as
  a dev only extra like now)
- Insights: Predicted finishes, Track record, Chips

## Page by page

### Overview (mockup 1)

Same data and states as now (live, provisional, locked, held). Top: the weather and
countdown like now, restyled. The hold banner in plain words ("No race weekend live
right now. Showing the last locked team until Mexico gets locked after FP3", wording
follows today's states). Then:

- Race name big and condensed, "Round 18, locked after FP3 on 24 Oct" under it.
- Team 1/2/3 switcher.
- **New: a 2x box** with the team's `boost_pick` name and its `reason` text as the
  server sends it (Roadmap banked idea "a 2x card on the main page").
- The confidence key, then the team as tower rows: predicted spot, stripe, full name,
  team plus confidence pill, price and expected points. Then the two constructors.
- Expected points, cost, left over.
- Chips for this team (today's `AutoChipAdvisor` data), in a 3 by 2 grid, verdicts as
  tags. `POST-QUALI` shows as `AFTER QUALI` (display only).
- Right column on desktop (under on a phone): predicted finish, driver prices,
  constructor prices. **The predicted finish shows only predictions until the real
  results are in; once `/weekend-finishes` says results are available (Monday) each
  line also shows "finished P2".** That's new for this page, the data is already there.
  Today's arrows (model vs practice order) can stay as a small marker.
- The CONSIDER rule (`displayCategory`) keeps working as now.

### Manual team (mockup 2, layout A)

- Race box (picks the next race by itself, can be changed) and budget box side by side
  at the top. Budget still saved as `pitwall_budget`.
- **Loads by itself**: when the tab opens, or the race changes, it checks the sessions
  and if practice exists it loads the pool straight away ("Loading the drivers, please
  wait..."). Before FP1: "No practice yet for Mexico. This fills in by itself after
  FP1" and it keeps the existing once a minute check, loading when data appears. Same
  request as now (FP3, FP1 on sprint weekends). No "Load driver pool" button.
- Drivers grouped by team, teams A to Z, teammates side by side, each card with the
  team colour, price, predicted spot and points. Then constructors A to Z, also with
  team colours. A small "By team / By points / By price" sort, By team first.
- Your team panel on the right (sticky), on a phone a bar stuck to the bottom: spent,
  left, 5/5 and 2/2, then the slots, your points and "vs PitWall's best".
- Same maths as now for score, vs optimal and the rating.
- **"Start from PitWall Team 1" button** (my call, Ashen hasn't said yes or no): copies
  the weekend's Team 1 into the picks so you just swap. Easy to leave out.

### Garage (mockups 3 and 4)

Replaces Planner and Chip Advisor.

- Three team slots, from `pitwall_planner_teams` (same format, so my saved teams carry
  over). Empty slots say "Add team". First visit: "Add your F1 Fantasy teams. Put in the
  teams you really have in the game, once..." (mockup 4 screen 1).
- **Add or edit a team**: name, budget in the game, free transfers as a 1/2/3 switcher
  ("You get 2 free transfers a week, pick 3 if you saved one last week"), then the same
  picker as Manual Team (drivers by team, constructors A to Z, colours), a bottom bar
  with 5/5, 2/2 and cost vs budget, "Save team" lit only when complete. This picker has
  to work before practice exists, so it uses `/prices` like the planner does now, and a
  driver to team map from data the site already loads (for example `/weekend-finishes`)
  rather than a hard coded grid if possible.
- After saving, or opening the tab with a saved team, it asks `/transfer-ladder` and
  `/chip-advisor` for that team and the next race by itself. Same "no practice yet,
  fills in after FP1" state as Manual Team.
- **Transfers as steps** (Keep, 1, 2, and 3 when you have 3 free): each step's height
  follows its expected points, the highest is red, "+27 vs keeping" under it. Under the
  steps, each row's swaps ("Mercedes out, Ferrari in" plus the server's reason) and the
  2x. Then the facts box. The numbers and rounding are exactly today's ladder (whole
  points, `Math.round`, vs keeping from the rounded numbers).
- **Chips for this team**, PLAY first then CONSIDER then the rest, each with the
  server's reason where there is one and its number.
- Plain labels: "Free transfers this week: 2", "1 transfer, free", "2 transfers, both
  free", "a 3rd transfer would cost 10 points". No "2 (free)".
- Fixes the Chip Advisor name bug for good: it sends the server's own constructor names
  (today it sends "RB F1 Team" and "Haas", which the server scores as 0).
- The race defaults to the next race, can be changed.

### Race data (mockup 7)

- One page: race box, then a session switcher with only the sessions that ran (FP1, FP2,
  FP3, Quali, Race; FP1 only on sprint weekends, like now).
- Practice: tower rows, best lap and gap to the top.
- Quali: tower rows with one time (the best from the last part they reached) and a tag
  (Q3, out in Q2, out in Q1). Tap a row to see all three times.
- Race: tower rows with the places gained or lost and "from P4", which now shows on
  phones too. DNFs faded at the bottom.
- The state keeps living in `App` / `useRaceData` so a picked race survives switching
  away and back (see Frontend.md).

### Insights (mockups 5 and 6)

- **Track record**: a headline ("How PitWall's locked teams really did"), one honest
  line under it (copying the FP3 order scored more so far, these locks were before the
  28 Oct fixes, words follow the data), four stat boxes (PitWall, FP3 order, most
  expensive, best possible, with "beat it 3 of 6"), then one line per race with a dot per
  team and the best possible as a tick, hover or tap a dot for its number, and "183 lost
  to FP3's 242" style results. Crowd gets its box and dots once it has races, the note
  explains why it's missing until then. Phone: stat boxes 2 by 2, each race full width.
  A plain table view stays available (the chart's numbers as text).
- **Predicted finishes**: rows instead of a table. Predicted spot, practice order under
  the name, "finished P2" on the right once the results are in, green within 1 place.
  The accuracy summary (model vs practice order) stays, restyled.
- **Chips**: three cards (3x, Limitless, No Negative) with the top 3 tracks and the
  worst, small bars, and for 3x the "who" line (Antonelli, P19 to P1). Then every track
  as a list (no sideways table), then the line each on the other three chips like now.
  At the bottom a folding **"How we picked these tracks"** box: what the chip would
  really have been worth at each track from the game's official points, ranked highest
  to lowest, top 3 plus the lowest shown, the middle value across seasons once there's
  more than one, and the honest catch that with one season we can't check yet if a good
  track stays good. No per chip "what it does" explanations (I don't want those here).

### Dropped: Team Optimizer

It builds teams for past races from the real grid at today's prices, so it isn't this
weekend's answer and isn't what you could have scored back then. The Track record
already answers "how would PitWall have done". Remove the tab, `TeamOptimizerTab.jsx`
and `useBudgetTeams` if nothing else uses them. `/predict-budget` stays on the backend,
unused, like the older endpoints (note it in API.md).

## The one backend task: Practice

`POST /practice-results` (`src/api/races.py`) answers 500 for every race on the live
server (checked 2026-10-28 with the US GP). It still loads laps through FastF1 live
timing, which went behind the F1TV login in October. Practice for the model already
comes from OpenF1 (`src/openf1.py`, `src/fetch_practice.py`). Switch this endpoint to
the same source, keeping the response shape the page uses (`session`,
`available_sessions`, `results` with Position, Abbreviation, FullName, TeamName,
LapTime, GapToPole). Test first, recorded data, OpenF1 switched off in tests like the
rest (`tests/conftest.py`). Push before FP1 Friday or after the race.

## Small fixes that come along

- Whole numbers that show without a decimal: points and prices always one decimal
  (`38.0`, `$3.0M`), except where a page rounds to whole points on purpose (the ladder).
- Long names never wrap badly on a phone.
- Montreal shows as "MontrÃ©al" on the Chips page because the server sends it garbled.
  That's in `data/chip_history.json` / the script that writes it, so it's a backend data
  fix, not part of this. Flag it, don't hide it in the frontend.

## Answers to the builder check

A fresh reviewer read this as a builder. What they asked, answered from the code and the
live server (2026-10-28):

- **How closely to follow the mockups:** match their look (colours, type, row shapes,
  the step chart, the race lines), not pixel for pixel. Known places where they're
  stale: mockup 2 still shows a Team optimizer tab and a Chip advisor tab, mockup 3
  calls the Garage "My real teams", mockup 4 says "Weekly plan". Points showing as
  "xx.x" and the confidence levels in mockups 1 and 2 are placeholders, the real page
  shows server values. Everything else in them is current.
- **Garage driver to team map:** `/prices` has no teams. Use the `team` on each line of
  `/weekend-finishes` (all 22 drivers of the newest weekend). A driver missing from it
  (a new rookie) goes in an "Other" group at the bottom with the muted colour, never
  dropped. No hard coded grid. (My call.)
- **Garage before practice:** both `/transfer-ladder` and `/chip-advisor` answer 400 with
  a `detail` ("No practice data yet for this race, the ladder needs at least FP1." /
  "No practice data available yet..."). Show the "No practice yet, this fills in by
  itself after FP1" state for that, check again once a minute like Manual Team, and the
  server's `detail` for any other error. No saved team: just the empty slots, no calls.
- **"Finished P2" on Overview:** `/weekend-finishes` has `results_available` and its
  `predictions` carry `actual_pos` / `actual_status` for the same race the lines
  predict (its own `race_name` and `round`). Show "finished" only when
  `results_available` is true, read from that same line. Same rule `PredictedFinishes`
  uses today.
- **Quali tag:** the server sends Q1, Q2, Q3 with nulls for parts not reached. Work the
  tag out on the page: Q3 time means "Q3", else Q2 means "out in Q2", else "out in Q1".
- **Track record chart:** hand made (divs or SVG), no chart library. "Beat it 3 of 6"
  comes from `summary` (`beaten`, `of`), the per race "lost to" from comparing that
  row's `cells`. Crowd gets its box and dots when `summary.Crowd.races > 0`, the same
  test `TrackRecord.jsx` uses today, and today's note text about ownership stays
  (restyled). The honest line picks its words from the averages (FP3 order higher or
  PitWall higher), the 28 Oct fixes sentence is today's existing copy.
- **"How we picked these tracks":** it's a description of the method, no new numbers.
  The numbers on the cards are already in `/chip-history` (`best`, `tracks`).
- **Font:** load Archivo with both axes (`wdth,wght@62..125,400..800`) in `index.html`,
  set it as the Tailwind `sans` font and the body font.

## Left to the builder

- How to split the components (one shared `ui/` folder for the pieces above is the
  likely shape).
- Exact spacing, breakpoints and the sticky bars, as long as 375px works.
- Whether the Garage asks for the ladder and chips in parallel or one after the other.
- Keyboard focus visible on everything clickable, reduced motion respected.

## Checking it

Every page in the browser pane at desktop width and at 375px, with real data from the
live backend (`VITE_API_URL` pointed at Render) and the held US GP team, including:
switching teams, Manual Team before practice (Mexico), Garage empty, adding a team, 3
free transfers, Race data race to quali and back, every Insights tab. Screenshots for
Ashen. Numbers compared against the live site for the same page before and after.

## My calls (check these)

1. The bottom tab bar on phones.
2. The "Start from PitWall Team 1" button on Manual Team.
3. `POST-QUALI` shows as `AFTER QUALI`.
4. The predicted finish arrows stay as a small marker next to "finished P2".
5. Fonts from Google Fonts (free) instead of a new npm package.
6. Garage teams come from `/weekend-finishes`, with an "Other" group for anyone missing.
