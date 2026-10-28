// How the team picker lays drivers and constructors out (Manual team and the Garage
// both use it). Teams A to Z so you can find someone fast, teammates side by side.
import { surname } from "./format.js";

const bySurname = (a, b) => surname(a.Abbreviation).localeCompare(surname(b.Abbreviation));

// [{ team, drivers }], teams A to Z, drivers in the order given. A driver with no
// team (a brand new name nobody has mapped yet) goes in "Other" at the end, never dropped
export function groupByTeam(drivers) {
  const groups = new Map();
  for (const d of drivers || []) {
    const team = d.TeamName || "Other";
    if (!groups.has(team)) groups.set(team, []);
    groups.get(team).push(d);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => (a === "Other") - (b === "Other") || a.localeCompare(b))
    .map(([team, list]) => ({ team, drivers: list }));
}

// "team" keeps the list as is (the picker groups it), points and price go high to low
export function sortDrivers(drivers, by) {
  const list = [...(drivers || [])];
  if (by === "points") return list.sort((a, b) => (b.FantasyValue ?? -Infinity) - (a.FantasyValue ?? -Infinity) || bySurname(a, b));
  if (by === "price") return list.sort((a, b) => (b.Price ?? 0) - (a.Price ?? 0) || bySurname(a, b));
  return list;
}

export function sortConstructors(constructors) {
  return [...(constructors || [])].sort((a, b) => a.name.localeCompare(b.name));
}

// PitWall's Team 1 this weekend, as entries from the pool, so you can start from it
// and swap. Anything the pool doesn't have gets skipped
export function pickTeam1(weekend, pool) {
  const team = weekend?.teams?.[0] || weekend?.team;
  if (!team || !pool) return { drivers: [], constructors: [] };
  const drivers = team.drivers
    .map(d => pool.drivers.find(p => p.Abbreviation === d.Abbreviation))
    .filter(Boolean);
  const constructors = (team.constructors || [])
    .map(c => pool.constructors.find(p => p.name === c.name))
    .filter(Boolean);
  return { drivers, constructors };
}
