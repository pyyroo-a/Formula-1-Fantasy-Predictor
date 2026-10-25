// This device's copy of the last weekend team, so the Overview has something to
// show between races. See pickNewer for how it's reconciled with the backend.

// Writes a team payload to this device's cache, ignoring quota/private-mode errors.
export function cacheTeam(d) {
  try { localStorage.setItem("pitwall_last_team", JSON.stringify(d)); } catch {}
}

export function readCachedTeam() {
  try { return JSON.parse(localStorage.getItem("pitwall_last_team") || "null"); }
  catch { return null; }
}

// Picks between this device's cached team and the backend's, by race round.
//
// The cache can legitimately be ahead of the backend for a few hours after a
// race, before the results are published, so the backend does not simply always
// win. But on a tie, or when either round is unknown, the BACKEND wins: it is the
// one answer every device shares, and a cached team that cannot prove it is newer
// is exactly the stale copy this whole comparison exists to get rid of.
//
// The unknown case is not hypothetical. Payloads cached before the `round` field
// existed have no round at all.
export function pickNewer(cached, fromServer) {
  if (!cached) return fromServer;
  if (!fromServer) return cached;
  const rc = Number.isFinite(cached.round) ? cached.round : -1;
  const rs = Number.isFinite(fromServer.round) ? fromServer.round : -1;
  return rc > rs ? cached : fromServer;
}
