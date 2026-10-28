import { test } from "node:test";
import assert from "node:assert/strict";
import { showConfidenceKey, finishLine } from "./overview.js";

test("no key when nobody has a confidence", () => {
  assert.equal(showConfidenceKey([{ Abbreviation: "LEC" }, { Abbreviation: "HAM", Confidence: null }]), false);
  assert.equal(showConfidenceKey([{ Confidence: "high" }]), true);
  assert.equal(showConfidenceKey(undefined), false);
});

test("finishLine hides the real result until results are in", () => {
  assert.deepEqual(finishLine({ model_pos: 1, actual_pos: 2, actual_status: "Finished" }, false),
                   { spot: "P1", finished: null, close: false });
});

test("finishLine after the race", () => {
  assert.deepEqual(finishLine({ model_pos: 1, actual_pos: 2, actual_status: "Finished" }, true),
                   { spot: "P1", finished: "finished P2", close: true });
  assert.equal(finishLine({ model_pos: 7, actual_pos: 11, actual_status: "Finished" }, true).close, false);
  assert.equal(finishLine({ model_pos: 20, actual_pos: null, actual_status: "DNF" }, true).finished, "DNF");
});
