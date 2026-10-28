import { test } from "node:test";
import assert from "node:assert/strict";
import { fetchJson } from "./api.js";

// a pretend fetch that answers with this status and body
const answer = (status, body) => async () => new Response(body, { status });

test("fetchJson gives the data", async () => {
  const r = await fetchJson("x", { fetchImpl: answer(200, JSON.stringify({ a: 1 })) });
  assert.deepEqual(r, { ok: true, data: { a: 1 } });
});

test("fetchJson gives the server's detail", async () => {
  const body = JSON.stringify({ detail: "No practice data yet for this race, the ladder needs at least FP1." });
  const r = await fetchJson("x", { fetchImpl: answer(400, body) });
  assert.deepEqual(r, { ok: false, error: "No practice data yet for this race, the ladder needs at least FP1." });
});

test("fetchJson survives an HTML 500", async () => {
  const r = await fetchJson("x", { fetchImpl: answer(500, "Internal Server Error") });
  assert.deepEqual(r, { ok: false, error: "The server sent something odd (HTTP 500). It might be waking up, try again in a minute." });
});

test("fetchJson survives a network failure", async () => {
  const r = await fetchJson("x", { fetchImpl: async () => { throw new TypeError("Failed to fetch"); } });
  assert.deepEqual(r, { ok: false, error: "Couldn't reach the server. It might be waking up, try again in a minute." });
});

test("fetchJson with a detail that isn't a sentence", async () => {
  const body = JSON.stringify({ detail: [{ msg: "field required" }] });
  const r = await fetchJson("x", { fetchImpl: answer(422, body) });
  assert.equal(r.ok, false);
  assert.equal(r.error, "The server didn't like that request (HTTP 422).");
});
