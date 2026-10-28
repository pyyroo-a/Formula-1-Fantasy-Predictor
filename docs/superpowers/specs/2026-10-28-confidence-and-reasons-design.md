# Confidence and reasons on every pick (design)

Project 4 of 7 on the roadmap. Written 2026-10-28 after brainstorming with Ashen.

## Why

Project 4 started as "better practice data": at the US GP Ashen watched Max top
sector 2 in FP3 while PitWall only saw him P4 on lap time. Before designing anything
we measured the ideas on this season's data (read only, nothing in the repo), using
places off between a driver's practice rank and their real rank:

| Idea | Result | Verdict |
|---|---|---|
| Ideal lap (best S1 + S2 + S3) instead of fastest lap | fantasy points 4.23 places off vs 4.14 now over all 18 rounds (worse on 11), 4.04 vs 3.90 on the 12 FP3 weekends (worse on 9) | dropped |
| FP2 long run pace instead of the FP3 order, 11 FP3 weekends | fantasy points 3.51 vs 3.03, worse on 9 of 11. Half and half 3.22, worse on 7 | dropped |

(Austin side note: in OpenF1's FP3 data Hamilton had the fastest sector 2, 37.550,
Max 37.871, and Max's ideal lap ranks P4, same as his lap time.) FP2 + FP3 combined
already lost in project 2. So the plain FP3 order is a stronger baseline than it
looks, and Ashen agreed to drop the inputs side ("its better than trying to do this").

What's left is the second half of project 4: how much to trust each pick. The FP3
order is right on average, but some FP3 spots are solid and some are flukes, and right
now every pick looks equally sure. Ashen's bar for this: "it should make sense for the
users that use it, not just say high with no reasoning".

## The evidence it works

Same read only check, 12 normal (FP3) weekends of 2026, 261 driver weekends. Three
things known before quali separate solid FP3 spots from shaky ones, on fantasy points,
in every position band (front, middle and back):

1. **Teammate doesn't back it up:** more than 2 places from the teammate in FP3.
2. **Moved around:** the driver's rank jumped about across FP1, FP2 and FP3 (standard
   deviation of their per session rank above 1.5).
3. **Tight pack:** under 0.05s from the nearest car on lap time.

FP3 lap count was checked too and told us nothing, so it's out.

Each failed check is a flag. 0 flags = high, 1 = medium, 2 or more = low:

| Confidence | Driver weekends | Places off, fantasy points | Within 2 places | Places off, race finish |
|---|---:|---:|---:|---:|
| High | 52 | 3.06 | 50% | 1.11 |
| Medium | 85 | 3.46 | 49% | 1.84 |
| Low | 124 | 4.56 | 30% | 2.09 |

High beat low on fantasy points in 10 of 12 weekends.

Honest caveats: the cutoffs (2 places, 1.5, 0.05s) were picked near the middle of the
data after looking at it, so this is partly fitted to these 12 weekends. Mexico
onwards is the real test. Even "high" lands within 2 places only half the time, so it
means "more trustworthy", never "safe". Sprint weekends weren't checked.

The throwaway scripts and their raw rows are in the brainstorm session's scratchpad
(`ideal_lap_check.py`, `long_run_check.py`, `confidence_check.py`). The rebuild in the
repo is part of this project (see "Proving it").

## What it is

Every driver pick gets a confidence level, HIGH, MEDIUM or LOW CONFIDENCE, with a
plain sentence saying why, always visible. Ashen picked this from 3 mockups (option A;
dots with a "why?" tap and a bare checklist were turned down):

> **Charles Leclerc** · Ferrari `HIGH CONFIDENCE`
> P1 in FP3. Teammate Hamilton P2 backs it up. Steady all weekend, 0.08s clear of the next car.
>
> **Max Verstappen** · Red Bull `LOW CONFIDENCE`
> P4 in FP3, but teammate Hadjar was P10, he moved around between sessions, and he was only 0.05s from the next car.

(Real Austin FP3 numbers.) The sentence names every check, passed or failed, with the
real numbers behind it. A short line on the page says what confidence means: how much
to trust a driver's practice spot, never a guarantee.

### SAFE becomes CONSIDER when confidence is low

The existing SAFE tag means "one of the top 3 predicted finishers". Next to LOW
CONFIDENCE it reads like a contradiction. Ashen's rule: a top 3 driver with low
confidence shows **CONSIDER** instead of SAFE. Medium stays SAFE. Only the tag on the
card changes: behind the scenes the driver is still Safe, so the team rules (like each
team needing a Safe driver) and the picks are exactly the same.

## Goals

1. Work out each driver's confidence level and reason from the practice sessions of
   the weekend, using the three checks and cutoffs above.
2. Show it, option A style, wherever a driver pick shows: the 3 teams on the main
   page, the 2x pick, and the planner's swaps (the driver coming in).
3. The SAFE to CONSIDER rule on the tag.
4. Saved in the snapshot at the lock, so a locked weekend's confidence never changes,
   like its teams.
5. **Proven in the repo before it shows on the site** (see "Proving it"), and re-run
   from Mexico onwards.
6. Notes updated: Model, Decisions and evidence (the three tried ideas and the
   confidence numbers), Roadmap, README, API and Frontend as needed.

## Non-goals

- **It doesn't change any picks.** Not the teams, not the 2x, not the planner's rows.
  Letting it steer something (like keeping the 2x off a low confidence driver) would be
  its own switch, starting off, and only on if it wins on the scorecard in official
  points. Not in this project.
- No confidence on constructors for now.
- No new data sources or better inputs (measured and dropped above).
- No percentages or odds. Three levels and a sentence.
- No polished look. Clear and usable now, the look is for the one redesign at the end.

## Anti-goals (a failure even if it works)

- A label with no reason, or a reason a new user can't follow.
- Anything that reads like a guarantee, or like "do this".
- The levels on the site disagree with the levels the proving script measured.
- A locked weekend's confidence changes after the lock.
- Picks change because of this project.

## Constraints

Ashen's working rules (`Fantasy Predictor/Working rules.md`): ask before changing code
outside the plan, Ashen commits and pushes, measure first, tests pass before a push
(`./venv/Scripts/python.exe -m pytest -q`), related files in one commit, free only, no
em or en dashes (a test enforces it), casual voice in comments and notes, no backend
pushes from FP1 Friday until the race is over. Keep it simple: F1 can't be 90%
predictable.

## How it gets made (decided)

- **Inputs are the practice grids PitWall already loads** (`get_practice_grid` /
  `get_sprint_quali_grid` in `src/fetch_practice.py`, OpenF1 first): rank, team and
  gap to pole per driver. The teammate check uses the ranks, the tight pack check uses
  the lap time gaps to the car directly ahead and behind, and the moved around check
  needs the earlier sessions of the weekend too (FP1 and FP2 on a normal weekend).
- **The maths lives in its own `src/` module**, plain functions, tested first, so the
  API, the snapshot lock and the proving script all use the same code.
- **Driver records carry it.** The driver dicts that already carry `PickCategory` and
  `DNFProb` (the pool, the 3 teams, the 2x pick, the snapshot) get the level and the
  reason too, so every page reads the same numbers.
- **The cutoffs are named constants** next to the code, with the evidence numbers in a
  comment, like the other switches.

### Exact definitions (how the brainstorm check worked them out)

These are what the 3.06 / 3.46 / 4.56 numbers came from, so the module matches them:

- **Rank in a session** = rank by the driver's fastest lap among drivers who set a
  timed lap in that session, ties broken by order (`rank(method="first")`). The same
  fastest lap rank PitWall already uses.
- **Teammate check** = the two teammates' ranks in the lock session, flagged if they
  are more than 2 apart. Both teammates get the same gap.
- **Moved around** = the sample standard deviation (pandas default, `ddof=1`) of the
  driver's rank across every session of the weekend so far that they set a time in
  (FP1, FP2, FP3 on a normal weekend), flagged above 1.5. Sprint weekends use FP1 and
  sprint quali with the same 1.5, which with two sessions means 3 or more places apart
  (my call, the sprint measurement decides if it holds).
- **Tight pack** = the smaller of the lap time gaps to the car directly ahead and
  directly behind, flagged under 0.05s. P1 and last place only have one neighbour, so
  that one gap is used.
- **A check that can't be worked out counts as passed**, and the reason sentence says
  it couldn't be checked (no teammate time in the session, or only one session with a
  time). That's how the brainstorm numbers treated it.
- Confidence is worked out on the **whole field** before any filtering (like Avoid
  drivers being left out of the 3 teams), so every driver in the pool has it, including
  the planner's incoming drivers.
- Every place that can lack confidence (provisional previews, old snapshots, sprint
  weekends if they don't pass) shows the card exactly as today, with no label.
- The proving script gets past sessions through the same OpenF1 loaders. It's fine for
  it to save what it fetched to a local file so re-runs are quick, the builder's call.

## Proving it (before it shows on the site)

It doesn't change picks, so there's no points scorecard bar. The bar is that the levels
are honest. A script in `scripts/` rebuilds the check above from the repo's own code:
every finished weekend, each driver's level from the module, against the real grid,
finish (finishers only) and official fantasy points (`data/official_points_2026.json`).
It reports places off and "within 2 places" per level, and how many weekends high beat
low.

- **Normal weekends:** it has to reproduce the brainstorm numbers (high 3.06, medium
  3.46, low 4.56 places off on fantasy points, high beat low 10 of 12) or close to it,
  and high has to beat low on most weekends. If the module's numbers come out
  different, stop and find out why before anything ships.
- **Sprint weekends** (locked on sprint quali, the moved around check uses FP1 and
  sprint quali): measured separately. Confidence only shows on sprint weekends if high
  beats low there too. Otherwise sprint weekends show no confidence and the notes say
  why.
- The numbers go in Decisions and evidence. Re-run after a few races from Mexico, the
  first honest test, and add it to the open tasks.

## Left to the builder

- Field names, and the exact reason wording (plain, facts only, in the mockup's style).
- What the reason says when a check can't be worked out (no teammate in the session,
  a driver who missed a session).
- How the planner shows the incoming driver's level next to its swap reason.
- Where the proving script lives and how it gets the earlier sessions for past rounds.
- How the page legend line is worded.

## Calls I made (Ashen, check these)

- **No confidence on provisional previews.** Before the weekend's lock session (FP3, or
  sprint quali) is in, the moved around check doesn't have its sessions yet, so cards
  show no confidence rather than a half measured one.
- **Old snapshots stay as they are.** Locked weekends from before this project show no
  confidence; we don't go back and add it.
- **The Manual Team page and Predicted Finishes page don't show it** (they weren't on
  the list). The data will be in the pool if we want it there later.
- **Medium stays SAFE**, only low flips a top 3 driver to CONSIDER.
- **Not rushing it for Mexico.** FP1 is Friday 2026-10-30, so backend pushes would have
  to land tomorrow. Built calmly, backend pushes Monday to Thursday. Mexico's real
  results are the first honest test either way, since the proving script can grade it
  afterwards.

## Order of work (suggested)

1. The module, test first: the three checks, the levels, the reason sentence, the
   CONSIDER rule.
2. The proving script. Stop and show Ashen the numbers. If they don't hold up, stop.
3. Wire it into the driver records, the API and the snapshot lock.
4. The cards: 3 teams, 2x pick, planner swaps.
5. Notes.
