// The Predicted finishes page's rules: one row per driver, and once the real results
// are in (results_available, from the Monday job) how close we were.
//   exact = spot on, close = within 1 place, off = further, dnf = didn't finish
import { surname } from "./format.js";

export function finishRows(predictions, resultsAvailable) {
  return (predictions || []).map(p => {
    const finished = resultsAvailable && p.actual_pos != null ? p.actual_pos : null;
    const dnf = resultsAvailable && p.actual_pos == null && !!p.actual_status;
    const offBy = finished != null ? Math.abs(p.model_pos - finished) : null;
    const status = !resultsAvailable ? null
      : dnf ? "dnf"
      : offBy == null ? null
      : offBy === 0 ? "exact" : offBy === 1 ? "close" : "off";
    return {
      spot: p.model_pos, code: p.abbreviation, name: surname(p.abbreviation), team: p.team,
      practice: p.baseline_pos, delta: p.delta, finished, offBy, status,
    };
  });
}

// where a driver lands on the right side of the lines view: their finish, or a DNF
// spot just under last place so it never sits on top of a real finisher
export function rightSpot(row, total) {
  return row.finished ?? total + 1;
}
