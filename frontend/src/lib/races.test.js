import { test } from "node:test";
import assert from "node:assert/strict";
import { raceToUse } from "./races.js";

const UPCOMING = [{ race_name: "Mexico City Grand Prix" }, { race_name: "São Paulo Grand Prix" }];

test("the race you picked, or else the next one", () => {
  assert.deepEqual(raceToUse("", UPCOMING, true), { name: "Mexico City Grand Prix", state: "ok" });
  assert.deepEqual(raceToUse("São Paulo Grand Prix", UPCOMING, true), { name: "São Paulo Grand Prix", state: "ok" });
});

test("while the race list is still on its way it says loading, not that your team isn't finished", () => {
  assert.deepEqual(raceToUse("", [], false), { name: "", state: "loading" });
});

test("if the race list never came, it says so", () => {
  assert.deepEqual(raceToUse("", [], true), { name: "", state: "failed" });
});
