import { teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

function PositionChange({ change, status }) {
  if (status === "DNF") return <span className="text-gray-500 text-sm font-medium">DNF</span>;
  if (change === null || change === undefined) return null;
  if (change > 0) return <span className="text-green-400 font-bold text-sm">+{change} ↑</span>;
  if (change < 0) return <span className="text-red-400 font-bold text-sm">{change} ↓</span>;
  return <span className="text-gray-500 text-sm">—</span>;
}

export default function RaceResultsTable({ results }) {
  return (
    <div className="space-y-2">
      {results.map((row) => {
        const accent = teamAccent(row.TeamName);
        const isDNF = row.Status === "DNF";
        return (
          <div
            key={row.Abbreviation}
            className={`flex items-center gap-4 rounded-xl px-4 py-4 border-l-[6px] ${isDNF ? "bg-gray-800/40 opacity-55" : "bg-gray-800"}`}
            style={{ borderColor: accent }}
          >
            <div className="w-14 text-center flex-shrink-0">
              {isDNF
                ? <span className="text-red-500 text-sm font-bold">DNF</span>
                : <span className="text-white text-2xl font-black leading-none">P{row.Position}</span>}
            </div>
            <DriverAvatar abbreviation={row.Abbreviation} size="lg" />
            <div className="flex-1 min-w-0">
              <p className="font-bold text-lg leading-tight truncate">{row.FullName}</p>
              <p className="text-gray-400 text-sm mt-0.5 truncate">{row.TeamName}</p>
            </div>
            <div className="text-right flex-shrink-0">
              {!isDNF && row.GridPosition != null && (
                <p className="text-gray-400 text-sm font-mono mb-1">P{row.GridPosition} → P{row.Position}</p>
              )}
              <PositionChange change={row.PositionChange} status={row.Status} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
