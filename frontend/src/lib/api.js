// One way to ask the backend for something that never throws. Basically the free
// Render server sometimes answers with an HTML error page (or not at all while it
// wakes up), and calling res.json() on that used to blow up the page.

const WAKING = "It might be waking up, try again in a minute.";

export async function fetchJson(url, options = {}) {
  const { fetchImpl = fetch, ...init } = options;
  let res;
  try {
    res = await fetchImpl(url, init);
  } catch {
    return { ok: false, error: `Couldn't reach the server. ${WAKING}` };
  }
  let data;
  try {
    data = await res.json();
  } catch {
    return { ok: false, error: `The server sent something odd (HTTP ${res.status}). ${WAKING}` };
  }
  if (!res.ok || data?.detail) {
    const detail = data?.detail;
    return { ok: false, error: typeof detail === "string" ? detail : `The server didn't like that request (HTTP ${res.status}).` };
  }
  return { ok: true, data };
}

// the usual POST with a JSON body
export function postJson(url, body, options = {}) {
  return fetchJson(url, { ...options, method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
