import { useState, useEffect } from "react";
import { API } from "../api";
import { DRIVER_NAMES, BADGE_COLOR, BUDGET, teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";
import SessionSchedule from "./SessionSchedule";

function SelectedDriverSlot({ driver, isCaptain, onRemove }) {
  const accent = teamAccent(driver.TeamName);
  return (
    <div className={`bg-gray-800 rounded-xl px-4 py-3 border-l-[6px] flex items-center gap-3 ${isCaptain ? "ring-2 ring-yellow-400/50" : ""}`} style={{ borderColor: accent }}>
      <div className="relative flex-shrink-0">
        <DriverAvatar abbreviation={driver.Abbreviation} size="lg" />
        {isCaptain && (
          <span className="absolute -top-1 -right-1 bg-yellow-400 text-black text-[9px] font-black w-4 h-4 rounded-full flex items-center justify-center leading-none">C</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-bold text-base leading-tight truncate">{DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}</p>
          {isCaptain && <span className="text-yellow-400 text-xs font-semibold bg-yellow-400/10 px-2 py-0.5 rounded-full flex-shrink-0">Captain</span>}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-gray-400 text-sm">${driver.Price?.toFixed(1)}M</span>
          <span className={`text-white text-xs px-2 py-0.5 rounded-full font-medium ${BADGE_COLOR[driver.PickCategory]}`}>
            {driver.PickCategory}
          </span>
        </div>
      </div>
      <button onClick={onRemove} className="text-gray-500 hover:text-red-400 text-sm ml-2 transition flex-shrink-0">✕</button>
    </div>
  );
}

function SelectedConstructorSlot({ constructor: c, onRemove }) {
  const accent = teamAccent(c.name);
  return (
    <div className="bg-gray-800 rounded-xl px-4 py-3 border-l-[6px] flex justify-between items-center" style={{ borderColor: accent }}>
      <div>
        <p className="font-bold text-base">{c.name}</p>
        <p className="text-gray-400 text-sm mt-0.5">${c.price?.toFixed(1)}M</p>
      </div>
      <button onClick={onRemove} className="text-gray-500 hover:text-red-400 text-sm ml-2 transition">✕</button>
    </div>
  );
}

function PoolDriverCard({ driver, isSelected, canAdd, onToggle }) {
  const accent = teamAccent(driver.TeamName);
  const dimmed = !isSelected && !canAdd;
  return (
    <button
      onClick={onToggle}
      disabled={dimmed}
      className={`text-left w-full rounded-xl px-4 py-4 border-l-[6px] transition ${
        isSelected ? "bg-gray-700 ring-2 ring-white/20"
        : dimmed ? "bg-gray-800/50 opacity-40 cursor-not-allowed"
        : "bg-gray-800 hover:bg-gray-750 cursor-pointer"
      }`}
      style={{ borderColor: accent }}
    >
      <div className="flex items-center gap-3 mb-3">
        <DriverAvatar abbreviation={driver.Abbreviation} size="lg" />
        <div className="flex-1 min-w-0">
          <p className="font-bold text-base leading-tight truncate">{DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}</p>
          <p className="text-gray-400 text-sm mt-0.5">{driver.TeamName}</p>
        </div>
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <p className="text-white font-bold text-base">${driver.Price?.toFixed(1)}M</p>
          <span className={`text-white text-xs px-2.5 py-1 rounded-full font-medium ${BADGE_COLOR[driver.PickCategory]}`}>
            {driver.PickCategory}
          </span>
        </div>
      </div>
      <div className="flex justify-between text-sm text-gray-500 border-t border-gray-700 pt-2">
        <span>Grid: <span className="text-gray-300">P{Math.round(driver.GridPosition)}</span></span>
        <span>Predicted: <span className="text-gray-300">P{Math.round(driver.Predicted)}</span></span>
        <span>Score: <span className="text-gray-300">{driver.FantasyValue?.toFixed(2)}</span></span>
      </div>
      {isSelected && <p className="text-xs text-white/40 mt-2 text-right">Click to remove</p>}
    </button>
  );
}

function PoolConstructorCard({ constructor: c, isSelected, canAdd, onToggle }) {
  const accent = teamAccent(c.name);
  const dimmed = !isSelected && !canAdd;
  return (
    <button
      onClick={onToggle}
      disabled={dimmed}
      className={`text-left w-full rounded-xl px-3 py-2 border-l-[6px] transition flex justify-between items-center ${
        isSelected ? "bg-gray-700 ring-2 ring-white/20"
        : dimmed ? "bg-gray-800/50 opacity-40 cursor-not-allowed"
        : "bg-gray-800 hover:bg-gray-750 cursor-pointer"
      }`}
      style={{ borderColor: accent }}
    >
      <div>
        <p className="font-bold text-sm">{c.name}</p>
        <p className="text-gray-500 text-xs mt-0.5">Score: {c.score?.toFixed(2)}</p>
      </div>
      <div className="text-right">
        <p className="text-white font-bold text-base">${c.price?.toFixed(1)}M</p>
        {isSelected && <p className="text-xs text-white/40 mt-1">Click to remove</p>}
      </div>
    </button>
  );
}

export default function ManualTeamBuilder({ upcomingRaces }) {
  const [selectedRace, setSelectedRace] = useState("");
  const [sessions, setSessions] = useState(null);
  const [pool, setPool] = useState(null);
  const [optimalTeam, setOptimalTeam] = useState(null);
  const [sessionUsed, setSessionUsed] = useState(null);
  const [selectedDrivers, setSelectedDrivers] = useState([]);
  const [selectedConstructors, setSelectedConstructors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const selectedIsSprint = upcomingRaces.find(r => r.race_name === selectedRace)?.is_sprint ?? false;
  const anySessionAvailable = sessions?.some(s => ["FP1", "FP2", "FP3"].includes(s.name) && s.available);

  const resetPool = () => {
    setPool(null); setOptimalTeam(null); setSessionUsed(null);
    setSelectedDrivers([]); setSelectedConstructors([]); setError(null);
  };

  const fetchSessions = async (raceName) => {
    try {
      const res = await fetch(`${API}/race-sessions`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: raceName }),
      });
      const data = await res.json();
      if (!data.detail) setSessions(data.sessions);
    } catch {}
  };

  useEffect(() => {
    if (!selectedRace || pool) return;
    const id = setInterval(() => fetchSessions(selectedRace), 60000);
    return () => clearInterval(id);
  }, [selectedRace, pool]);

  const loadPool = async () => {
    if (!selectedRace) return;
    resetPool();
    setLoading(true);
    try {
      const res = await fetch(`${API}/upcoming-race-pool`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year: 2026, race_name: selectedRace, session: selectedIsSprint ? "FP1" : "FP3" }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setPool(data.pool);
      setSessionUsed(data.session_used);
      if (data.optimal) setOptimalTeam(data.optimal);
    } catch (e) {
      setError(e.message || "Failed to load race data.");
    }
    setLoading(false);
  };

  const toggleDriver = (driver) => {
    const isSelected = selectedDrivers.some(d => d.Abbreviation === driver.Abbreviation);
    if (isSelected) setSelectedDrivers(prev => prev.filter(d => d.Abbreviation !== driver.Abbreviation));
    else if (selectedDrivers.length < 5) setSelectedDrivers(prev => [...prev, driver]);
  };

  const toggleConstructor = (constructor) => {
    const isSelected = selectedConstructors.some(c => c.name === constructor.name);
    if (isSelected) setSelectedConstructors(prev => prev.filter(c => c.name !== constructor.name));
    else if (selectedConstructors.length < 2) setSelectedConstructors(prev => [...prev, constructor]);
  };

  const totalCost = selectedDrivers.reduce((s, d) => s + d.Price, 0)
    + selectedConstructors.reduce((s, c) => s + c.price, 0);
  const remaining = BUDGET - totalCost;
  const overBudget = totalCost > BUDGET;
  const teamComplete = selectedDrivers.length === 5 && selectedConstructors.length === 2;
  const myScore = selectedDrivers.reduce((s, d) => s + d.FantasyValue, 0)
    + selectedConstructors.reduce((s, c) => s + c.score, 0);
  const scoreVsOptimal = optimalTeam ? Math.round((myScore / optimalTeam.total_score) * 100) : null;
  const qualityColor = !teamComplete ? "text-gray-400"
    : scoreVsOptimal >= 90 ? "text-green-400"
    : scoreVsOptimal >= 70 ? "text-yellow-400"
    : "text-orange-400";
  const qualityLabel = !teamComplete ? "—"
    : scoreVsOptimal >= 90 ? "Excellent"
    : scoreVsOptimal >= 70 ? "Good"
    : scoreVsOptimal >= 50 ? "Average" : "Weak";
  const budgetPct = Math.min((totalCost / BUDGET) * 100, 100);
  const barColor = overBudget ? "bg-red-500" : budgetPct > 90 ? "bg-yellow-500" : "bg-green-500";
  const driverCategoryCounts = selectedDrivers.reduce((acc, d) => {
    acc[d.PickCategory] = (acc[d.PickCategory] || 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <p className="text-gray-400 text-sm text-center mb-4">Pick 5 drivers + 2 constructors for an upcoming race based on practice data.</p>

      <select
        value={selectedRace}
        onChange={(e) => {
          const race = e.target.value;
          setSelectedRace(race);
          resetPool();
          if (race) fetchSessions(race);
          else setSessions(null);
        }}
        className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-3"
      >
        <option value="">Select an upcoming race</option>
        {upcomingRaces.map(r => (
          <option key={r.race_name} value={r.race_name}>{r.race_name}{r.is_sprint ? " 🏁 Sprint" : ""}</option>
        ))}
      </select>

      {selectedRace && selectedIsSprint && (
        <p className="text-yellow-400 text-sm mb-3 text-center">Sprint weekend — will use FP1 data</p>
      )}
      {selectedRace && sessions && <SessionSchedule sessions={sessions} />}

      {selectedRace && !pool && !loading && (
        <button
          onClick={loadPool}
          disabled={sessions && !anySessionAvailable}
          className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed transition font-medium mb-4"
        >
          {sessions && !anySessionAvailable ? "No practice data yet — check back after FP1" : "Load Driver Pool"}
        </button>
      )}

      {error && <p className="text-red-400 text-sm text-center mb-4">{error}</p>}
      {loading && (
        <div className="text-center mb-4">
          <p className="text-gray-400 text-sm">Fetching practice data and running predictions...</p>
          <p className="text-gray-600 text-xs mt-1">This can take up to 30 seconds</p>
        </div>
      )}

      {pool && sessionUsed && (
        <div className="flex items-center gap-2 mb-4 bg-gray-800/60 rounded-lg px-3 py-2 border border-gray-700">
          <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
          <p className="text-sm text-gray-300">Predictions based on <span className="text-white font-semibold">{sessionUsed}</span> data</p>
        </div>
      )}

      {pool && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400">Spent: <span className={`font-semibold ${overBudget ? "text-red-400" : "text-white"}`}>${totalCost.toFixed(1)}M</span></span>
              <span className="text-gray-400">Remaining: <span className={`font-semibold ${overBudget ? "text-red-400" : "text-green-400"}`}>
                {overBudget ? `-$${(totalCost - BUDGET).toFixed(1)}M` : `$${remaining.toFixed(1)}M`}
              </span></span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${budgetPct}%` }} />
            </div>
            {overBudget && <p className="text-red-400 text-xs mt-2 text-center">Over budget — remove a pick to fix this</p>}
          </div>

          {teamComplete && (
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Team Summary</h3>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-xs text-gray-500 mb-1">My Score</p>
                  <p className="text-white font-bold text-lg">{myScore.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">vs Optimal</p>
                  <p className={`font-bold text-lg ${qualityColor}`}>{scoreVsOptimal}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Rating</p>
                  <p className={`font-bold text-lg ${qualityColor}`}>{qualityLabel}</p>
                </div>
              </div>
              {optimalTeam && (
                <p className="text-xs text-gray-500 text-center mt-3">
                  Optimal score: {optimalTeam.total_score?.toFixed(2)} (cost: ${optimalTeam.total_cost}M)
                </p>
              )}
              <div className="flex justify-center gap-3 mt-3 flex-wrap">
                {Object.entries(driverCategoryCounts).map(([cat, count]) => (
                  <span key={cat} className={`text-white text-xs px-2 py-0.5 rounded-full ${BADGE_COLOR[cat]}`}>{count}× {cat}</span>
                ))}
              </div>
            </div>
          )}

          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Your Drivers ({selectedDrivers.length}/5)</h3>
            <div className="grid grid-cols-1 gap-2 mb-4">
              {selectedDrivers.length === 0
                ? <p className="text-gray-600 text-sm text-center py-4 border border-dashed border-gray-700 rounded-lg">Click drivers below to add them</p>
                : (() => {
                    const withScore = selectedDrivers.filter(d => d.FantasyValue != null && !isNaN(d.FantasyValue));
                    const captainAbbr = withScore.length > 0
                      ? withScore.reduce((best, d) => d.FantasyValue > best.FantasyValue ? d : best).Abbreviation
                      : selectedDrivers[0]?.Abbreviation;
                    return selectedDrivers.map(d => (
                      <SelectedDriverSlot
                        key={d.Abbreviation}
                        driver={d}
                        isCaptain={d.Abbreviation === captainAbbr}
                        onRemove={() => toggleDriver(d)}
                      />
                    ));
                  })()
              }
            </div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Your Constructors ({selectedConstructors.length}/2)</h3>
            <div className="grid grid-cols-1 gap-2 mb-6">
              {selectedConstructors.length === 0
                ? <p className="text-gray-600 text-sm text-center py-4 border border-dashed border-gray-700 rounded-lg">Click constructors below to add them</p>
                : selectedConstructors.map(c => <SelectedConstructorSlot key={c.name} constructor={c} onRemove={() => toggleConstructor(c)} />)
              }
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Available Drivers</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {pool.drivers.map(driver => (
                <PoolDriverCard
                  key={driver.Abbreviation}
                  driver={driver}
                  isSelected={selectedDrivers.some(d => d.Abbreviation === driver.Abbreviation)}
                  canAdd={!selectedDrivers.some(d => d.Abbreviation === driver.Abbreviation) && selectedDrivers.length < 5}
                  onToggle={() => toggleDriver(driver)}
                />
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Available Constructors</h3>
            <div className="grid grid-cols-3 gap-3">
              {pool.constructors.map(c => (
                <PoolConstructorCard
                  key={c.name}
                  constructor={c}
                  isSelected={selectedConstructors.some(sc => sc.name === c.name)}
                  canAdd={!selectedConstructors.some(sc => sc.name === c.name) && selectedConstructors.length < 2}
                  onToggle={() => toggleConstructor(c)}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
