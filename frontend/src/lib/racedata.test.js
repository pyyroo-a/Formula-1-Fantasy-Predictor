import { test } from "node:test";
import assert from "node:assert/strict";
import { qualiTag, sessionOptions, raceChange, needsFetch } from "./racedata.js";

// real US GP rows from /qualifying-results and /race-results
test("qualiTag", () => {
  assert.deepEqual(qualiTag({ Q1: "1:35.390", Q2: "1:34.278", Q3: "1:34.035" }), { time: "1:34.035", tag: "Q3" });
  assert.deepEqual(qualiTag({ Q1: "1:35.662", Q2: "1:35.058", Q3: null }), { time: "1:35.058", tag: "out in Q2" });
  assert.deepEqual(qualiTag({ Q1: "1:36.531", Q2: null, Q3: null }), { time: "1:36.531", tag: "out in Q1" });
  assert.deepEqual(qualiTag({ Q1: null, Q2: null, Q3: null }), { time: "-", tag: "out in Q1" });
});

test("sessionOptions", () => {
  assert.deepEqual(sessionOptions(null), ["FP1", "FP2", "FP3", "Quali", "Race"]);
  assert.deepEqual(sessionOptions(["FP1"]), ["FP1", "Quali", "Race"]);
});

test("raceChange", () => {
  assert.deepEqual(raceChange({ PositionChange: 2, Status: "Finished", GridPosition: 4 }), { text: "+2", tone: "up", from: "from P4" });
  assert.deepEqual(raceChange({ PositionChange: -3, Status: "Finished", GridPosition: 3 }), { text: "-3", tone: "down", from: "from P3" });
  assert.deepEqual(raceChange({ PositionChange: 0, Status: "Lapped", GridPosition: 9 }), { text: "same", tone: "same", from: "from P9" });
  assert.deepEqual(raceChange({ PositionChange: -1, Status: "DNF", GridPosition: 19 }), { text: "", tone: "none", from: "from P19" });
  assert.deepEqual(raceChange({ PositionChange: null, Status: "Finished", GridPosition: null }), { text: "", tone: "none", from: "" });
});

// a session that loaded stays kept, one that failed (server asleep) gets asked again
test("only answers that worked are kept", () => {
  const answers = { "US GP|Race": { ok: true, data: [] }, "US GP|Quali": { ok: false, error: "Couldn't reach the server." } };
  assert.equal(needsFetch(answers, "US GP|Race"), false);
  assert.equal(needsFetch(answers, "US GP|Quali"), true);
  assert.equal(needsFetch(answers, "US GP|FP3"), true);
});
