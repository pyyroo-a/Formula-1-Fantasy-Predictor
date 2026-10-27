# Accuracy bar and real scoring (design)

Project 2 of 7 on the roadmap. Written 2026-10-27 after brainstorming with Ashen.

## Why

PitWall should be worth more than guessing. Ashen said it plainly: if it can't hit a
certain level of accuracy "i can simply just guess". Right now we can't even tell,
because:

- **We grade PitWall with our own maths.** `src/backtest.py` scores finished races with
  our version of the rules (`_actual_driver_points`, `_actual_constructor_points`), and
  our version has known holes.
- **Our rules are wrong in places.** Checked against the real game on 2026-10-27
  (sources plus Ashen confirming in the app): qualifying P11 to P20 scores 0, and -5 is
  only for not setting a time. PitWall gives -5 to anyone predicted P16 or worse. The
  constructor qualifying bonus is -1 / +1 / +3 / +5 / +10 in the game, PitWall uses only
  +1 / +3. Pit stop points (up to +20, +5 fastest, +15 world record) aren't modelled at
  all. Ashen's friend's point: the constructor is where the points are, and we
  undervalue exactly that.
- **The "baseline" isn't a baseline any more.** The backtest's "pick by FP3 order" runs
  the same optimiser on the same FP3 order as PitWall, and since `SHRINK_TO_GRID = 0.0`
  PitWall's prediction IS the FP3 order. So it's PitWall against itself.
- **Two scoring quirks** (kept on purpose in the cleanup, see
  `Fantasy Predictor/Fantasy scoring.md`): the team builders drop Avoid drivers before
  summing a constructor, and the driver pool skips the constructor bonus. So the 3 teams,
  the Manual Team page and the chip advice add constructors up differently. Ashen noticed
  the Manual Team page "feels" less trustworthy and this is a big part of why.

## The big find: the game's own points are in a free feed

`https://fantasy.formula1.com/feeds/drivers/<round>_en.json` (the feed we already read
prices from) carries, for every driver and constructor, that round's official points:
`GamedayPoints`, plus `QualifyingPoints`, `RacePoints`, `SprintPoints` and
`SessionWisePoints`. Each round's feed keeps its own round's points (checked rounds 1, 13,
17, 18). It also has `SelectedPercentage` and `CaptainSelectedPercentage` (share of
players owning / captaining each one), but only as of now, not frozen at past deadlines.

**Verified:** Ashen's US GP team (Leclerc 2x, Antonelli, Lindblad, Hulkenberg, Perez,
Ferrari, Haas) adds up to exactly **238** from the feed, the same as the app.

Checked and ruled out: OpenF1 as the source of truth. It has stationary pit stop times for
only 6 of 20 races this season (none since Spa) and its overtakes count position changes
from pit stops too, unlike the game. The feed's `ProjectedGamedayPoints` is just the real
score copied in after the race (0 before), so it's no use as a prediction.

## Goals

1. **The points referee.** Real game points for every driver and constructor for every
   finished round, read from the official feed and stored in the repo. This is the one
   source of truth every grade uses.
2. **The season scorecard.** A report grading every 2026 race in real points, five
   columns:
   - **PitWall team 1**: the real locked snapshot for R13 to R18, a walk-forward replay
     (only information from before that race) for earlier rounds
   - **Copy the FP3 order**: model-free, see below
   - **Most expensive that fit**: model-free
   - **Copy the crowd**: the most-owned team that fits, from Mexico (R19) on only
   - **Best possible in hindsight**: the ceiling
   Plus average real points per race and races won against each simple column.
3. **Correct forecast rules**, each kept only if it raises PitWall's real points on the
   scorecard:
   - qualifying: P1 to P10 +10 to +1, P11 to P20 0 (drop the P16+ -5)
   - constructor qualifying bonus from the predicted grid: -1 neither in Q2, +1 one in Q2,
     +3 both in Q2, +5 one in Q3, +10 both in Q3
   - expected constructor extras per team (pit stops mostly), learned from real data, see
     "How it gets made"
   - fix both quirks so every page adds a constructor up the same way: both drivers'
     points, Avoid or not, plus the bonus
4. **Start saving ownership.** At every lock, the snapshot stores `SelectedPercentage` and
   `CaptainSelectedPercentage` for every driver and constructor, so the crowd column has
   honest data going forward.
5. **Notes updated** to match: Fantasy scoring, Decisions and evidence (with the new
   numbers), Chips, Gotchas, Roadmap, plus correcting the claims built on the fake P15/P16
   cliff (the 25.8% "wrong side of a scoring jump" number in the README and Decisions and
   evidence).

## Non-goals

- No website changes. The scorecard is a report we read together. Showing it on the site
  is project 5, and the whole UI gets redesigned once at the end with the frontend design
  plugin.
- No budget changes. The 3 teams stay at $100M (Ashen: it's "an idea of what you can do
  with 100 mil"). Building at your own budget is the planner, project 3.
- No new practice features (best sectors, long runs): project 4.
- No AI agents. Discussed: counting points, predicting and building teams are plain maths
  that code does exactly and for free. An agent only fits the Reddit feed (project 7).
- No predicting fastest lap, Driver of the Day or overtake counts, unless a test shows it
  helps (they stay out by default).

## Anti-goals (a failure even if it "works")

- A number in the scorecard that isn't real: tuned, guessed, or quietly filled in.
- Information leaking from the future into a replay (a race graded with knowledge from
  itself or later races). The lesson from the model's shift-by-one features.
- A rule change shipping without its scorecard numbers, or shipping when it scores less.
- Breaking the weekend lock, or a backend push between FP1 Friday and the race.
- Anything paid.

## Constraints

Ashen's working rules (`Fantasy Predictor/Working rules.md`): ask before changing code,
Ashen commits and pushes, measure first and leave the number next to every switch, tests
pass before a push, related files in one commit, free only, no em or en dashes, casual
voice in comments and notes. All 79 current tests keep passing, and golden changes from
an intended rule change get re-recorded with the reason in the commit.

## How it gets made (decided)

- **Referee data:** a new module (my call: `src/official_points.py`) fetches a round's
  feed, keeps one row per driver code and constructor (prefer the active row, the same
  duplicate driver trap as prices, see `parse_price_feed`), and saves the points to a
  committed file (my call: `data/official_points_2026.json`, keyed by round). A one-off
  backfill fills rounds 1 to 18. The Monday job (`scripts/update_data.py`) adds each new
  round, and a failure there must not stop the results update, same as prices today.
- **Grading uses the referee, never our own rule maths.** The backtest's
  `_actual_driver_points` and `_actual_constructor_points` get replaced by the referee for
  grading (they stay only if something else needs them).
- **The model-free picks** (no fantasy points, no model, only what a person could see
  before the deadline):
  - *Copy the FP3 order:* drivers taken in FP3 (or sprint quali) order, constructors
    ranked by the best car's FP3 position, filled into the best legal team under $100M
    that follows that order. The exact fill rule is left to the builder, but it must not
    use `FantasyValue` or the model.
  - *Most expensive that fit:* the team with the highest total price under $100M.
  - *Copy the crowd:* the team with the highest total `SelectedPercentage` under $100M.
  - Everyone gets a 2x: PitWall uses its own boost pick, FP3 order boosts the fastest
    driver it owns, most expensive boosts its priciest driver, the crowd boosts its most
    captained driver, hindsight best boosts its top scorer.
- **Prices:** each round's real prices (`data/price_history.json`). Round 14 is missing
  there, so fetch it from the feed (`<14>_en.json` has prices too) and fill the gap.
- **Expected constructor extras:** for each finished round, a constructor's official
  points minus its two drivers' official points minus the qualifying bonus their real
  grid earned leaves the pit stop part (plus rare DSQ penalties). Average that per team
  over the rounds BEFORE the race being predicted (walk forward), and add it to the
  constructor's forecast. It's tested on its own column of the scorecard like every
  other change.
- **Measuring changes:** past snapshots can't be re-locked, so every rule change is
  measured on a walk-forward replay of EVERY 2026 round (same session the live lock would
  use: FP3, or sprint quali on sprint weekends). The real locked teams (R13 to R18) stay in
  the scorecard as the honest record of what PitWall actually picked, next to the replay.
  The replay runs once per change (the old rules, then each fix on its own, then all kept
  fixes together), and the numbers go in the code next to the switch, the same way
  `DNF_WEIGHT` and `SHRINK_TO_GRID` are documented now.
- **Snapshots:** `build_snapshot` adds ownership. The site and the existing snapshot
  readers must not break on old snapshots without it.

## Left to the builder

- The exact fill rule for "copy the FP3 order" (within the rule above).
- Where the scorecard report lives and its exact layout (a script that writes a markdown
  report is the expected shape; a `Fantasy Predictor/Scorecard.md` note is a good home).
- How the backfill is run (a script or a flag on an existing one).
- Whether old rule maths in `src/backtest.py` gets deleted or kept for comparison.

## Calls I made (Ashen, check these)

- The scorecard grades everything at $100M, the same budget the 3 teams are built at.
  Grading at your $116M belongs with the planner.
- Each race is graded as a fresh team, ignoring transfer limits, the same way the locked
  teams are built. The planner is where transfers come in.
- Sprint weekends: assumed to follow the same rules (Ashen wasn't sure). The referee
  doesn't care, the feed already includes sprint points.
- Driver of the Day, fastest lap and overtakes stay out of the forecast by default, but
  they're all inside the official points, so the scorecard grades them for free.
- The extra baseline "copy the crowd" only covers R19 onwards, so it'll have very few
  races this season. It's there to build up a record.
- The scorecard is run by hand for now. Running it automatically every Monday can come
  with the track record page (project 5).
- A wrong prediction rule (the P16+ -5) also feeds No Negative chip advice
  (`evaluate_team_chips` counts -5 per back row driver). That gets fixed with the rest.

## Order of work (suggested)

1. Referee: module, backfill rounds 1 to 18, round 14 prices, check against the 238.
2. Scorecard with the OLD forecast rules: this is the honest starting number.
3. Each forecast fix measured on its own, then the kept ones together.
4. Ownership in snapshots, Monday job adds official points.
5. Notes.

Mexico FP1 is Friday 2026-10-30. Backend changes only get pushed Monday to Thursday, so
anything that changes the live picks waits until after Mexico if it isn't measured and
ready by Thursday.
