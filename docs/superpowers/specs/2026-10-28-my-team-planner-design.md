# The "my team" transfer planner (design)

Project 3 of 7 on the roadmap. Written 2026-10-28 after brainstorming with Ashen.

## Why

PitWall's main page builds 3 fresh teams at $100M every weekend. That's not the call
Ashen actually has to make. In the real game he already has a team (three of them, the
game allows 3 entries), a budget that's grown past $100M, and a limited number of free
transfers. Every transfer beyond the free ones costs -10.

At the US GP his main team had 2 free transfers. The big swaps (dropping an A tier
driver and constructor) were obvious and instant. The hard part was the cheap picks
and the second constructor: **"does this swap actually gain points, and is it still
worth it if it costs me -10?"** He'd used his 2 transfers and couldn't tell whether a
third was worth the hit.

There's also the rollover: an unused free transfer carries over, so saving one this
week gives 3 free next week (Ashen and I both think 3 is the cap, see Constraints).

## What it is

A page where Ashen saves his teams and, on a race weekend, sees a **transfer ladder**
for any one of them:

| Transfers | Change | Expected | vs keeping |
|---|---|---|---|
| 0 | keep the team | 182 | |
| 1 | Haas to Mercedes | 203 | +21 |
| 2 (free) | + Perez to Bortoleto | 211 | +29 |
| 3 (costs -10) | + Lindblad to Gasly | 204 | +22 |

(Made up numbers, from the mockup Ashen picked. The layout was option A; option B,
swap by swap with tick boxes, was turned down.)

Each row is the best team you can reach with exactly that many transfers, its expected
points for this weekend from PitWall's forecast, and the difference from keeping the
team, with -10 already taken off for every transfer past the free ones. Each row also
shows the 2x pick for that team.

Rows are worked out **independently**: row 2 is the best team with any 2 transfers, not
row 1 plus another swap, because with budgets the best pair often doesn't contain the
best single swap. So the Change column lists every swap in that row against your
current team (the mockup's "+ Perez to Bortoleto" was a shorthand), and the facts
compare a row with the one above it ("2 transfers adds +8 over 1").

### Facts, not orders

Ashen: "lets just state facts". The page never says "do this". Under the ladder it
states facts, for example:

- "The highest expected total is with 2 transfers (211)."
- "Your 2nd swap adds +3."
- "Skip it and you'd have 3 free transfers next week."
- "A 3rd transfer adds +6 but costs -10."

### Every swap shows why

What made Ashen trust the Leclerc and Ferrari picks at Austin was seeing why: they were
on top in practice, which matched what he watched in FP3. So every swap in the ladder
shows its practice facts in plain words, e.g. "Haas to Mercedes: Mercedes cars P2 and
P4 in FP3, Haas P14 and P17", and "Perez P19 to Bortoleto P9". Kept to positions in the
session the forecast used. Deeper confidence and reasons are project 4.

### Uncertainty

Numbers are expected points, a positive lean with honest uncertainty, never anything
that reads like a guarantee.

## Goals

1. Save up to **3 teams** in the browser (Ashen: "remembering 3 is better"), each with
   its 5 drivers, 2 constructors, budget and free transfers this week. Switch between
   them on the page. Next weekend you only change what changed.
2. The transfer ladder for the chosen team, at **its own budget**, using the same
   forecast and the same per driver and per constructor scoring as the rest of the site.
3. Facts under the ladder, including the rollover fact when a free transfer goes unused.
4. A practice reason on every swap.
5. **Graded on real points before it ships** (the project 2 rule): over a replayed
   season, does following the ladder score more than keeping your team? See "Proving it".
6. Notes updated (vault: a new Planner note, Roadmap, README, API, Frontend).

## Non-goals

- No link to the F1 Fantasy account. It never makes a transfer, it's advice only.
- No chips (project 6), no wildcard or limitless rows.
- No planning several weeks ahead. It covers this weekend, plus the plain fact that a
  saved transfer means one more next week. It doesn't put a points value on saving
  one (that would mean guessing next week, the overcomplicating Ashen said to avoid).
- No change to the main page's 3 teams, which stay at $100M.
- No polished visual design. The page has to be clear and usable now. Making it look
  great is part of the one redesign at the end of the roadmap (frontend design plugin).
  Ashen did flag that labels like "2 (free)" confused him at first glance, so wording
  has to be plain even now.
- No accounts or server side storage. Teams live in the browser.

## Anti-goals (a failure even if it works)

- It reads like orders instead of facts.
- A number looks more certain than it is.
- It ever suggests a team that's illegal (not 5 drivers and 2 constructors, a driver
  twice, a driver who isn't in this weekend's field) or over the team's budget.
- Its per driver and per constructor numbers disagree with what the Manual Team page
  shows for the same picks. (Totals can differ on purpose: the ladder's total includes
  the 2x and says so, see "Scoring is shared".)
- It ships without showing, in real points, that following it beats keeping your team.

## Constraints

Ashen's working rules (`Fantasy Predictor/Working rules.md`): ask before changing code
outside the plan, Ashen commits and pushes, measure first, tests pass before a push,
related files in one commit, free only, no em or en dashes, casual voice in comments and
notes. No backend pushes from FP1 Friday until the race is over. Keep it simple: Ashen
said F1 can't be 90% predictable, so no clever extras to squeeze out accuracy.

**The rollover cap is unconfirmed.** We both think a free transfer carries over once
and you can never hold more than 3. Check the official 2026 F1 Fantasy rules before
building the free transfers input, and write what you found in the notes.

## How it gets made (decided)

- **Built into the existing site.** A FastAPI endpoint for the ladder (a new file under
  `src/api/`, the maths in its own `src/` module so it can be tested and replayed
  without the API), plus one new React page under My Team in `frontend/`. Teams saved in
  localStorage, like the Manual Team page already remembers the budget
  (`pitwall_budget`).
- **The forecast is recomputed live, not read from the snapshot.** A locked snapshot
  only saves the 3 teams and the predicted finishing order, not every driver's points.
  The Manual Team page (`/upcoming-race-pool`) and the Chip Advisor already recompute
  the forecast from the practice grid, so the planner does the same: the session the
  weekend locked on once it's locked (the snapshot's `session_used`), the latest
  session before that, marked provisional like the main page.
- **Scoring is shared.** Each driver's expected points are the pool's `FantasyValue`
  and each constructor's are the pool's constructor score (`get_race_pool`), the same
  numbers the Manual Team page shows, so the anti-goal above holds by construction.
  A team's expected total is its 5 drivers plus its 2 constructors plus the 2x driver
  counted again, because the 2x is real points in the game. The 2x pick is
  `pick_boost_driver`, the main page's rule. The page labels the total as including the
  2x, since the Manual Team page's MY SCORE leaves the 2x out (and marks its 2x as the
  highest scorer). Changing the Manual Team page is out of scope. Prices are the
  upcoming round's (`state.current_prices`), the same prices everything else uses.
- **Candidates for a swap in** are every priced driver in this weekend's field and every
  constructor, not only the main page's non Avoid ones. The 3 teams' "at least 1 Safe
  driver" rule doesn't apply, it's the user's team.
- **Rows:** 0 transfers up to the free transfers plus 1 paid one (as in the mockup).
- **Budget per team** is what the user types in, their total budget in the game (team
  value plus money in the bank). Every row's team has to cost no more than that at this
  weekend's prices.

## Proving it (the grade before shipping)

Replay R3 to R18 of 2026 walk forward, the same way the scorecard does
(`src/backtest.py`, only information from before each race), and grade every team with
the official points (`data/official_points_2026.json`), charging -10 for every paid
transfer. Three ways to play the season from the same start, each with 2 free transfers
a race plus the rollover (an unused one carries over, cap as per the confirmed rule):

- **Keep:** the starting team, never changed.
- **Free only:** each race, take the best row that uses no paid transfer.
- **With hits:** each race, take the row with the highest expected total, paid rows
  included.

**Two bars (Ashen's call):**
1. **Free only has to beat Keep** in average real points per race, or the planner
   doesn't ship.
2. **With hits has to beat Free only**, hits charged, or the paid row doesn't get
   suggested. In that case the page still shows the free transfer rows, and states the
   -10 as a plain fact ("a 3rd transfer costs -10") without a paid row ranked against
   them.

Why the second bar: PitWall's expected points aren't on the game's exact scale (no pit
stop points, retirements charged at 0 in forecasts, the old -5 quali rule, circuit
scaling), so "+6 expected vs -10" compares two slightly different scales. Only the real
points can say whether paying for a transfer on the ladder's say so works.

Start: PitWall's replayed team 1 at R3 at $100M. Budget after that follows the game:
the team's value at each race's prices plus whatever was left in the bank, so a team
that gets more expensive can still be kept. Report the average real points per race and
races won for each, plus the total transfer hits paid. Whatever the result, it gets
written down like any other.

The report can be a section added to the scorecard or a separate script, the builder's
call, as long as it's run by hand and its numbers go in the notes.

## Left to the builder

- The search for the best team at each transfer count (brute force over which picks go
  out and who comes in is fine at this size).
- The exact request and response shape of the endpoint.
- Exact wording of the facts and the reasons (plain, no "do this").
- How the page lets you type a team in (pickers from the current price list are the
  obvious way) and the localStorage format.
- What happens when a saved team has a driver who's left the grid (show it clearly, never
  crash).
- Where the grade lives (scorecard section or its own script).

## Calls I made (Ashen, check these)

- The page lives under My Team, next to Team Optimizer, Manual Team and Chip Advisor.
- Recompute the forecast live instead of saving every driver's points in the snapshot.
- Swap candidates include Avoid drivers. If it's the best expected swap for your
  budget, you see it, with its reason.
- Rows stop at one paid transfer.
- Rows are independent bests, not nested, and the total includes the 2x (labelled).
- Not rushing it for Mexico (FP1 is Friday 2026-10-30, so backend pushes would have to
  land tomorrow). Built calmly, backend pushes Monday to Thursday, frontend only pushes
  are fine any day (Gotchas).
- Before the lock, the ladder shows provisionally from the latest practice, like the
  main page does.
- The grade starts from PitWall's replayed R3 team at $100M and plays "take the highest
  expected row" every race. Nobody plays exactly like that, but it's the honest way to
  test the numbers the ladder shows.

## Order of work (suggested)

1. Confirm the rollover rule.
2. The ladder maths as a plain module, test first: legal teams only, budget, hits,
   rollover, the 2x pick.
3. Prove it on the replay (both bars). Stop and show Ashen the numbers. If free only
   loses to keeping, stop.
4. The endpoint.
5. The page, with 3 saved teams.
6. Notes.

Mexico FP1 is Friday 2026-10-30. Backend changes only get pushed Monday to Thursday.
