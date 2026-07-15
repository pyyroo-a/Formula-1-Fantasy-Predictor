import { teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

export default function QualifyingTable({ results }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4 px-4 py-1 text-xs text-gray-500 uppercase tracking-wider">
        <span className="w-14 text-center flex-shrink-0">Pos</span>
        <span className="w-14 flex-shrink-0" />
        <span className="flex-1">Driver</span>
        <div className="flex gap-3 flex-shrink-0 text-right">
          <span className="w-24">Q1</span>
          <span className="w-24">Q2</span>
          <span className="w-24">Q3</span>
        </div>
      </div>
      {results.map((row) => {
        const accent = teamAccent(row.TeamName);
        const inQ3 = row.Q3 !== null;
        const inQ2 = row.Q2 !== null;
        return (
          <div
            key={row.Abbreviation}
            className="flex items-center gap-4 rounded-xl px-4 py-4 bg-gray-800 border-l-[6px]"
            style={{ borderColor: accent }}
          >
            <div className="w-14 text-center flex-shrink-0">
              <span className="text-white text-2xl font-black leading-none">P{row.Position}</span>
            </div>
            <DriverAvatar abbreviation={row.Abbreviation} size="lg" />
            <div className="flex-1 min-w-0">
              <p className="font-bold text-lg leading-tight truncate">{row.FullName}</p>
              <p className="text-gray-400 text-sm mt-0.5 truncate">{row.TeamName}</p>
            </div>
            <div className="flex gap-3 flex-shrink-0 text-right text-sm font-mono">
              <span className={`w-24 ${inQ3 ? "text-yellow-400" : inQ2 ? "text-white" : "text-gray-400"}`}>{row.Q1 ?? "—"}</span>
              <span className={`w-24 ${inQ3 ? "text-yellow-400" : inQ2 ? "text-white" : "text-gray-600"}`}>{row.Q2 ?? "—"}</span>
              <span className={`w-24 ${inQ3 ? "text-yellow-300 font-bold" : "text-gray-600"}`}>{row.Q3 ?? "—"}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
