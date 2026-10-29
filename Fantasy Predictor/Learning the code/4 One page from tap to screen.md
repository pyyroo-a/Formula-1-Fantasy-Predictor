---
title: 4 One page, from tap to screen
date: 2026-10-30
tags: [pitwall, learning, frontend]
---

# 4. One page, from tap to screen: the Garage

The best way to see how it all fits is to follow one page the whole way. The Garage is a
good one because it touches everything: my saved teams, two questions to the backend,
the rulebook, and the bricks.

Like following one lap of onboard footage: corner by corner.

## Corner 1: I tap "My team", then "Garage"

In `App.jsx` the tab buttons just change state:

```jsx
onClick={() => setSubTab(tab.id)}
```

That sets `myTeamTab` to `"garage"`, React redraws, and this line now says yes:

```jsx
{mode === "garage" && section === "myteam" && <Garage upcomingRaces={upcomingRaces} upcomingReady={upcomingReady} finishes={finishes} />}
```

So the Garage appears, and `App` hands it three things it already asked for when the site
opened: the upcoming races, whether that list has answered yet, and the predicted finish
(the Garage borrows each driver's team from it, because the price list has no teams).

## Corner 2: the Garage reads my saved teams

```jsx
const [teams, setTeams] = useState(loadTeams);
```

`loadTeams` is in `plannerTeams.js`. It opens the browser's notebook (`localStorage`) and
reads `pitwall_planner_teams`:

```js
export function loadTeams() {
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(KEY) || "null"); } catch { /* junk or blocked storage, start empty */ }
  return [0, 1, 2].map(i => clean(Array.isArray(saved) ? saved[i] : null, i));
}
```

Always 3 slots. If the notebook is empty, blocked (private browsing) or has junk in it,
`clean` fills in empty teams instead of crashing. That's why my old planner teams carried
over into the Garage: same notebook page, same shape.

## Corner 3: the price list

Straight after it appears, an effect asks for `/prices` (that's the `useEffect` example
from note 2). The editor needs it to show drivers and prices, even before practice has
happened.

## Corner 4: which race?

```jsx
const racePick = raceToUse(race, upcomingRaces, upcomingReady);
```

From `lib/races.js`: the race I picked in the box, or else the next one. If the race list
hasn't arrived yet it says "loading", if it never came it says so. (That was one of the
reviewer's fixes: before, a cold start made it say my team wasn't finished.)

## Corner 5: asking the backend for the ladder and the chips

When a complete team is picked, the `Results` part of `Garage.jsx` asks two questions at
the same time:

```jsx
const [ladder, chips] = await Promise.all([
  postJson(`${API}/transfer-ladder`, { race_name: raceName, drivers: team.drivers, constructors: team.constructors,
                                       budget: team.budget, free_transfers: team.freeTransfers }),
  postJson(`${API}/chip-advisor`, { race_name: raceName, my_drivers: team.drivers, my_constructors: team.constructors }),
]);
```

`Promise.all` is like sending two engineers to two different garages at once instead of
one after the other, then waiting for both. `postJson` is the safe "ask the backend"
from `lib/api.js`, so even a weird answer can't crash the page.

While it waits, the page shows the grey `Loading` blocks. It knows it's still waiting
because it keeps a `key` for the team and race it asked about. If the answer it has is
for a different key, it's not the right answer yet.

## Corner 6: the kitchen does the maths

On the backend, `/transfer-ladder` is in `src/api/planner.py`, which calls
`transfer_ladder` in `src/planner.py`. That's where "keep your team, or the best team with
1, 2, 3 transfers" is worked out. The website does none of that maths, see
[Planner](../Planner.md). The chips come from `/chip-advisor` the same way, see
[Chips](../Chips.md).

Before FP1 the backend says "No practice data yet for this race". The Garage spots the
word "practice" in that message and shows "No practice yet for Mexico City Grand Prix.
This fills in by itself after FP1", then asks again once a minute.

## Corner 7: the rulebook turns numbers into steps

The ladder comes back as rows like `{ transfers: 2, expected: 188.5 }`. The page hands
them to the rulebook:

```jsx
const steps = ladderSteps(data.rows);
```

`ladderSteps` (in `lib/garage.js`) does the display maths only:

- rounds each row to whole points like the old planner did (188.5 becomes 189),
- works out "+61 vs keeping" from the rounded numbers, so it always matches what you see,
- marks the highest one as the red best step,
- gives each step a height compared to the tallest (never under 40%, so Keep never vanishes),
- and a row with `none: true` says "no team fits" instead of a 0.

Then `stepLabel` gives the plain words ("2 transfers, both free") and `chipOrder` sorts
the chips PLAY first.

## Corner 8: drawing it

The page maps over the steps and draws a block for each, with the height from the
rulebook:

```jsx
{steps.map((s, i) => (
  <button key={s.transfers} onClick={() => setPicked(i)}>
    <div className={s.best ? "bg-pw-red text-pw-bg" : "bg-pw-raised"} style={{ height: `${Math.round(s.height * 120)}px` }}>
      {s.none ? "-" : s.expected}
    </div>
    ...
  </button>
))}
```

(Shortened.) Red if it's the best one, taller if it's more points. Tap one and `picked`
changes, so the swaps under it change (on a phone).

## Corner 9: editing the team

"Edit this team" sets `editing` to true, and the Garage shows `GarageEditor.jsx` instead.
The editor keeps its own copy of the picks while I change them (so Cancel throws them
away), uses the shared `ui/TeamPicker.jsx` (same as Manual team), and on Save:

```jsx
const save = (next) => {
  const all = teams.map((t, i) => (i === active ? next : t));
  setTeams(all);
  saveTeams(all);
  setEditing(false);
};
```

Swap in the new team, write the notebook (`saveTeams`), close the editor. The team's
`key` changed, so corner 5 runs again by itself and the new ladder appears. No "refresh"
button anywhere, the state change does it.

## The whole lap in one go

```
tap Garage
  -> App shows <Garage>
  -> read my teams from localStorage
  -> ask /prices (for the editor)
  -> pick the race (lib/races.js)
  -> ask /transfer-ladder and /chip-advisor together
       -> backend: src/planner.py does the maths
  -> lib/garage.js turns rows into steps and labels
  -> draw blocks, swaps, facts and chips with ui/ bricks
```

Every other page is the same lap with different corners. Overview is even simpler: App
already asked for the team, so it just draws.

Next: [The backend side](5%20The%20backend%20side.md)
