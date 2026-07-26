import { DRIVER_NAMES, teamAccent } from "../constants";

const CAT_BADGE = {
  Safe:  "text-pw-safe bg-pw-safe/10",
  Value: "text-pw-rain bg-pw-rain/10",
  Risk:  "text-pw-risk bg-pw-risk/10",
  Avoid: "text-pw-red bg-pw-red/10",
};

// 3-cell hairline stat grid: BUDGET USED · REMAINING · PROJECTED PTS.
export function TeamStatGrid({ used, remaining, score }) {
  const cells = [
    { label: "BUDGET USED",   value: `$${used?.toFixed(1)}M`,      color: "text-white" },
    { label: "REMAINING",     value: `$${remaining?.toFixed(1)}M`, color: "text-pw-safe" },
    { label: "PROJECTED PTS", value: score?.toFixed(1),            color: "text-pw-red" },
  ];
  return (
    <div className="pw-hairgrid grid grid-cols-3 gap-px border border-white/[0.06] mb-4">
      {cells.map(c => (
        <div key={c.label} className="bg-pw-panel px-3 py-3 text-center">
          <p className="text-[9.5px] text-pw-muted tracking-[0.05em] mb-1">{c.label}</p>
          <p className={`text-lg font-extrabold ${c.color}`}>{c.value}</p>
        </div>
      ))}
    </div>
  );
}

// Kept for backward-compat; the stat grid is the primary summary now.
export function BudgetBar({ used, total = 100 }) {
  return <TeamStatGrid used={used} remaining={total - used} score={null} />;
}

export function BudgetDriverCard({ driver, isCaptain = false }) {
  const accent = teamAccent(driver.TeamName);
  const badge = CAT_BADGE[driver.PickCategory] || "text-pw-muted bg-white/5";
  return (
    <div
      className={`flex items-center gap-3 px-3 py-2.5 bg-pw-panel2 border-l-2 ${isCaptain ? "ring-1 ring-pw-risk/40" : ""}`}
      style={{ borderColor: accent }}
    >
      <div className="flex-1 min-w-0">
        <p className="text-[12.5px] text-white truncate">
          {isCaptain && <span className="text-pw-risk font-bold mr-1">C</span>}
          {DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}
          <span className="text-pw-muted"> — {driver.TeamName}</span>
        </p>
        <p className="text-[10px] text-pw-muted mt-0.5">
          Grid P{Math.round(driver.GridPosition)} · Pred P{Math.round(driver.Predicted)} · {driver.FantasyValue?.toFixed(2)}
        </p>
      </div>
      {driver.PickCategory && (
        <span className={`text-[9.5px] px-1.5 py-0.5 rounded-sm flex-shrink-0 ${badge}`}>{driver.PickCategory.toUpperCase()}</span>
      )}
      <span className="text-[12px] text-white w-16 text-right flex-shrink-0">${driver.Price?.toFixed(1)}M</span>
    </div>
  );
}

export function BoostPickCard({ pick }) {
  if (!pick) return null;
  const gain = pick.GridPosition - pick.Predicted;
  return (
    <div className="border-l-2 border-pw-risk bg-pw-panel2 p-3 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="bg-pw-risk text-black text-[9px] font-black px-1.5 py-0.5 rounded-sm tracking-wider">2× BOOST PICK</span>
        {pick.alternatives?.length > 0 && (
          <span className="text-pw-muted text-[10px]">Alt: {pick.alternatives.join(", ")}</span>
        )}
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[13px] text-white font-bold truncate">
          {DRIVER_NAMES[pick.Abbreviation] || pick.Abbreviation}
          <span className="text-pw-muted font-normal"> — {pick.TeamName}</span>
        </p>
        <span className="text-pw-risk font-bold text-[12px] flex-shrink-0">{pick.FantasyValue?.toFixed(2)}</span>
      </div>
      <p className="text-[10.5px] text-pw-muted mt-0.5">
        P{pick.GridPosition} → P{Math.round(pick.Predicted)}
        {gain > 0 && <span className="text-pw-safe"> · +{gain.toFixed(1)} pos</span>}
      </p>
      {pick.reason && <p className="text-[10.5px] text-pw-muted mt-2 border-t border-white/[0.06] pt-2 leading-relaxed">{pick.reason}</p>}
    </div>
  );
}

export function ConstructorCard({ constructor: c }) {
  const accent = teamAccent(c.name);
  return (
    <div className="flex items-center justify-between gap-2 px-3 py-2.5 bg-pw-panel2 border-l-2" style={{ borderColor: accent }}>
      <span className="text-[12.5px] text-white truncate">{c.name} <span className="text-pw-muted">— Constructor</span></span>
      <div className="text-right flex-shrink-0">
        <span className="text-[12px] text-white">${c.price?.toFixed(1)}M</span>
        <span className="text-[10px] text-pw-muted ml-2">{c.score?.toFixed(2)}</span>
      </div>
    </div>
  );
}
