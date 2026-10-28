// The Insights pages' plain rules. The words follow the numbers, so when PitWall
// starts beating the FP3 order the headline changes by itself, no hand edits.

// whole points stay whole (183), anything else gets one decimal (88.1), as sent
export const pointsText = v => (v == null ? "-" : Number.isInteger(v) ? String(v) : v.toFixed(1));

export function raceVerdict(cells) {
  const pw = cells?.Locked;
  const fp3 = cells?.["FP3 order"];
  if (pw == null || fp3 == null) return { text: "", won: null };
  if (pw === fp3) return { text: `${pointsText(pw)} tied with FP3's ${pointsText(fp3)}`, won: null };
  const won = pw > fp3;
  return { text: `${pointsText(pw)} ${won ? "beat" : "lost to"} FP3's ${pointsText(fp3)}`, won };
}

export function honestLine(summary) {
  const pw = summary?.Locked?.avg;
  const fp3 = summary?.["FP3 order"]?.avg;
  if (pw == null || fp3 == null) return "";
  if (fp3 > pw) return "Copying the FP3 order scored a bit more so far.";
  if (pw > fp3) return "PitWall scored more than copying the FP3 order so far.";
  return "PitWall and copying the FP3 order have scored the same so far.";
}

// where a dot sits on the line, 0 to 100 (percent)
export function dotX(value, max) {
  return Math.min(100, Math.max(0, (value / max) * 100));
}

// the line runs to the best possible score rounded up to the next 50
export function chartMax(rows) {
  const top = Math.max(0, ...(rows || []).map(r => r.cells?.["Hindsight best"] ?? 0));
  return Math.max(50, Math.ceil(top / 50) * 50);
}
