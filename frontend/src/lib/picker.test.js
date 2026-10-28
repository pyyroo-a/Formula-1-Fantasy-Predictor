import { test } from "node:test";
import assert from "node:assert/strict";
import { groupByTeam, sortDrivers, sortConstructors, pickTeam1 } from "./picker.js";

const D = [
  { Abbreviation: "LEC", TeamName: "Ferrari", Price: 24.4, FantasyValue: 38 },
  { Abbreviation: "GAS", TeamName: "Alpine", Price: 9.6, FantasyValue: 4.6 },
  { Abbreviation: "HAM", TeamName: "Ferrari", Price: 24.7, FantasyValue: 29.7 },
  { Abbreviation: "NEW", TeamName: null, Price: 1, FantasyValue: 0 },
];

test("groupByTeam puts teams A to Z and teammates together", () => {
  assert.deepEqual(groupByTeam(D).map(g => [g.team, g.drivers.map(d => d.Abbreviation)]),
                   [["Alpine", ["GAS"]], ["Ferrari", ["LEC", "HAM"]], ["Other", ["NEW"]]]);
});

test("sortDrivers by points and by price", () => {
  assert.deepEqual(sortDrivers(D, "points").map(d => d.Abbreviation), ["LEC", "HAM", "GAS", "NEW"]);
  assert.deepEqual(sortDrivers(D, "price").map(d => d.Abbreviation), ["HAM", "LEC", "GAS", "NEW"]);
});

test("sortDrivers doesn't change the list it was given", () => {
  const before = D.map(d => d.Abbreviation);
  sortDrivers(D, "price");
  assert.deepEqual(D.map(d => d.Abbreviation), before);
});

test("constructors A to Z", () => {
  assert.deepEqual(sortConstructors([{ name: "Williams" }, { name: "Alpine" }, { name: "Haas F1 Team" }]).map(c => c.name),
                   ["Alpine", "Haas F1 Team", "Williams"]);
});

test("pickTeam1 copies Team 1 and skips what the pool doesn't have", () => {
  const weekend = { teams: [{ drivers: [{ Abbreviation: "LEC" }, { Abbreviation: "XXX" }], constructors: [{ name: "Ferrari" }] }] };
  const pool = { drivers: D, constructors: [{ name: "Ferrari", price: 28.5, score: 71.2 }] };
  const r = pickTeam1(weekend, pool);
  assert.deepEqual(r.drivers.map(d => d.Abbreviation), ["LEC"]);
  assert.deepEqual(r.constructors.map(c => c.name), ["Ferrari"]);
});

test("pickTeam1 with no weekend team gives nothing", () => {
  assert.deepEqual(pickTeam1(null, { drivers: D, constructors: [] }), { drivers: [], constructors: [] });
});
