export default function SessionSchedule({ sessions }) {
  if (!sessions?.length) return null;
  const practiceSessions = sessions.filter(s => ["FP1", "FP2", "FP3"].includes(s.name));
  if (!practiceSessions.length) return null;

  return (
    <div className="bg-gray-800/60 rounded-xl px-4 py-4 border border-gray-700 mb-3">
      <p className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Practice Sessions</p>
      <div className="space-y-3">
        {practiceSessions.map((s) => {
          const dt = new Date(s.date);
          return (
            <div key={s.name} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`w-3 h-3 rounded-full flex-shrink-0 ${s.available ? "bg-green-400" : "bg-gray-600"}`} />
                <span className={`text-base font-bold ${s.available ? "text-white" : "text-gray-400"}`}>{s.name}</span>
              </div>
              <span className={`text-sm font-medium ${s.available ? "text-green-400" : "text-gray-400"}`}>
                {s.available
                  ? "Data available ✓"
                  : dt.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
