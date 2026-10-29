---
title: Frontend
date: 2026-10-30
tags: [pitwall, frontend]
---

# Frontend

React + Vite + Tailwind, deployed on Vercel from `frontend/`. It reads the backend at
`VITE_API_URL` (set on Vercel, Vite bakes it in at build time so a change needs a
redeploy). Locally it falls back to `http://127.0.0.1:8000`.

The whole site got one redesign at the end of October 2026 (design in
[`docs/superpowers/specs/2026-10-28-ui-redesign-design.md`](../docs/superpowers/specs/2026-10-28-ui-redesign-design.md),
mockups next to it). Dark timing tower look, the Archivo font, one red accent, and every
page works on a phone (375px) with no sideways scrolling.

## The pages

Four sections. On a laptop they're in the header, on a phone in a bar at the bottom that
sits above the home bar (that's what `viewport-fit=cover` in `index.html` is for).

- **Overview** (`components/Overview.jsx`): the weekend's 3 teams with a Team 1/2/3
  switcher, the 2x pick in its own box with its reason, the team as timing tower rows
  (predicted spot, team colour, name, price, points, Safe/Risk, DNF %, confidence pill),
  the confidence key (only when the lock has confidence), the chips for that team
  (`AutoChipAdvisor.jsx`), weather, the predicted finish (with "finished P2" once the
  Monday job has the results) and prices. Between races it shows the HELD team.
- **My team**, two tabs:
  - **Manual team** (`ManualTeamBuilder.jsx`): picks the next race, checks if practice has
    happened and loads the drivers by itself (or says "no practice yet" and checks once a
    minute). Drivers by team A to Z, constructors A to Z, by points or price too. Your
    budget is remembered as `pitwall_budget`. "Start from PitWall Team 1" shows on a race
    weekend.
  - **Garage** (`components/myteam/Garage.jsx` and `GarageEditor.jsx`): took over the old
    Planner and Chip Advisor. Your 3 real teams, saved by `plannerTeams.js` as
    `pitwall_planner_teams` (same format as the planner, so they carried over). For the
    team you pick it shows the transfer ladder as steps and the chips, both loaded by
    itself. See [Planner](Planner.md) and [Chips](Chips.md).
  - The Team Optimizer got dropped in the redesign (old races at today's prices wasn't
    useful). `/predict-budget` is still on the backend, unused.
- **Race data** (`components/racedata/RaceDataPage.jsx`): one page, pick a race, then a
  session strip (FP1 to Race, FP1 only on sprint weekends). Practice comes from OpenF1 on
  the backend. Backtest shows as a second tab only when running locally
  (`import.meta.env.DEV`).
- **Insights**, three tabs:
  - **Predicted finishes** (`PredictedFinishes.jsx`): model vs practice order, and how
    they did once the race is in.
  - **Track record** (`TrackRecord.jsx`, project 5): the honest headline, four boxes, a
    line per race with a dot per team (tap or hover for a bubble), or as a table. Reads
    `/track-record`.
  - **Chips** (`ChipHistory.jsx`, project 6): best and worst tracks per chip with who
    scored the 3x, every track folded away in calendar order with a key, and "how we
    picked these tracks". Reads `/chip-history`.

## How it fits together

- `App.jsx` is the shell: the header, the sections and tabs, and the fetches everything
  shares (races, next race, prices, the weekend team, predicted finishes). It wraps each
  page in an error boundary, so a crash shows a message instead of a black screen.
- `ui/` is the look, shared by every page: `TowerRow` (one timing tower row), `Switcher`,
  `Confidence` (pill, key, reason), `StatBox`, `VerdictTag` (PLAY, AFTER QUALI...),
  `Panel`, `Loading` and `ErrorLine`, `TeamPicker` (Manual team and the Garage),
  `RiskTag`, `ErrorBoundary`.
- `lib/` is the plain logic with no React in it, each file with its own tests:
  `format.js` (one decimal everywhere, `$24.1M`), `api.js` (`fetchJson` and `postJson`,
  which never throw, so the free server's HTML error pages can't crash a page),
  `overview.js`, `picker.js`, `garage.js` (the ladder steps and labels), `racedata.js`,
  `races.js` (which race a page works on, and "loading" vs "the race list never came"),
  `insights.js` (the track record words, the bubble, calendar order).
- `hooks/useRaceData.js` holds the Race data state, called in `App`, not inside the page,
  on purpose: the page unmounts when you switch away, and keeping the state in `App` is
  what makes your picked race still be there when you come back.
- `teamCache.js`: this device's copy of the last weekend team (`pitwall_last_team`) and
  `pickNewer`, which compares it with the backend's by round number. This used to be the
  bug where my phone showed the Dutch GP team while the laptop showed Monza.
- `constants.js`: driver names, team colours, chip info (`CHIP_META`, colours match the
  official F1 Fantasy app), badge colours. `confidence.js`: `displayCategory`, which shows
  a Safe driver with low confidence as CONSIDER (display only).
- `styles.js`: the shared input and button classes. `index.css` and `tailwind.config.js`:
  the colours (`pw-bg`, `pw-panel`, `pw-red`...) and the Archivo font.
- `public/`: the fast P icon (`favicon.svg`, `favicon-32.png` as the backup), the home
  screen icons (`apple-touch-icon.png`, `icon-*.png` and `site.webmanifest`, those have a
  white P because iPhone dark mode drops the red background), `drivers/<CODE>.avif`
  headshots.

## Checking a change

- `npm test` runs the `lib/` tests with Node's own test runner (no extra package).
- `npm run build` has to pass. `npm run lint` has 4 old errors (an empty catch block, two
  setState in an effect, one unused variable), don't add new ones.
- Then click through every page locally at laptop width and phone width, including
  picking a race in Race data and flicking between sessions.

Related: [API](API.md), [How-tos](How-tos.md)
