# PitWall cleanup and Fantasy Predictor notes (design)

Written 2026-10-25, after the US GP weekend brainstorm. This is project 1 of 7, the
other six are listed at the bottom so nothing from the brainstorm gets lost.

## Why

PitWall works and the picks are decent, but the next six projects (planner, better
practice data, chips and so on) all get built on top of this code. Right now:

- 11 of 74 tests fail because their saved answers were recorded before the last few
  races. So the tests can't currently prove a change broke nothing.
- Team scoring is copied three times in `src/fantasy.py` and the copies disagree (see
  "Known scoring quirks" below). Any scoring fix has to be made three times.
- Leftovers from the early days are lying about (unused images, old CSVs, template
  files, two overlapping plan docs), and comments and UI text have em dashes in them,
  one of which shows on the site as garbled "â€”" text in the 2x pick reason.
- Project knowledge lives in four places (README, `docs/`, `ROADMAP.md`, Claude's
  memory files) that drift apart. Every new chat has to rebuild the context.

## Goals

1. The test suite passes fully and actually protects us.
2. One copy of team scoring instead of three, with exactly the same numbers coming out.
3. Leftovers removed or archived, em dashes gone.
4. Big files split up where it helps reading.
5. An Obsidian vault called `Fantasy Predictor/` in the repo that Ashen reads to
   remember how things work, and that a new Claude chat reads to catch up.

## Non-goals

- No prediction changes. Same teams, same predicted finishes, same chip advice, same
  website. Anything that changes a number belongs in project 2 and gets measured there.
- No new features.
- No dependency upgrades.

## Anti-goals (would make this a failure even if it "works")

- A prediction or a team changes and nobody notices. The tests must prove they didn't.
- Render or Vercel breaks after a push (has happened twice from split commits).
- History lost: the old notebooks and results are the model's history, so archive, don't
  delete.
- Notes that describe the code wrongly, or a second copy of the same facts that drifts.

## Constraints (Ashen's rules)

- Never commit or push. At each milestone hand over the files to tick in GitHub Desktop,
  a Summary and a Description, then wait for "committed".
- Ask before writing or changing code, explain what and why. This document being
  approved covers the work it describes. Anything outside it gets asked first.
- `python -m pytest` (via `./venv/Scripts/python.exe`) passes before any push.
- Files that belong together go in the same commit.
- No em dashes or en dashes anywhere. Casual, plain voice in comments, notes and commits.
- Free hosting and data only.

## Part 0: fix the safety net (its own commit, first)

Re-record the 11 stale golden files with `UPDATE_GOLDEN=1`, but only after checking the
differences are data, not logic: new races in schedules and pools, new prices, new
results. Expected cause: race data added since the goldens were last recorded at
ede3bef. If any difference looks like a logic change, stop and tell Ashen before
re-recording. Ashen sees the golden diff before committing it.

After this commit: 74 of 74 pass. That's the baseline for every later step.

## Part 1: code cleanup

### One team scoring path

`build_budget_team`, `build_budget_teams` and `get_race_pool` each repeat the same
setup: filter to the race, `calculate_fantasy_score`, `GridGap`, map prices, drop
unpriced drivers, Safe/Value/Avoid/Risk categories, constructor scores. Pull that into
shared helpers so there's one copy.

**Known scoring quirks to keep exactly as they are** (project 2 fixes them, with
measurement):

- The team builders drop Avoid drivers BEFORE summing constructor scores. US GP example:
  Cadillac scored on Bottas alone (-3.7, both drivers give -8.8), Aston Martin 0 with
  both drivers negative.
- The team builders add the Q2/Q3 and "top team" bonus, `get_race_pool` doesn't. So the
  chip check (which uses the pool) saw Ferrari as 67.7 while the team builder had 71.2.

So the shared helper needs a way for each caller to keep its own behaviour. How that
looks is left to the builder. Leave a comment at each quirk pointing to project 2.

### Dead code

- `evaluate_fantasy_picks` in `src/fantasy.py` isn't used by anything: delete.
- Correction from the brainstorm: `calculate_gainer_score`, `get_safe_picks`,
  `get_midfield_drivers` and `get_position_gain_picks` are NOT dead. They're used by
  `build_fantasy_team`, which serves `/predict`. The website doesn't call `/predict`,
  `/predict-upcoming` or `/race-pool`, but they're public endpoints with golden tests,
  so they stay (my call, see below).
- Anything else the builder finds unused gets listed for Ashen, not deleted silently.

### Leftovers

| What | Action | Why |
|---|---|---|
| `driver-cards/` (22 images) | delete | Copy of `frontend/public/drivers`, used by nothing, already in `.dockerignore` |
| `frontend/src/assets/react.svg`, `vite.svg`, `hero.png`, `frontend/public/icons.svg` | delete | Vite template files, nothing references them (builder re-checks before deleting) |
| `frontend/README.md` | replace with a short one pointing to the vault | It's the default Vite README |
| `notebooks/`, `results/` | move to `archive/notebooks/` and `archive/results/` | Model history. Archived notebooks don't have to run any more |
| `scripts/measure_grid_error.py` | keep, change its output path to `archive/results/` | It writes `results/grid_error_<year>.csv` |
| `ROADMAP.md`, `docs/FUTURE_PLANS.md`, `docs/MODEL.md`, `docs/SNAPSHOTS.md` | merge into the vault | One place for everything |

`.dockerignore` needs `archive/` and `Fantasy Predictor/` added (it already skips `*.md`
except README, but the vault may get images or `.obsidian/` files later).

### Em dashes

Remove every em dash and en dash from code comments, docstrings, UI strings, docs,
workflows and the Dockerfile (28 files have them). The user-visible ones matter most:
the 2x reasons in `pick_boost_driver` (`src/fantasy.py` around line 347). Text changes
inside golden-tested output (like the boost reason) are expected golden changes; those
get their own clearly labelled golden re-record, text only.

### Splitting big files

- `src/api/race_weekend.py` (609 lines)
- `frontend/src/App.jsx` (496 lines)
- `frontend/src/components/ManualTeamBuilder.jsx` (390 lines)
- `src/fantasy.py` (792 lines, smaller once the scoring copies are merged)

Split only where there's a natural seam (for example weekend team vs predicted finishes
vs snapshot endpoints). The builder picks the seams. Routes, URLs and response shapes
must not change.

## Part 2: the Fantasy Predictor vault

A folder `Fantasy Predictor/` at the repo root, set up as an Obsidian vault with the
obsidian-notes plugin. Links must work in Obsidian, on GitHub and in VS Code (relative
markdown links, as the plugin recommends).

Readers: Ashen, months later, and a new Claude chat ("read Fantasy Predictor/Start here").

Notes:

- **Start here**: one-page map of the project, linking everything else. Written so a new
  chat is caught up from this page plus the links it follows.
- **Race weekend flow**: OpenF1 practice data, prediction, team, lock (FP3 or SQ),
  snapshot committed to GitHub, Monday results job.
- **One note per part**: model, fantasy scoring, chips, prices, snapshots, API, frontend.
  What it does, which files, why it works this way.
- **Decisions and evidence**: OpenF1 vs FastF1 (identical on 4 weekends), FP3 lock,
  DNF weight off, accuracy numbers (R15 FP3 MAE 3.67, R16 3.05, R17 SQ 2.39, Hungary 59/58/58).
- **Gotchas**: price feed duplicate TLAs, F1 livetiming login wall, snapshot rules,
  Render free tier (no disk, sleeps), data workflow runs Python 3.11 while Docker uses 3.13.
- **How-tos**: lock a weekend by hand, re-record goldens, recover a missed weekend.
- **Roadmap**: the 7 projects below, updated as they get done.
- **Working rules**: the constraints above.

Existing docs content moves in, rewritten where it's out of date (it must describe the
code as it is now, so check against the code, not just copy). `README.md` stays as the
GitHub front page and links to the vault. Claude's memory files then get trimmed to short
pointers into the vault.

## How we prove nothing broke

1. After Part 0, all 74 tests pass. They must still pass after every later step, not just
   at the end. A step that breaks one gets fixed or undone before moving on.
2. Only labelled, text-only golden changes are allowed after Part 0 (em dash removal).
3. `npm run build` in `frontend/` succeeds.
4. Run the backend and frontend locally and compare the main page, the 3 teams, predicted
   finishes and the chip panel against the live site.
5. Before deleting or moving anything, check the Dockerfile, `.dockerignore`, workflows
   and Render don't use it.
6. Commits are grouped so each one deploys cleanly on its own.

## Commits (suggested order, each handed to Ashen)

1. Re-recorded goldens (data only)
2. One scoring path plus dead code
3. Leftovers removed or archived, `.dockerignore`
4. Em dashes (plus the text-only golden re-record)
5. File splits (backend and frontend can be separate commits since Render and Vercel
   deploy separately, but each must be complete on its own)
6. The vault, merged docs, README link

## Left to the builder

- Exact shape of the shared scoring helpers.
- Where to split the big files.
- Note titles and folder layout inside the vault.

## Calls I made (Ashen, check these)

- Keep `/predict`, `/predict-upcoming` and `/race-pool` and the helpers behind them,
  even though the website doesn't use them. Removing endpoints can wait.
- Archive notebooks and old results instead of deleting them.
- Design and plan docs stay in `docs/superpowers/` (that's where this workflow keeps
  them), and the vault's roadmap links to them.
- Em dash fixes in golden-tested text are allowed, as their own labelled step.
- No backend pushes from Friday FP1 until the race is over. A cleanup bug that lands on a
  race weekend could break the lock, so backend commits go out Monday to Thursday.
- The vault commits only Obsidian's shared settings, `.obsidian/workspace*.json` (which
  windows are open on Ashen's laptop) goes in `.gitignore`.

## Not part of this build: the rest of the roadmap

Captured from the brainstorm so it's not lost. Each gets its own brainstorm and design.

2. **Accuracy bar and real constructor scoring.** Score each locked team with the game's
   real points once results are in, and compare with simple no-model picks (copy the FP3
   order, most expensive drivers that fit). PitWall must beat them over a season. Every
   model change is tested on past weekends first. Constructor scoring follows the game's
   rules: bigger Q2/Q3 bonuses (about +10 both in Q3, +5 one, a penalty for neither out of
   Q1, check the real 2026 rules) and pit stop points (sub 2.0s around +20, fastest stop
   bonus), learned from OpenF1 pit data. Fixes the two scoring quirks above.
3. **"My team" planner.** Ashen's team saved in the browser, plus free transfers and real
   bank balance. After the lock it shows the best move for 0, 1, 2 and 3+ transfers, with
   -10 per extra transfer already taken off, plus the 2x pick. Advice only, never touches
   the F1 Fantasy account. Works every weekend type (FP3 or SQ lock) and next season
   (empty $100m team means "build from scratch"). Chips plug in later as "unlimited
   transfers" (Limitless also ignores budget).
4. **Better practice data, plus confidence and reasons.** The trigger: Max topped sector 2
   in FP3 but the model only sees each driver's single fastest lap. Add best sectors
   (ideal lap), long runs vs quali runs (OpenF1 stints and tyres), all three sessions.
   Aimed at race finish and fantasy points, not quali order. Then each pick gets a
   confidence level and a real reason.
5. **Track record page.** Real points per weekend for the locked team vs the simple
   picks, so trust comes from results.
6. **Chips.** A season chip plan by circuit, based on real history (No Negative at high
   attrition street circuits, 3x on sprint weekends, Limitless when expensive drivers
   dominate, Wildcard for big rebuilds), tested on past seasons. The weekly chip check
   compares against it ("play now" or "save it, X is better"). Manual what-ifs ("what if I
   play Limitless here"). Evidence plus a recommendation, never "always play it here".
   Ashen has no chips left in 2026, so this is aimed at 2027.
7. **Reddit discussion feed (parked).** What other players are picking and their game
   plans. Reddit's free API is limited and AI summaries would be a paid call, so explore
   later. Possibly ownership % from the F1 Fantasy feed first, if it's in there.

Also outstanding, outside these projects: Monday's data job (`scripts/update_data.py`)
still loads race results through FastF1, which may now hit the F1 login wall.
