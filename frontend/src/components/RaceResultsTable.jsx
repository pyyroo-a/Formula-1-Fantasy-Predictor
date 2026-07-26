import { teamAccent } from "../constants";

function PositionChange({ change, status }) {
  if (status === "DNF") return null;
  if (change === null || change === undefined) return null;
  if (change > 0) return <span className="text-pw-safe font-semibold">+{change}</span>;
  if (change < 0) return <span className="text-pw-red font-semibold">{change}</span>;
  return <span className="text-pw-muted">—</span>;
}

export default function RaceResultsTable({ results }) {
  return (
    <div className="border border-white/[0.06]">
      {results.map((row, i) => {
        const accent = teamAccent(row.TeamName);
        const isDNF = row.Status === "DNF";
        const last = i === results.length - 1;
        return (
          <div
            key={row.Abbreviation}
            className={`flex items-center gap-3 px-3 py-2.5 ${last ? "" : "border-b border-white/[0.05]"} ${isDNF ? "opacity-50" : ""}`}
          >
            <div className={`w-9 flex-shrink-0 text-[11px] font-bold ${isDNF ? "text-pw-red" : "text-pw-muted"}`}>
              {isDNF ? "DNF" : `P${row.Position}`}
            </div>
            <div
              className="flex-1 min-w-0 text-[12.5px] text-white truncate border-l-2 pl-2.5"
              style={{ borderColor: accent }}
            >
              {row.FullName} <span className="text-pw-muted">— {row.TeamName}</span>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0 text-[11px] text-right">
              {!isDNF && row.GridPosition != null && (
                <span className="text-pw-muted hidden sm:inline">P{row.GridPosition} → P{row.Position}</span>
              )}
              <span className="w-10 text-right"><PositionChange change={row.PositionChange} status={row.Status} /></span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
