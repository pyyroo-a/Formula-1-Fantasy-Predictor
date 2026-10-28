import { verdictLabel } from "../lib/format";

const STYLE = {
  PLAY:         "bg-[#163222] text-pw-safe",
  CONSIDER:     "bg-[#332D16] text-pw-caution",
  "POST-QUALI": "bg-[#1A2440] text-pw-info",
  HEDGE:        "bg-[#332D16] text-pw-caution",
  HOLD:         "bg-pw-edge text-pw-muted",
  SAVE:         "bg-pw-edge text-pw-muted",
};

// PLAY / CONSIDER / HOLD... as a small tag. POST-QUALI reads AFTER QUALI
export default function VerdictTag({ rec }) {
  if (!rec) return null;
  return (
    <span className={`text-[11px] font-extrabold px-1.5 py-0.5 rounded whitespace-nowrap ${STYLE[rec] || STYLE.HOLD}`}>
      {verdictLabel(rec)}
    </span>
  );
}
