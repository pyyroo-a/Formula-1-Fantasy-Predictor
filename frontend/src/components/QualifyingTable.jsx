import { teamAccent } from "../constants";

export default function QualifyingTable({ results }) {
  return (
    <div className="border border-white/[0.06]">
      <div className="flex items-center gap-3 px-3 py-1.5 text-[9.5px] text-pw-muted tracking-[0.06em] border-b border-white/[0.06]">
        <span className="w-9 flex-shrink-0">POS</span>
        <span className="flex-1">DRIVER</span>
        <div className="flex gap-2 flex-shrink-0 text-right">
          <span className="w-16">Q1</span>
          <span className="w-16">Q2</span>
          <span className="w-16">Q3</span>
        </div>
      </div>
      {results.map((row, i) => {
        const accent = teamAccent(row.TeamName);
        const inQ3 = row.Q3 !== null;
        const inQ2 = row.Q2 !== null;
        const last = i === results.length - 1;
        return (
          <div
            key={row.Abbreviation}
            className={`flex items-center gap-3 px-3 py-2.5 ${last ? "" : "border-b border-white/[0.05]"}`}
          >
            <div className="w-9 flex-shrink-0 text-[11px] font-bold text-pw-muted">P{row.Position}</div>
            <div
              className="flex-1 min-w-0 text-[12.5px] text-white truncate border-l-2 pl-2.5"
              style={{ borderColor: accent }}
            >
              {row.FullName} <span className="text-pw-muted">— {row.TeamName}</span>
            </div>
            <div className="flex gap-2 flex-shrink-0 text-right text-[11px]">
              <span className={`w-16 ${inQ3 ? "text-pw-risk" : inQ2 ? "text-white" : "text-pw-muted"}`}>{row.Q1 ?? "—"}</span>
              <span className={`w-16 ${inQ3 ? "text-pw-risk" : inQ2 ? "text-white" : "text-pw-muted/60"}`}>{row.Q2 ?? "—"}</span>
              <span className={`w-16 ${inQ3 ? "text-pw-risk font-bold" : "text-pw-muted/60"}`}>{row.Q3 ?? "—"}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
