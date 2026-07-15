import { DRIVER_NAMES, BADGE_COLOR, teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

export function BudgetBar({ used, total = 100 }) {
  const pct = Math.min((used / total) * 100, 100);
  const remaining = total - used;
  const barColor = pct > 90 ? "bg-red-500" : pct > 75 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div className="mb-6">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">Budget used: <span className="text-white font-medium">${used.toFixed(1)}M</span></span>
        <span className="text-gray-400">Remaining: <span className="text-green-400 font-medium">${remaining.toFixed(1)}M</span></span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function BudgetDriverCard({ driver }) {
  const accent = teamAccent(driver.TeamName);
  return (
    <div className="bg-gray-800 rounded-xl px-4 py-4 shadow-lg border-l-[6px]" style={{ borderColor: accent }}>
      <div className="flex items-center gap-4 mb-3">
        <DriverAvatar abbreviation={driver.Abbreviation} size="lg" />
        <div className="flex-1 min-w-0">
          <p className="text-lg font-bold leading-tight truncate">{DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}</p>
          <p className="text-gray-400 text-sm mt-0.5">{driver.TeamName}</p>
        </div>
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <p className="text-white font-bold text-base">${driver.Price?.toFixed(1)}M</p>
          {driver.PickCategory && (
            <span className={`text-white text-xs px-2.5 py-1 rounded-full font-medium ${BADGE_COLOR[driver.PickCategory]}`}>
              {driver.PickCategory}
            </span>
          )}
        </div>
      </div>
      <div className="flex justify-between text-sm text-gray-500 border-t border-gray-700 pt-2">
        <span>Grid: <span className="text-gray-300">P{Math.round(driver.GridPosition)}</span></span>
        <span>Predicted: <span className="text-gray-300">P{Math.round(driver.Predicted)}</span></span>
        <span>Score: <span className="text-gray-300">{driver.FantasyValue?.toFixed(2)}</span></span>
      </div>
    </div>
  );
}

export function ConstructorCard({ constructor: c }) {
  const accent = teamAccent(c.name);
  return (
    <div className="bg-gray-800 rounded-xl px-4 py-4 shadow-lg border-l-[6px] flex justify-between items-center" style={{ borderColor: accent }}>
      <div>
        <p className="text-lg font-bold">{c.name}</p>
        <p className="text-gray-500 text-sm mt-0.5">Constructor</p>
      </div>
      <div className="text-right">
        <p className="text-white font-bold text-base">${c.price?.toFixed(1)}M</p>
        <p className="text-gray-500 text-sm mt-0.5">Score: {c.score?.toFixed(2)}</p>
      </div>
    </div>
  );
}
