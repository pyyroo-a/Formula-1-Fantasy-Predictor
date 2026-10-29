---
title: 3 The frontend, file by file
date: 2026-10-30
tags: [pitwall, learning, frontend]
---

# 3. The frontend, file by file

Everything lives in `frontend/src/`. Think of it like an F1 team:

| Folder or file | Team version | What it is |
|---|---|---|
| `main.jsx` | turning the car on | starts React and puts `App` on the page |
| `App.jsx` | the pit wall | the header, the four sections, and the questions everyone shares |
| `components/` | the race engineers | one file per page (Overview, Garage, Race data...) |
| `ui/` | the spare parts shelf | the bricks every page reuses (rows, switchers, pills) |
| `lib/` | the rulebook | plain rules with no drawing in them, each with its own tests |
| `hooks/` | the team's memory | state that has to survive switching pages |
| `constants.js`, `styles.js`, `index.css` | the livery | names, colours, fonts |

## `main.jsx`: turning it on

```jsx
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

`index.html` has one empty box called `root`. This says "draw `App` inside it". That's
the only job of this file, I'll basically never touch it.

## `api.js`: where the backend is

```js
export const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
```

The backend's address. On Vercel, `VITE_API_URL` is set to the Render address. On my
laptop, if nothing is set, it uses the local backend. Every question the site asks starts
with `${API}/...`.

## `App.jsx`: the pit wall

The biggest and most important file. Three jobs:

1. **Remember which page you're on**: `section` (Overview, My team...) and which tab
   inside it, all with `useState`.
2. **Ask the shared questions once**, when the site opens:

   ```jsx
   useEffect(() => {
     fetch(`${API}/races`).then(r => r.json()).then(setRaces).catch(() => {});
     fetch(`${API}/next-race`).then(r => r.json()).then(setNextRace).catch(() => {});
     fetch(`${API}/weekend-team`).then(r => r.json()).then(d => { ... });
     ...
   }, []);
   ```

   Why here and not in each page? Because several pages need the same answers (the
   weekend team is used by Overview and by Manual team's "Start from PitWall Team 1"). Ask
   once, hand it down as props.
3. **Draw the shell**: the header with the fast P, the bottom bar on phones, the sub tabs,
   and then the right page:

   ```jsx
   {section === "overview" && <Overview weekendData={overviewWeekend} ... />}
   {mode === "garage" && section === "myteam" && <Garage upcomingRaces={upcomingRaces} ... />}
   ```

   That's idea 6 from the last note: "if you're on this section, show this page".

It also wraps every page in an **error boundary** (`ui/ErrorBoundary.jsx`). It's like a
safety net under a trapeze: if a page crashes while drawing, the net catches it and says
"Something on this page broke" instead of the whole screen going black. That was the
black screen I used to see.

### The held team bit

There's a clever part in `App.jsx` with `teamCache.js`. Between races the backend says
"no live weekend", so the main page shows the last locked team. My phone also keeps its
own copy. They can disagree (that was the Dutch GP vs Monza bug), so `pickNewer` picks
whichever has the higher round number. Newest wins, simple.

## `components/`: one file per page

| File | Page |
|---|---|
| `Overview.jsx` | the main page |
| `AutoChipAdvisor.jsx` | the chip cards on the main page |
| `WeatherWidget.jsx`, `CountdownWidget.jsx` | the weather boxes, "Race in 3d 02:14" |
| `ManualTeamBuilder.jsx` | My team > Manual team |
| `myteam/Garage.jsx`, `myteam/GarageEditor.jsx` | My team > Garage, and its add or edit screen |
| `racedata/RaceDataPage.jsx` | Race data |
| `PredictedFinishes.jsx`, `TrackRecord.jsx`, `ChipHistory.jsx` | the three Insights tabs |
| `SessionSchedule.jsx`, `DriverAvatar.jsx` | small helpers (session times, headshots) |
| `Backtest.jsx` | only shows when running on my laptop |

Each page does the same three things: ask its own questions (if it has any), keep its
own state (what you picked), and draw itself out of `ui/` bricks.

## `ui/`: the spare parts shelf

The bricks every page uses, so the whole site looks like one site:

- `TowerRow.jsx`: one timing tower row (spot, team stripe, name, numbers on the right).
  Used on Overview, Race data, and more.
- `Switcher.jsx`: the segmented buttons (Team 1/2/3, FP1 to Race, 1/2/3 free transfers).
- `Confidence.jsx`: the high, medium, low pill, the key line and the reason line.
- `StatBox.jsx`, `Panel.jsx`, `VerdictTag.jsx` (PLAY, AFTER QUALI), `RiskTag.jsx` (DNF %).
- `TeamPicker.jsx`: the whole driver and constructor picker, shared by Manual team and the Garage.
- `Loading.jsx`: the grey blocks and "the free server can take up to 30 seconds".
- `ErrorBoundary.jsx`: the safety net.

If I want to change how every row on the site looks, I change `TowerRow.jsx` once.

## `lib/`: the rulebook

This is the bit I'll understand fastest, because it's just logic, like Python functions.
No drawing, no React. A real one from `lib/format.js`:

```js
export function fmt1(n) {
  return missing(n) ? "-" : Number(n).toFixed(1);
}
```

"Show a number with one decimal, or a dash if it's missing." That's why every price and
points total on the site looks the same (38.0, never 38).

The most important one is `lib/api.js`, the safe way to ask the backend:

```js
export async function fetchJson(url, options = {}) {
  ...
  try {
    res = await fetchImpl(url, init);
  } catch {
    return { ok: false, error: "Couldn't reach the server. It might be waking up, try again in a minute." };
  }
  ...
  return { ok: true, data };
}
```

It always comes back with either `{ ok: true, data }` or `{ ok: false, error }`, it never
crashes. It's like a radio message that always arrives, even if what it says is "no
signal". Before the redesign, a weird answer from the sleepy server could crash a page.

The other rule files, one line each:

| File | Rules for |
|---|---|
| `overview.js` | when to show the confidence key, the "finished P2" line |
| `picker.js` | drivers grouped by team A to Z, sorting, "Start from PitWall Team 1" |
| `garage.js` | the transfer steps (rounding, heights, the red best one), labels, chip order |
| `racedata.js` | the quali tag ("out in Q2"), the session strip, "+2 from P4", when to ask again |
| `races.js` | which race a page works on, and "loading" vs "the race list never came" |
| `insights.js` | the track record words, the dot positions, the bubble, calendar order |

Every one of these has a `.test.js` file next to it (more on that in
[Tests and checking](6%20Tests%20and%20checking.md)).

### Why split `lib/` from the pages?

Because rules are easy to test and pages are not. "Does 205.1 round to 205 and say +77?"
is a one line test in `lib/garage.test.js`. Testing the same thing by clicking around the
page would be slow and easy to forget. So the page just asks the rulebook and draws.

## `hooks/useRaceData.js`: memory that survives switching

When I leave Race data and come back, the race I picked is still there. That's because
its state lives in `App` (which never goes away), not in the page (which gets thrown away
when I switch). `useRaceWeekend` is that memory, plus a little cache: answers that
worked are kept, so flicking between FP3 and Quali doesn't ask the server twice.

## The livery: `constants.js`, `styles.js`, `index.css`, `tailwind.config.js`

- `constants.js`: driver names (`LEC` is Charles Leclerc), team colours, the chip info and
  colours (matched to the F1 app).
- `tailwind.config.js` and `index.css`: our colours (`pw-red`, `pw-panel`...), the Archivo
  font, and the phone bar's safe area (the space above the iPhone home bar).
- `styles.js`: the input box and red button styles.

Next: [One page, from tap to screen](4%20One%20page%20from%20tap%20to%20screen.md)
