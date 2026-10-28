---
title: Frontend
date: 2026-10-25
tags: [pitwall, frontend]
---

# Frontend

React + Vite + Tailwind, deployed on Vercel from `frontend/`. It reads the backend at
`VITE_API_URL` (set on Vercel, Vite bakes it in at build time so a change needs a
redeploy). Locally it falls back to `http://127.0.0.1:8000`.

## The pages

The header has 4 sections, and two of them have tabs:

- **Overview** (`components/Overview.jsx`): the weekend team with the Team 1/2/3
  switcher, chip advice per team (`AutoChipAdvisor.jsx`), prices, weather, the
  predicted finish. Between races it shows the HELD team.
- **My Team**: Team Optimizer (`components/myteam/TeamOptimizerTab.jsx`, 3 teams for
  any race), Manual Team (`ManualTeamBuilder.jsx` with its cards in
  `ManualTeamParts.jsx`, pick your own and see how it scores, remembers your budget),
  Chip Advisor (`ChipAdvisor.jsx`), Planner (`components/myteam/TransferPlanner.jsx`,
  my 3 real teams and the transfer ladder, saved by `plannerTeams.js` as
  `pitwall_planner_teams` in localStorage, see [Planner](Planner.md)).
- **Race Data**: Practice, Qualifying, Race Results (`components/racedata/`), plus
  Backtest when running locally only (`import.meta.env.DEV`).
- **Insights**: two sub tabs. Predicted finishes, model vs practice order, and how
  they did (`PredictedFinishes.jsx`). Track record (`TrackRecord.jsx`, project 5): what
  PitWall's locked team 1 really scored each weekend vs copy the FP3 order, most
  expensive, copy the crowd and the best possible, green where PitWall won, amber
  where it lost. Reads `/track-record`.

## How it fits together

- `App.jsx` is the shell: the header, nav, tabs, and the fetches everything shares
  (races, next race, prices, the weekend team, predicted finishes).
- `hooks/useRaceData.js` holds the state and fetching for the Race Data tabs and the
  Team Optimizer. They're called in `App`, not inside the tabs, on purpose: a tab
  unmounts when you switch away, and keeping the state in `App` is what makes your
  picked race still be there when you come back.
- `teamCache.js`: this device's copy of the last weekend team (`pitwall_last_team` in
  localStorage), and `pickNewer`, which compares it with the backend's by round number.
  This used to be the bug where my phone showed the Dutch GP team while the laptop
  showed Monza.
- `styles.js`: the shared form classes (inputs, the red button, section headings).
- `constants.js`: driver names, team colours, chip info, badge colours.
- `components/BudgetTeam.jsx`: the driver, constructor, 2x and stats cards the team
  views share, plus `ConfidencePill` and `ConfidenceReason` (project 4).
- `confidence.js`: the confidence legend line, and `displayCategory`, which shows a
  Safe driver with low confidence as CONSIDER. Display only, the driver is still Safe.
  The main page teams (`Overview.jsx`) and the planner's swaps use these. No
  confidence on a driver means no pill and no reason line. (One small change for
  everyone: long names on the main page now wrap on a phone instead of getting cut off.)
- `public/drivers/<CODE>.avif`: driver headshots.

## Checking a change

`npm run build` has to pass. `npm run lint` currently has 7 old errors (empty catch
blocks, two setState-in-effect warnings, one unused variable), don't add new ones.
There are no frontend tests, so click through every tab locally, including picking a
race in Practice, switching to Qualifying and back.

Related: [API](API.md), [How-tos](How-tos.md)
