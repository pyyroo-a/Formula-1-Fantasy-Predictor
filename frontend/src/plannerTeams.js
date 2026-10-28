// My 3 real teams for the transfer planner, saved in this browser only
// (pitwall_planner_teams in localStorage). The game lets you play 3 teams, so we keep
// 3 slots. Anything broken in storage just gives 3 empty teams, never a crash.

const KEY = "pitwall_planner_teams";

export function emptyTeam(i) {
  return {
    name: `Team ${i + 1}`,
    drivers: ["", "", "", "", ""],
    constructors: ["", ""],
    budget: 100,
    freeTransfers: 2,
  };
}

// keeps whatever looks right from a saved team and fills the rest from an empty one
function clean(saved, i) {
  const base = emptyTeam(i);
  if (!saved || typeof saved !== "object") return base;
  const list = (v, n) => (Array.isArray(v) && v.length === n ? v.map(x => (typeof x === "string" ? x : "")) : null);
  const budget = Number(saved.budget);
  const free = Number(saved.freeTransfers);
  return {
    name: typeof saved.name === "string" && saved.name.trim() ? saved.name : base.name,
    drivers: list(saved.drivers, 5) || base.drivers,
    constructors: list(saved.constructors, 2) || base.constructors,
    budget: Number.isFinite(budget) && budget > 0 ? budget : base.budget,
    freeTransfers: [1, 2, 3].includes(free) ? free : base.freeTransfers,
  };
}

export function loadTeams() {
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(KEY) || "null"); } catch { /* junk or blocked storage, start empty */ }
  return [0, 1, 2].map(i => clean(Array.isArray(saved) ? saved[i] : null, i));
}

export function saveTeams(teams) {
  try { localStorage.setItem(KEY, JSON.stringify(teams)); } catch { /* private mode or full, it just won't remember */ }
}
