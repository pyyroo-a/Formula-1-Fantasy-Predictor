import { useState, useEffect } from "react";
import { DRIVER_NAMES, BADGE_COLOR, teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

export default function WeekendTeamWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/weekend-team")
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading || !data || !data.active || !data.team) return null;

  const { race_name, session_used, team } = data;

  return (
    <div className="mb-6 bg-gray-900 rounded-xl border border-red-600/40 overflow-hidden">
      <div className="bg-red-600/10 px-4 py-3 flex justify-between items-center border-b border-red-600/30">
        <div>
          <p className="text-xs text-red-400 uppercase tracking-wider font-medium">Race Weekend</p>
          <p className="text-white font-bold">{race_name}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Based on {session_used}</p>
          <p className="text-xs text-gray-500">Score: <span className="text-white font-medium">{team.total_score?.toFixed(2)}</span></p>
        </div>
      </div>
      <div className="p-4 space-y-2">
        <div className="grid grid-cols-1 gap-2">
          {team.drivers.map((d) => {
            const accent = teamAccent(d.TeamName);
            return (
              <div key={d.Abbreviation} className="flex items-center gap-3 bg-gray-800 rounded-xl px-3 py-3 border-l-[6px]" style={{ borderColor: accent }}>
                <DriverAvatar abbreviation={d.Abbreviation} size="md" />
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-sm leading-tight truncate">{DRIVER_NAMES[d.Abbreviation] || d.Abbreviation}</p>
                  <p className="text-gray-500 text-xs mt-0.5">{d.TeamName}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-white text-xs px-2 py-0.5 rounded-full font-medium ${BADGE_COLOR[d.PickCategory]}`}>{d.PickCategory}</span>
                  <span className="text-gray-400 text-sm">${d.Price?.toFixed(1)}M</span>
                </div>
              </div>
            );
          })}
        </div>
        <div className="grid grid-cols-2 gap-1.5 mt-1">
          {team.constructors.map((c) => {
            const accent = teamAccent(c.name);
            return (
              <div key={c.name} className="flex justify-between items-center bg-gray-800 rounded-lg px-3 py-2 border-l-4" style={{ borderColor: accent }}>
                <span className="font-medium text-xs">{c.name}</span>
                <span className="text-gray-400 text-xs">${c.price?.toFixed(1)}M</span>
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-xs text-gray-500 pt-1">
          <span>Total: <span className="text-white">${team.total_cost}M</span></span>
          <span>Remaining: <span className="text-green-400">${team.budget_remaining}M</span></span>
        </div>
      </div>
    </div>
  );
}
