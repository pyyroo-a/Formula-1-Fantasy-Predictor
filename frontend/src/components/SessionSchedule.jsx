// When each practice session is, in your own time, and which ones are already in
export default function SessionSchedule({ sessions }) {
  if (!sessions?.length) return null;
  const practiceSessions = sessions.filter(s => ["FP1", "FP2", "FP3"].includes(s.name));
  if (!practiceSessions.length) return null;

  return (
    <div className="bg-pw-panel rounded-xl px-3.5 py-3 mb-3">
      <h3 className="cond font-bold text-[15px] mb-1.5">Practice sessions</h3>
      {practiceSessions.map((s) => {
        const dt = new Date(s.date);
        return (
          <div key={s.name} className="flex items-center justify-between py-1 text-[13px]">
            <span className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${s.available ? "bg-pw-safe" : "bg-pw-edge"}`} />
              <span className={`cond font-bold text-[15px] ${s.available ? "" : "text-pw-muted"}`}>{s.name}</span>
            </span>
            <span className={`num ${s.available ? "text-pw-safe" : "text-pw-muted"}`}>
              {s.available
                ? "In"
                : dt.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        );
      })}
    </div>
  );
}
