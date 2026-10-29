---
title: 2 React in 10 minutes
date: 2026-10-30
tags: [pitwall, learning, frontend]
---

# 2. React in 10 minutes

The whole website is built from about six ideas. Once these click, every file in
`frontend/src/` reads the same way. I know Python, so I'll compare where it helps.

## Idea 1: a component is a function that returns a piece of page

In React, a bit of screen is a **component**: a normal function whose answer is "here's
what to draw". The drawing bit looks like HTML sitting inside the code, that's called
**JSX**. Our smallest real one, `ui/StatBox.jsx` (the "Expected points / 144.0" boxes):

```jsx
export default function StatBox({ label, value, sub, accent = "" }) {
  return (
    <div className="flex-1 min-w-0 bg-pw-raised rounded-lg px-3 py-2">
      <div className="text-xs text-pw-muted truncate">{label}</div>
      <div className={`cond-x font-extrabold text-2xl leading-tight num ${accent}`}>{value}</div>
      {sub && <div className="text-xs text-pw-muted">{sub}</div>}
    </div>
  );
}
```

Read it like a Python function: it takes some inputs and returns a little box with a
small label on top and a big number under it. Anything inside `{ }` in the JSX is normal
code, so `{label}` means "put the label here".

Components are like **LEGO bricks**: small ones (a box, a row, a pill) get snapped
together into bigger ones (a team list), and those into whole pages (Overview).

## Idea 2: props are the inputs

The inputs to a component are called **props** (short for properties). Using StatBox
looks like writing an HTML tag with settings, this is from `Overview.jsx`:

```jsx
<StatBox label="Expected points" value={fmt1(team.total_score)} />
<StatBox label="Cost" value={money(team.total_cost)} />
<StatBox label="Left over" value={money(team.budget_remaining)} />
```

Same brick three times, different props. In Python terms it's like calling
`stat_box(label="Cost", value="$99.5M")` three times.

## Idea 3: state is the component's memory

Some things change while you're on the page: which team tab you picked, what you typed
in the budget box. That memory is called **state**, and you make it with `useState`:

```jsx
const [sort, setSort] = useState("team");
```

That one line (from `ManualTeamBuilder.jsx`) means: "remember a value called `sort`,
start it at `"team"`, and here's a function `setSort` to change it". When I tap "By
points", the code calls `setSort("points")`, and **React redraws the page by itself**
with the new sort. I never have to say "now update the screen", that's React's whole job.

Think of it like the scoreboard on a TV broadcast: you change the number in the system,
and the graphic on screen updates itself.

## Idea 4: effects are "do this when the page opens" (or when something changes)

Asking the backend a question is something you do **after** the page appears, not while
drawing it. That's what `useEffect` is for. From `Garage.jsx`, getting the price list
when the Garage opens:

```jsx
useEffect(() => {
  let cancelled = false;
  fetchJson(`${API}/prices`).then(r => {
    if (cancelled) return;
    if (r.ok) setPrices(r.data); else setPricesError(r.error);
  });
  return () => { cancelled = true; };
}, []);
```

In plain words:
- "When this page opens, ask the backend for `/prices`."
- "When the answer comes, save it in state (`setPrices`), which redraws the page with prices in it."
- The `[]` at the end means "only once, when the page opens". If it listed things,
  like `[raceName]`, it would run again whenever the race changed. That's how Manual team
  reloads when you pick another race.
- The `cancelled` bit is just safety: if I leave the page before the answer arrives,
  don't try to update a page that's gone.

## Idea 5: lists with `.map`

The team rows, the 22 race results, the chip cards: they're all one brick repeated for
every item in a list. JavaScript's `.map` is like a Python list comprehension.

```jsx
{team.drivers.map(d => (
  <TowerRow
    key={d.Abbreviation}
    spot={`P${Math.round(d.Predicted)}`}
    color={teamAccent(d.TeamName)}
    name={DRIVER_NAMES[d.Abbreviation] || d.Abbreviation}
    right={money(d.Price)}
    rightSub={pts(d.FantasyValue)}
  />
))}
```

That's "for every driver, draw a timing tower row". The Python version would be
`[tower_row(d) for d in team.drivers]`. The `key` is just a name tag so React can tell
the rows apart when the list changes.

## Idea 6: showing something only sometimes

Two tiny patterns you'll see everywhere:

```jsx
{sub && <div>{sub}</div>}                       // only if sub exists
{held ? "What we predicted for " : "Predicted finish for "}   // one or the other
```

`a && b` means "if a, show b". `a ? b : c` means "if a, show b, else c" (like Python's
`b if a else c`). That's how the confidence key only shows when the lock has confidence,
and how the hold banner only shows between races.

## And the styling: Tailwind

All those `className="flex text-xs text-pw-muted"` bits are **Tailwind**. Instead of
writing a separate style file, each class is one small style: `text-xs` = small text,
`text-pw-muted` = our grey, `rounded-lg` = rounded corners, `sm:` in front means "only
on screens wider than a phone". The `pw-` colours (`pw-red`, `pw-panel`...) are ours,
set once in `frontend/tailwind.config.js`. Change a colour there and the whole site
changes.

## The 6 ideas on one card

| Idea | In one line | React word |
|---|---|---|
| 1 | a function that returns a bit of page | component, JSX |
| 2 | its inputs | props |
| 3 | its memory, change it and the page redraws | `useState` |
| 4 | do something after the page appears | `useEffect` |
| 5 | one brick for every item in a list | `.map` |
| 6 | show it only sometimes | `&&` and `? :` |

Next: [The frontend, file by file](3%20The%20frontend%20file%20by%20file.md)
