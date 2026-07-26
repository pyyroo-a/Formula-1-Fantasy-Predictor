import { useState, useEffect } from "react";
import { API } from "../api";
import { DRIVER_NAMES, BUDGET, teamAccent } from "../constants";
import SessionSchedule from "./SessionSchedule";

const CAT_BADGE = {
  Safe:  "text-pw-safe bg-pw-safe/10",
  Value: "text-pw-rain bg-pw-rain/10",
  Risk:  "text-pw-risk bg-pw-risk/10",
  Avoid: "text-pw-red bg-pw-red/10",
};

const SELECT_CLS = "w-full p-2.5 bg-pw-panel2 text-white text-sm border border-white/10 outline-none focus:border-pw-red/50";
const BTN_CLS = "w-full p-2.5 bg-pw-red hover:bg-[#ff7676] text-white text-sm font-semibold transition disabled:bg-white/10 disabled:text-pw-muted disabled:cursor-not-allowed";
const HEAD_CLS = "text-xs text-pw-muted tracking-[0.08em] mb-3";

function SelectedDriverSlot({ driver, isCaptain, onRemove }) {
  const accent = teamAccent(driver.TeamName);
  const badge = CAT_BADGE[driver.PickCategory] || "text-pw-muted bg-white/5";
  return (
    <div className={`flex items-center gap-3 px-3 py-2.5 bg-pw-panel2 border-l-2 ${isCaptain ? "ring-1 ring-pw-risk/40" : ""}`} style={{ borderColor: accent }}>
      <p className="flex-1 min-w-0 text-[12.5px] text-white truncate">
        {isCaptain && <span className="text-pw-risk font-bold mr-1">C</span>}
        {DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}
        <span className="text-pw-muted"> — {driver.TeamName}</span>
      </p>
      <span className={`text-[9.5px] px-1.5 py-0.5 rounded-sm flex-shrink-0 ${badge}`}>{(driver.PickCategory || "").toUpperCase()}</span>
      <span className="text-[12px] text-white w-14 text-right flex-shrink-0">${driver.Price?.toFixed(1)}M</span>
      <button onClick={onRemove} className="text-pw-muted hover:text-pw-red text-sm flex-shrink-0 transition">✕</button>
    </div>
  );
}

function SelectedConstructorSlot({ constructor: c, onRemove }) {
  const accent = teamAccent(c.name);
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 bg-pw-panel2 border-l-2" style={{ borderColor: accent }}>
      <span className="flex-1 text-[12.5px] text-white truncate">{c.name} <span className="text-pw-muted">— Constructor</span></span>
      <span className="text-[12px] text-white flex-shrink-0">${c.price?.toFixed(1)}M</span>
      <button onClick={onRemove} className="text-pw-muted hover:text-pw-red text-sm flex-shrink-0 transition">✕</button>
    </div>
  );
}

function PoolDriverCard({ driver, isSelected, canAdd, onToggle }) {
  const accent = teamAccent(driver.TeamName);
  const dimmed = !isSelected && !canAdd;
  const badge = CAT_BADGE[driver.PickCategory] || "text-pw-muted bg-white/5";
  return (
    <button
      onClick={onToggle}
      disabled={dimmed}
      className={`text-left w-full px-3 py-2.5 border-l-2 transition ${
        isSelected ? "bg-pw-panel ring-1 ring-white/20"
        : dimmed ? "bg-pw-panel2/50 opacity-40 cursor-not-allowed"
        : "bg-pw-panel2 hover:bg-pw-panel cursor-pointer"
      }`}
      style={{ borderColor: accent }}
    >
      <div className="flex items-center gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-[12.5px] text-white truncate">{DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation} <span className="text-pw-muted">— {driver.TeamName}</span></p>
          <p className="text-[10px] text-pw-muted mt-0.5">Grid P{Math.round(driver.GridPosition)} · Pred P{Math.round(driver.Predicted)} · {driver.FantasyValue?.toFixed(2)}</p>
        </div>
        <span className={`text-[9.5px] px-1.5 py-0.5 rounded-sm flex-shrink-0 ${badge}`}>{(driver.PickCategory || "").toUpperCase()}</span>
        <span className="text-[12px] text-white w-14 text-right flex-shrink-0">${driver.Price?.toFixed(1)}M</span>
      </div>
      {isSelected && <p className="text-[9.5px] text-pw-muted/60 mt-1 text-right">Click to remove</p>}
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
      className={`text-left w-full px-3 py-2 border-l-2 transition flex justify-between items-center gap-2 ${
        isSelected ? "bg-pw-panel ring-1 ring-white/20"
        : dimmed ? "bg-pw-panel2/50 opacity-40 cursor-not-allowed"
        : "bg-pw-panel2 hover:bg-pw-panel cursor-pointer"
      }`}
      style={{ borderColor: accent }}
    >
      <div className="min-w-0">
        <p className="text-[12px] text-white truncate">{c.name}</p>
        <p className="text-[9.5px] text-pw-muted mt-0.5">{c.score?.toFixed(2)}</p>
      </div>
      <span className="text-[12px] text-white flex-shrink-0">${c.price?.toFixed(1)}M</span>
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
  const qualityColor = !teamComplete ? "text-pw-muted"
    : scoreVsOptimal >= 90 ? "text-pw-safe"
    : scoreVsOptimal >= 70 ? "text-pw-risk"
    : "text-pw-red";
  const qualityLabel = !teamComplete ? "—"
    : scoreVsOptimal >= 90 ? "Excellent"
    : scoreVsOptimal >= 70 ? "Good"
    : scoreVsOptimal >= 50 ? "Average" : "Weak";
  const budgetPct = Math.min((totalCost / BUDGET) * 100, 100);
  const barColor = overBudget ? "bg-pw-red" : budgetPct > 90 ? "bg-pw-risk" : "bg-pw-safe";
  const driverCategoryCounts = selectedDrivers.reduce((acc, d) => {
    acc[d.PickCategory] = (acc[d.PickCategory] || 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <p className="text-pw-muted text-sm text-center mb-4">Pick 5 drivers + 2 constructors for an upcoming race based on practice data.</p>

      <select
        value={selectedRace}
        onChange={(e) => {
          const race = e.target.value;
          setSelectedRace(race);
          resetPool();
          if (race) fetchSessions(race);
          else setSessions(null);
        }}
        className={`${SELECT_CLS} mb-3`}
      >
        <option value="">Select an upcoming race</option>
        {upcomingRaces.map(r => (
          <option key={r.race_name} value={r.race_name}>{r.race_name}{r.is_sprint ? " 🏁 Sprint" : ""}</option>
        ))}
      </select>

      {selectedRace && selectedIsSprint && (
        <p className="text-pw-risk text-sm mb-3 text-center">Sprint weekend — will use FP1 data</p>
      )}
      {selectedRace && sessions && <SessionSchedule sessions={sessions} />}

      {selectedRace && !pool && !loading && (
        <button
          onClick={loadPool}
          disabled={sessions && !anySessionAvailable}
          className={`${BTN_CLS} mb-4`}
        >
          {sessions && !anySessionAvailable ? "No practice data yet — check back after FP1" : "Load Driver Pool"}
        </button>
      )}

      {error && <p className="text-pw-red text-sm text-center mb-4">{error}</p>}
      {loading && (
        <div className="text-center mb-4">
          <p className="text-pw-muted text-sm">Fetching practice data and running predictions…</p>
          <p className="text-pw-muted/60 text-xs mt-1">This can take up to 30 seconds</p>
        </div>
      )}

      {pool && sessionUsed && (
        <div className="flex items-center gap-2 mb-4 bg-pw-panel2 px-3 py-2 border border-white/[0.06]">
          <span className="w-1.5 h-1.5 rounded-full bg-pw-safe flex-shrink-0" />
          <p className="text-[12px] text-pw-muted">Predictions based on <span className="text-white font-semibold">{sessionUsed}</span> data</p>
        </div>
      )}

      {pool && (
        <div className="space-y-6">
          <div className="bg-pw-panel2 border border-white/[0.06] p-3">
            <div className="flex justify-between text-[12px] mb-2">
              <span className="text-pw-muted">Spent: <span className={`font-semibold ${overBudget ? "text-pw-red" : "text-white"}`}>${totalCost.toFixed(1)}M</span></span>
              <span className="text-pw-muted">Remaining: <span className={`font-semibold ${overBudget ? "text-pw-red" : "text-pw-safe"}`}>
                {overBudget ? `-$${(totalCost - BUDGET).toFixed(1)}M` : `$${remaining.toFixed(1)}M`}
              </span></span>
            </div>
            <div className="h-1.5 bg-white/10 overflow-hidden">
              <div className={`h-full transition-all ${barColor}`} style={{ width: `${budgetPct}%` }} />
            </div>
            {overBudget && <p className="text-pw-red text-[10.5px] mt-2 text-center">Over budget — remove a pick to fix this</p>}
          </div>

          {teamComplete && (
            <div className="bg-pw-panel2 border border-white/[0.06] p-4">
              <p className={HEAD_CLS}>TEAM SUMMARY</p>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-[10px] text-pw-muted mb-1">MY SCORE</p>
                  <p className="text-white font-extrabold text-lg">{myScore.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-pw-muted mb-1">VS OPTIMAL</p>
                  <p className={`font-extrabold text-lg ${qualityColor}`}>{scoreVsOptimal}%</p>
                </div>
                <div>
                  <p className="text-[10px] text-pw-muted mb-1">RATING</p>
                  <p className={`font-extrabold text-lg ${qualityColor}`}>{qualityLabel}</p>
                </div>
              </div>
              {optimalTeam && (
                <p className="text-[10.5px] text-pw-muted text-center mt-3">
                  Optimal score: {optimalTeam.total_score?.toFixed(2)} (cost: ${optimalTeam.total_cost}M)
                </p>
              )}
              <div className="flex justify-center gap-2 mt-3 flex-wrap">
                {Object.entries(driverCategoryCounts).map(([cat, count]) => (
                  <span key={cat} className={`text-[9.5px] px-1.5 py-0.5 rounded-sm ${CAT_BADGE[cat] || "text-pw-muted bg-white/5"}`}>{count}× {cat.toUpperCase()}</span>
                ))}
              </div>
            </div>
          )}

          <div>
            <p className={HEAD_CLS}>YOUR DRIVERS ({selectedDrivers.length}/5)</p>
            <div className="grid grid-cols-1 gap-2 mb-4">
              {selectedDrivers.length === 0
                ? <p className="text-pw-muted/70 text-xs text-center py-4 border border-dashed border-white/10">Click drivers below to add them</p>
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
            <p className={HEAD_CLS}>YOUR CONSTRUCTORS ({selectedConstructors.length}/2)</p>
            <div className="grid grid-cols-1 gap-2 mb-6">
              {selectedConstructors.length === 0
                ? <p className="text-pw-muted/70 text-xs text-center py-4 border border-dashed border-white/10">Click constructors below to add them</p>
                : selectedConstructors.map(c => <SelectedConstructorSlot key={c.name} constructor={c} onRemove={() => toggleConstructor(c)} />)
              }
            </div>
          </div>

          <div>
            <p className={HEAD_CLS}>AVAILABLE DRIVERS</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
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
            <p className={HEAD_CLS}>AVAILABLE CONSTRUCTORS</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
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
