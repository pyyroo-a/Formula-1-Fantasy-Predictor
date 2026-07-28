import { teamAccent } from "../constants";

// Fastest-lap classification for a practice session. Gap-to-pole is shown
// against the session-topping time; P1 shows the reference lap instead.
export default function PracticeTable({ results }) {
  return (
    <div className="border border-white/[0.06]">
      <div className="flex items-center gap-3 px-3 py-1.5 text-[9.5px] text-pw-muted tracking-[0.06em] border-b border-white/[0.06]">
        <span className="w-9 flex-shrink-0">POS</span>
        <span className="flex-1">DRIVER</span>
        <div className="flex gap-3 flex-shrink-0 text-right">
          <span className="w-20">BEST LAP</span>
          <span className="w-14">GAP</span>
        </div>
      </div>
      {results.map((row, i) => {
        const accent = teamAccent(row.TeamName);
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
            <div className="flex gap-3 flex-shrink-0 text-right text-[11px]">
              <span className={`w-20 ${i === 0 ? "text-pw-risk font-bold" : "text-white"}`}>{row.LapTime}</span>
              <span className="w-14 text-pw-muted">{i === 0 ? "—" : `+${row.GapToPole.toFixed(3)}`}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
