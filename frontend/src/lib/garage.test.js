import { test } from "node:test";
import assert from "node:assert/strict";
import { ladderSteps, stepLabel, teamFromSaved, isComplete, driverTeamMap, pickerDrivers, chipOrder } from "./garage.js";

// the live server's real ladder for the US GP example team (ANT HAM HUL GAS BOT,
// Mercedes, Cadillac, $110M, 3 free transfers)
const ROWS = [{ transfers: 0, paid: 0, expected: 128.2 }, { transfers: 1, paid: 0, expected: 155.0 },
              { transfers: 2, paid: 0, expected: 188.5 }, { transfers: 3, paid: 0, expected: 205.1 }];

test("ladderSteps rounds like the planner always did", () => {
  const s = ladderSteps(ROWS);
  assert.deepEqual(s.map(x => x.expected), [128, 155, 189, 205]);
  assert.deepEqual(s.map(x => x.vsKeep), [null, 27, 61, 77]);
  assert.deepEqual(s.map(x => x.best), [false, false, false, true]);
  assert.equal(s[3].height, 1);
  assert.ok(s[0].height >= 0.4 && s[0].height < 1);
});

test("a row where no team fits the budget", () => {
  const s = ladderSteps([{ transfers: 0, paid: 0, expected: 128.2 }, { transfers: 1, paid: 0, none: true }]);
  assert.equal(s[1].none, true);
  assert.equal(s[1].expected, null);
  assert.equal(s[1].vsKeep, null);
  assert.equal(s[1].height, 0.4);
  assert.equal(s[0].best, true);
});

test("stepLabel says it plainly", () => {
  assert.deepEqual(stepLabel({ transfers: 0, paid: 0 }, 2), { label: "Keep your team", sub: "no changes" });
  assert.deepEqual(stepLabel({ transfers: 1, paid: 0 }, 2), { label: "1 transfer", sub: "free" });
  assert.deepEqual(stepLabel({ transfers: 2, paid: 0 }, 2), { label: "2 transfers", sub: "both free" });
  assert.deepEqual(stepLabel({ transfers: 3, paid: 0 }, 3), { label: "3 transfers", sub: "all 3 free" });
  assert.deepEqual(stepLabel({ transfers: 1, paid: 0 }, 1), { label: "1 transfer", sub: "your free one" });
  assert.deepEqual(stepLabel({ transfers: 3, paid: 1 }, 2), { label: "3 transfers", sub: "one costs 10 points" });
});

test("teamFromSaved keeps a driver who left the price list", () => {
  const prices = { drivers: { LEC: 24.4 }, constructors: { Ferrari: 28.5 } };
  const t = teamFromSaved({ drivers: ["LEC", "DOO", "", "", ""], constructors: ["Ferrari", "RB F1 Team"] }, prices);
  assert.deepEqual(t.drivers.slice(0, 2), [{ code: "LEC", known: true }, { code: "DOO", known: false }]);
  assert.equal(t.drivers.length, 2);
  assert.deepEqual(t.constructors[1], { name: "RB F1 Team", known: false });
});

test("isComplete", () => {
  assert.equal(isComplete({ drivers: ["A", "B", "C", "D", "E"], constructors: ["X", "Y"] }), true);
  assert.equal(isComplete({ drivers: ["A", "B", "C", "D", ""], constructors: ["X", "Y"] }), false);
  assert.equal(isComplete({ drivers: ["A", "B", "C", "D", "E"], constructors: ["X"] }), false);
});

test("driver to team map and the Other group", () => {
  const m = driverTeamMap({ predictions: [{ abbreviation: "LEC", team: "Ferrari" }] });
  assert.deepEqual(pickerDrivers({ drivers: { LEC: 24.4, NEW: 1 } }, m).map(d => [d.Abbreviation, d.TeamName, d.Price]),
                   [["LEC", "Ferrari", 24.4], ["NEW", null, 1]]);
  assert.deepEqual(driverTeamMap(null), {});
});

test("chips best first", () => {
  const chips = { my_team_score: 98.5, autopilot: { recommendation: "SAVE" }, x3_boost: { recommendation: "CONSIDER" },
                  limitless: { recommendation: "PLAY" }, final_fix: { recommendation: "POST-QUALI" }, wildcard: { recommendation: "PLAY" } };
  assert.deepEqual(chipOrder(chips).map(([k]) => k), ["limitless", "wildcard", "x3_boost", "final_fix", "autopilot"]);
});
