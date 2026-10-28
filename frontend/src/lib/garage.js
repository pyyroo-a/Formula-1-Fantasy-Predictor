// The Garage's plain logic: the transfer steps, their labels, your saved team against
// the price list, and the chips in best first order. The maths is the backend's
// (src/planner.py), this only lays it out.
import { CHIP_META } from "../constants.js";

// the steps, Keep then 1, 2, 3 transfers. Whole points like the planner always showed,
// and "vs keeping" from the rounded numbers so it always equals what's on screen.
// height is the step's share of the tallest, never under 0.4 so Keep doesn't vanish
export function ladderSteps(rows) {
  const keep = rows?.[0];
  const rounded = (rows || []).map(r => (r.none ? null : Math.round(r.expected)));
  const top = Math.max(...rounded.filter(v => v != null));
  const bestIdx = rounded.indexOf(top);
  return (rows || []).map((r, i) => {
    const expected = rounded[i];
    return {
      transfers: r.transfers,
      expected,
      vsKeep: i === 0 || expected == null ? null : expected - Math.round(keep.expected),
      best: i === bestIdx,
      none: !!r.none,
      height: expected == null || top <= 0 ? 0.4 : Math.max(0.4, expected / top),
    };
  });
}

export function stepLabel(row, free) {
  if (row.transfers === 0) return { label: "Keep your team", sub: "no changes" };
  const label = row.transfers === 1 ? "1 transfer" : `${row.transfers} transfers`;
  if (row.paid) return { label, sub: "one costs 10 points" };
  if (row.transfers === free) {
    return { label, sub: free === 1 ? "your free one" : free === 2 ? "both free" : `all ${free} free` };
  }
  return { label, sub: "free" };
}

// your saved picks next to today's price list. Anything that isn't in it any more
// stays, marked unknown, so it never just disappears from your team
export function teamFromSaved(saved, prices) {
  const drivers = (saved?.drivers || []).filter(Boolean)
    .map(code => ({ code, known: code in (prices?.drivers || {}) }));
  const constructors = (saved?.constructors || []).filter(Boolean)
    .map(name => ({ name, known: name in (prices?.constructors || {}) }));
  return { drivers, constructors };
}

export function isComplete(team) {
  return team?.drivers?.length === 5 && team.drivers.every(Boolean)
    && team?.constructors?.length === 2 && team.constructors.every(Boolean);
}

// /prices has no teams, so the picker borrows them from the predicted finish list
export function driverTeamMap(finishes) {
  const map = {};
  for (const p of finishes?.predictions || []) map[p.abbreviation] = p.team;
  return map;
}

export function pickerDrivers(prices, teamMap) {
  return Object.entries(prices?.drivers || {}).map(([code, price]) => ({
    Abbreviation: code, TeamName: teamMap[code] || null, Price: price,
  }));
}

const RANK = { PLAY: 0, CONSIDER: 1 };

// PLAY first, then CONSIDER, then the rest, each in the usual chip order
export function chipOrder(chips) {
  return Object.keys(CHIP_META)
    .filter(key => chips?.[key])
    .map((key, i) => ({ key, i, rank: RANK[chips[key].recommendation] ?? 2 }))
    .sort((a, b) => a.rank - b.rank || a.i - b.i)
    .map(({ key }) => [key, chips[key]]);
}
