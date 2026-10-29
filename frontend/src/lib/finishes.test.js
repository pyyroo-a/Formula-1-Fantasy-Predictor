import { test } from "node:test";
import assert from "node:assert/strict";
import { finishRows, rightSpot } from "./finishes.js";

// real US GP lines from /weekend-finishes
const PREDS = [
  { abbreviation: "LEC", team: "Ferrari", model_pos: 1, baseline_pos: 1, delta: 0, actual_pos: 2, actual_status: "Finished" },
  { abbreviation: "RUS", team: "Mercedes", model_pos: 8, baseline_pos: 6, delta: -2, actual_pos: 8, actual_status: "Finished" },
  { abbreviation: "HUL", team: "Audi", model_pos: 7, baseline_pos: 8, delta: 1, actual_pos: 11, actual_status: "Finished" },
  { abbreviation: "BOT", team: "Cadillac", model_pos: 22, baseline_pos: 22, delta: 0, actual_pos: null, actual_status: "DNF" },
];

test("each driver gets judged once the results are in", () => {
  const rows = finishRows(PREDS, true);
  assert.deepEqual(rows.map(r => [r.code, r.finished, r.status]),
                   [["LEC", 2, "close"], ["RUS", 8, "exact"], ["HUL", 11, "off"], ["BOT", null, "dnf"]]);
  assert.equal(rows[2].offBy, 4);
});

test("before the results nobody gets judged", () => {
  const rows = finishRows(PREDS, false);
  assert.deepEqual(rows.map(r => [r.finished, r.status]), [[null, null], [null, null], [null, null], [null, null]]);
  assert.equal(rows[0].practice, 1);
});

test("missing predictions give an empty list", () => {
  assert.deepEqual(finishRows(null, true), []);
});

test("a DNF goes to its own spot under the last place on the lines view", () => {
  const rows = finishRows(PREDS, true);
  assert.equal(rightSpot(rows[1], 22), 8);
  assert.equal(rightSpot(rows[3], 22), 23);
});
