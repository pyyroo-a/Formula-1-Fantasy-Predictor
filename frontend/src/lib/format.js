// Number and label formatting the whole site shares, so a price or a points total
// looks the same on every page (one decimal, always: 38.0 not 38).
import { DRIVER_NAMES } from "../constants.js";

const missing = (n) => n === null || n === undefined || Number.isNaN(n);

export function fmt1(n) {
  return missing(n) ? "-" : Number(n).toFixed(1);
}

export function money(n) {
  return missing(n) ? "-" : `$${fmt1(n)}M`;
}

export function pts(n) {
  return missing(n) ? "-" : `${fmt1(n)} pts`;
}

// "ANT" -> "Antonelli". Unknown codes just stay as the code
export function surname(code) {
  const full = DRIVER_NAMES[code];
  return full ? full.split(" ").at(-1) : code;
}

// the chip verdicts as the server sends them, in plain words where they weren't
export function verdictLabel(rec) {
  return rec === "POST-QUALI" ? "AFTER QUALI" : rec;
}
