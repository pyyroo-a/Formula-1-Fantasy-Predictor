import { useState, useEffect } from "react";
import { API } from "../api";
import { DRIVER_NAMES, BADGE_COLOR, teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

export default function WeekendTeamWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTeam, setActiveTeam] = useState(0);

  useEffect(() => {
    fetch(`${API}/weekend-team`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  // Prefer the multi-team array; fall back to a single team for safety.
  const teams = data?.teams?.length ? data.teams : (data?.team ? [data.team] : []);

  if (loading || !data || !data.active || teams.length === 0) return null;

  const { race_name, session_used } = data;
  const team = teams[Math.min(activeTeam, teams.length - 1)];

  const captainAbbr = team.boost_pick?.Abbreviation ?? null;

  return (
    <div className="mb-4">
      {/* Section header */}
      <div className="flex justify-between items-end mb-3">
        <div>
          <p className="text-xs text-red-500 uppercase tracking-widest font-semibold mb-0.5">Race Weekend</p>
          <p className="text-white font-bold text-lg">{race_name} Lineup</p>
        </div>
        <div className="text-right">
          {data.locked && (
            <span className="inline-flex items-center gap-1 bg-green-500/10 text-green-400 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-green-500/20 mb-1">
              LOCKED
            </span>
          )}
          <p className="text-xs text-gray-500">Based on {session_used} · Score <span className="text-white font-medium">{team.total_score?.toFixed(2)}</span></p>
          <p className="text-xs text-gray-600 mt-0.5">${team.total_cost}M used · <span className="text-green-400">${team.budget_remaining}M left</span></p>
        </div>
      </div>

      {/* Team switcher — F1 Fantasy allows up to 3 entries */}
      {teams.length > 1 && (
        <div className="flex rounded-lg overflow-hidden border border-gray-700 mb-3">
          {teams.map((t, i) => (
            <button
              key={i}
              onClick={() => setActiveTeam(i)}
              className={`flex-1 py-2 text-xs font-medium transition ${
                activeTeam === i ? "bg-red-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              Team {i + 1}
              <span className={`block text-[10px] mt-0.5 ${activeTeam === i ? "text-red-200" : "text-gray-600"}`}>
                {t.total_score?.toFixed(1)} pts · ${t.total_cost}M
              </span>
            </button>
          ))}
        </div>
      )}

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
      <div className="grid grid-cols-2 gap-2 mb-2">
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

      {/* 2x boost recommendation */}
      {team.boost_pick && (
        <div className="flex items-start gap-3 rounded-lg bg-yellow-400/5 border border-yellow-400/20 px-3 py-2 mt-1">
          <span className="bg-yellow-400 text-black text-[9px] font-black px-1.5 py-0.5 rounded-full mt-0.5 flex-shrink-0">2×</span>
          <div className="min-w-0">
            <span className="text-yellow-400 text-xs font-semibold">{team.boost_pick.Abbreviation}</span>
            <span className="text-gray-500 text-xs"> · {team.boost_pick.reason}</span>
          </div>
        </div>
      )}
    </div>
  );
}
