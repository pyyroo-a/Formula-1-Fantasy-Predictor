import { test } from "node:test";
import assert from "node:assert/strict";
import { raceVerdict, honestLine, dotX, chartMax } from "./insights.js";

// real rows and summary from /track-record (R13 to R18, 2026)
test("raceVerdict", () => {
  assert.deepEqual(raceVerdict({ Locked: 147, "FP3 order": 205 }), { text: "147 lost to FP3's 205", won: false });
  assert.deepEqual(raceVerdict({ Locked: 145, "FP3 order": 129 }), { text: "145 beat FP3's 129", won: true });
  assert.deepEqual(raceVerdict({ Locked: 145, "FP3 order": null }), { text: "", won: null });
});

test("raceVerdict on a tie", () => {
  assert.deepEqual(raceVerdict({ Locked: 150, "FP3 order": 150 }), { text: "150 tied with FP3's 150", won: null });
});

test("honestLine follows the averages", () => {
  assert.equal(honestLine({ Locked: { avg: 175.2 }, "FP3 order": { avg: 187.0 } }), "Copying the FP3 order scored a bit more so far.");
  assert.equal(honestLine({ Locked: { avg: 190 }, "FP3 order": { avg: 187 } }), "PitWall scored more than copying the FP3 order so far.");
  assert.equal(honestLine({ Locked: { avg: null }, "FP3 order": { avg: 187 } }), "");
});

test("chart scale", () => {
  assert.equal(chartMax([{ cells: { "Hindsight best": 428 } }, { cells: { "Hindsight best": 199 } }]), 450);
  assert.equal(chartMax([{ cells: { "Hindsight best": null } }]), 50);
  assert.equal(dotX(225, 450), 50);
  assert.equal(dotX(999, 450), 100);
  assert.equal(dotX(-5, 450), 0);
});
