import { test } from "node:test";
import assert from "node:assert/strict";
import { raceVerdict, honestLine, dotX, chartMax, nextOpenDot, calendarOrder } from "./insights.js";

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

// one open bubble for the whole chart. Mouse: hover opens, leaving closes. Touch: a tap
// opens, tapping it again or anywhere else closes. Another dot always replaces it
test("hovering opens and leaving closes", () => {
  let open = nextOpenDot(null, { type: "enter", id: "R13|FP3", pointer: "mouse" });
  assert.equal(open, "R13|FP3");
  assert.equal(nextOpenDot(open, { type: "leave", id: "R13|FP3", pointer: "mouse" }), null);
});

test("touch doesn't count as a hover", () => {
  assert.equal(nextOpenDot(null, { type: "enter", id: "R13|FP3", pointer: "touch" }), null);
  assert.equal(nextOpenDot("R13|FP3", { type: "leave", id: "R13|FP3", pointer: "touch" }), "R13|FP3");
});

test("tapping the same dot again closes it", () => {
  const open = nextOpenDot(null, { type: "tap", id: "R13|FP3" });
  assert.equal(open, "R13|FP3");
  assert.equal(nextOpenDot(open, { type: "tap", id: "R13|FP3" }), null);
});

test("a dot on another line replaces the open one", () => {
  assert.equal(nextOpenDot("R13|FP3", { type: "tap", id: "R14|Locked" }), "R14|Locked");
  assert.equal(nextOpenDot("R13|FP3", { type: "enter", id: "R16|Locked", pointer: "mouse" }), "R16|Locked");
});

test("leaving a dot that isn't the open one changes nothing", () => {
  assert.equal(nextOpenDot("R14|Locked", { type: "leave", id: "R13|FP3", pointer: "mouse" }), "R14|Locked");
});

test("tapping anywhere else closes it", () => {
  assert.equal(nextOpenDot("R13|FP3", { type: "outside" }), null);
});

// the chips list goes in calendar order. A track without a round (an old file from
// before we saved it) goes at the end, A to Z, never dropped
test("tracks in calendar order", () => {
  const tracks = [{ track: "Monza", name: "Italian Grand Prix", round: 13 }, { track: "Melbourne", name: "Australian Grand Prix", round: 1 },
                  { track: "Zandvoort", name: "Dutch Grand Prix" }, { track: "Austin", name: "United States Grand Prix", round: 18 },
                  { track: "Baku", name: "Azerbaijan Grand Prix" }];
  assert.deepEqual(calendarOrder(tracks).map(t => t.track), ["Melbourne", "Monza", "Austin", "Baku", "Zandvoort"]);
});
