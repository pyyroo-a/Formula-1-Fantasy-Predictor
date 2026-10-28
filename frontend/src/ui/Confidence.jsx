// Confidence = how sure we are about a driver's predicted spot (project 4). It's about
// the spot, not whether he's a good pick, so the key says that once instead of every
// pill shouting CONFIDENCE.
const STYLE = {
  high:   { pill: "bg-[#163222] text-pw-safe", dot: "bg-pw-safe" },
  medium: { pill: "bg-[#332D16] text-pw-caution", dot: "bg-pw-caution" },
  low:    { pill: "bg-[#3A1D22] text-pw-low", dot: "bg-pw-low" },
};

// nothing when the server sent no level (previews, old snapshots, sprint weekends)
export function ConfidencePill({ level }) {
  const s = STYLE[level];
  if (!s) return null;
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-semibold pl-1.5 pr-2 py-px rounded-full whitespace-nowrap ${s.pill}`}>
      <span className={`w-2 h-2 rounded-full ${s.dot}`} />{level}
    </span>
  );
}

function Dot({ level }) {
  return <span className="inline-flex items-center gap-1"><span className={`w-2 h-2 rounded-full ${STYLE[level].dot}`} />{level}</span>;
}

export function ConfidenceKey() {
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-pw-muted my-2">
      <span className="hidden sm:inline">How sure we are about the predicted spot:</span>
      <Dot level="high" /><Dot level="medium" /><Dot level="low" />
      <span className="hidden sm:inline">(about the spot, not whether he's a good pick)</span>
      <span className="sm:hidden">= how sure we are about the spot</span>
    </p>
  );
}

// the plain reason under a name, when the server sent one
export function ConfidenceReason({ text }) {
  if (!text) return null;
  return <p className="text-xs text-pw-muted mt-0.5 leading-relaxed whitespace-normal">{text}</p>;
}
