import { useState, useEffect } from "react";
import { API } from "../api";
import { DRIVER_NAMES, BADGE_COLOR, teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

export default function WeekendTeamWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/weekend-team`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading || !data || !data.active || !data.team) return null;

  const { race_name, session_used, team } = data;

  const captainAbbr = team.drivers.length > 0
    ? [...team.drivers].sort((a, b) => (b.FantasyValue ?? 0) - (a.FantasyValue ?? 0))[0].Abbreviation
    : null;

  return (
    <div className="mb-4">
      {/* Section header */}
      <div className="flex justify-between items-end mb-3">
        <div>
          <p className="text-xs text-red-500 uppercase tracking-widest font-semibold mb-0.5">Race Weekend</p>
          <p className="text-white font-bold text-lg">{race_name} Lineup</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Based on {session_used} · Score <span className="text-white font-medium">{team.total_score?.toFixed(2)}</span></p>
          <p className="text-xs text-gray-600 mt-0.5">${team.total_cost}M used · <span className="text-green-400">${team.budget_remaining}M left</span></p>
        </div>
      </div>

      {/* Driver grid — 2 columns */}
      <div className="grid grid-cols-2 gap-2 mb-2">
        {team.drivers.map(d => {
          const accent = teamAccent(d.TeamName);
          const isCaptain = d.Abbreviation === captainAbbr;
          return (
            <div
              key={d.Abbreviation}
              className={`flex items-center gap-3 bg-gray-800 rounded-xl px-3 py-3 border-l-[5px] ${isCaptain ? "ring-1 ring-yellow-400/40" : ""}`}
              style={{ borderColor: accent }}
            >
              <div className="relative flex-shrink-0">
                <DriverAvatar abbreviation={d.Abbreviation} size="md" />
                {isCaptain && (
                  <span className="absolute -top-1 -right-1 bg-yellow-400 text-black text-[9px] font-black w-4 h-4 rounded-full flex items-center justify-center">C</span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-bold text-sm leading-tight truncate">{DRIVER_NAMES[d.Abbreviation] || d.Abbreviation}</p>
                <p className="text-gray-500 text-xs mt-0.5 truncate">{d.TeamName}</p>
              </div>
              <div className="flex flex-col items-end gap-1 flex-shrink-0">
                <span className={`text-white text-[10px] px-2 py-0.5 rounded-full font-medium ${BADGE_COLOR[d.PickCategory]}`}>{d.PickCategory}</span>
                <span className="text-gray-400 text-xs">${d.Price?.toFixed(1)}M</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Constructor row */}
      <div className="grid grid-cols-2 gap-2">
        {team.constructors.map(c => {
          const accent = teamAccent(c.name);
          return (
            <div key={c.name} className="flex justify-between items-center bg-gray-800 rounded-lg px-3 py-2 border-l-4" style={{ borderColor: accent }}>
              <span className="font-medium text-sm text-white">{c.name}</span>
              <span className="text-gray-400 text-xs">${c.price?.toFixed(1)}M</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
