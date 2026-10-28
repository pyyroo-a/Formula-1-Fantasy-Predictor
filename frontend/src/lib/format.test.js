import { test } from "node:test";
import assert from "node:assert/strict";
import { fmt1, money, pts, surname, verdictLabel } from "./format.js";

test("fmt1 always shows one decimal", () => {
  assert.equal(fmt1(38), "38.0");
  assert.equal(fmt1(-3.7), "-3.7");
  assert.equal(fmt1(0), "0.0");
});

test("fmt1 shows a plain dash for missing numbers", () => {
  for (const v of [null, undefined, NaN]) assert.equal(fmt1(v), "-");
});

test("money and pts", () => {
  assert.equal(money(3), "$3.0M");
  assert.equal(money(24.1), "$24.1M");
  assert.equal(money(null), "-");
  assert.equal(pts(-3.7), "-3.7 pts");
});

test("surname", () => {
  assert.equal(surname("HUL"), "Hülkenberg");
  assert.equal(surname("ANT"), "Antonelli");
  assert.equal(surname("XYZ"), "XYZ");
});

test("verdictLabel", () => {
  assert.equal(verdictLabel("POST-QUALI"), "AFTER QUALI");
  assert.equal(verdictLabel("PLAY"), "PLAY");
});
