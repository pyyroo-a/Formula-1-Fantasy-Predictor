// Race data's plain rules: the quali tag, which sessions go in the strip, and how a
// race result reads ("+2 from P4").

// one time per driver, from the furthest part of quali they got to, plus where they
// went out. The server sends null for the parts they didn't reach
export function qualiTag(row) {
  if (row.Q3) return { time: row.Q3, tag: "Q3" };
  if (row.Q2) return { time: row.Q2, tag: "out in Q2" };
  return { time: row.Q1 || "-", tag: "out in Q1" };
}

// the practice sessions that ran (FP1 only on sprint weekends), then Quali and Race.
// Until the practice answer says which ran, assume a normal weekend
export function sessionOptions(availablePractice) {
  return [...(availablePractice || ["FP1", "FP2", "FP3"]), "Quali", "Race"];
}

export function raceChange(row) {
  const from = row.GridPosition != null ? `from P${row.GridPosition}` : "";
  const ch = row.PositionChange;
  if (row.Status === "DNF" || ch == null) return { text: "", tone: "none", from };
  if (ch > 0) return { text: `+${ch}`, tone: "up", from };
  if (ch < 0) return { text: `${ch}`, tone: "down", from };
  return { text: "same", tone: "same", from };
}
