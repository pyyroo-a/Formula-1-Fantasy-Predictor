// Retirement risk, shown as a coloured percentage. This is advisory only: it
// deliberately does NOT feed the optimiser's score, because charging it as a
// points deduction measured worse in the backtest. It is here so a double-DNF
// constructor like Aston Martin at Monza is at least visible before you commit.
export default function RiskTag({ p, label = "DNF" }) {
  if (p == null || Number.isNaN(p)) return null;
  const pct = Math.round(p * 100);
  // Bands are relative to the ~15% field-average retirement rate.
  const tone = pct >= 30 ? "text-pw-caution" : pct >= 18 ? "text-amber-400" : "text-pw-muted";
  return (
    <span className={`text-[11px] ${tone}`} title={`Estimated chance of ${label === "DNF" ? "retiring" : label}`}>
      {label} {pct}%
    </span>
  );
}
