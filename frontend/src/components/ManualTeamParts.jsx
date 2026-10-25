import { CAT_BADGE, DRIVER_NAMES, teamAccent } from "../constants";

// The small cards the Manual Team builder is made of, moved out so the builder
// itself is just the logic and layout.

export function SelectedDriverSlot({ driver, isCaptain, onRemove }) {
  const accent = teamAccent(driver.TeamName);
  const badge = CAT_BADGE[driver.PickCategory] || "text-pw-muted bg-white/5";
  return (
    <div className={`flex items-center gap-3 px-3 py-2.5 bg-pw-panel2 border-l-2 ${isCaptain ? "ring-1 ring-pw-risk/40" : ""}`} style={{ borderColor: accent }}>
      <p className="flex-1 min-w-0 text-[12.5px] text-white truncate">
        {isCaptain && <span className="text-pw-risk font-bold mr-1">C</span>}
        {DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}
        <span className="text-pw-muted"> · {driver.TeamName}</span>
      </p>
      <span className={`text-[9.5px] px-1.5 py-0.5 rounded-sm flex-shrink-0 ${badge}`}>{(driver.PickCategory || "").toUpperCase()}</span>
      <span className="text-[12px] text-white w-14 text-right flex-shrink-0">${driver.Price?.toFixed(1)}M</span>
      <button onClick={onRemove} className="text-pw-muted hover:text-pw-red text-sm flex-shrink-0 transition">✕</button>
    </div>
  );
}

export function SelectedConstructorSlot({ constructor: c, onRemove }) {
  const accent = teamAccent(c.name);
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 bg-pw-panel2 border-l-2" style={{ borderColor: accent }}>
      <span className="flex-1 text-[12.5px] text-white truncate">{c.name} <span className="text-pw-muted">· Constructor</span></span>
      <span className="text-[12px] text-white flex-shrink-0">${c.price?.toFixed(1)}M</span>
      <button onClick={onRemove} className="text-pw-muted hover:text-pw-red text-sm flex-shrink-0 transition">✕</button>
    </div>
  );
}

export function PoolDriverCard({ driver, isSelected, canAdd, onToggle }) {
  const accent = teamAccent(driver.TeamName);
  const dimmed = !isSelected && !canAdd;
  const badge = CAT_BADGE[driver.PickCategory] || "text-pw-muted bg-white/5";
  return (
    <button
      onClick={onToggle}
      disabled={dimmed}
      className={`text-left w-full px-3 py-2.5 border-l-2 transition ${
        isSelected ? "bg-pw-panel ring-1 ring-white/20"
        : dimmed ? "bg-pw-panel2/50 opacity-40 cursor-not-allowed"
        : "bg-pw-panel2 hover:bg-pw-panel cursor-pointer"
      }`}
      style={{ borderColor: accent }}
    >
      <div className="flex items-center gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-[12.5px] text-white truncate">{DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation} <span className="text-pw-muted">· {driver.TeamName}</span></p>
          <p className="text-[10px] text-pw-muted mt-0.5">Grid P{Math.round(driver.GridPosition)} · Pred P{Math.round(driver.Predicted)} · {driver.FantasyValue?.toFixed(2)}</p>
        </div>
        <span className={`text-[9.5px] px-1.5 py-0.5 rounded-sm flex-shrink-0 ${badge}`}>{(driver.PickCategory || "").toUpperCase()}</span>
        <span className="text-[12px] text-white w-14 text-right flex-shrink-0">${driver.Price?.toFixed(1)}M</span>
      </div>
      {isSelected && <p className="text-[9.5px] text-pw-muted/60 mt-1 text-right">Click to remove</p>}
    </button>
  );
}

export function PoolConstructorCard({ constructor: c, isSelected, canAdd, onToggle }) {
  const accent = teamAccent(c.name);
  const dimmed = !isSelected && !canAdd;
  return (
    <button
      onClick={onToggle}
      disabled={dimmed}
      className={`text-left w-full px-3 py-2 border-l-2 transition flex justify-between items-center gap-2 ${
        isSelected ? "bg-pw-panel ring-1 ring-white/20"
        : dimmed ? "bg-pw-panel2/50 opacity-40 cursor-not-allowed"
        : "bg-pw-panel2 hover:bg-pw-panel cursor-pointer"
      }`}
      style={{ borderColor: accent }}
    >
      <div className="min-w-0">
        <p className="text-[12px] text-white truncate">{c.name}</p>
        <p className="text-[9.5px] text-pw-muted mt-0.5">{c.score?.toFixed(2)}</p>
      </div>
      <span className="text-[12px] text-white flex-shrink-0">${c.price?.toFixed(1)}M</span>
    </button>
  );
}
