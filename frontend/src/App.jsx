import { useState, useEffect } from "react";

// Drop driver headshots into frontend/public/drivers/ named by abbreviation e.g. VER.png
// If an image is missing the component falls back to showing the abbreviation text.

const DRIVER_NAMES = {
  VER: "Max Verstappen",
  NOR: "Lando Norris",
  PIA: "Oscar Piastri",
  LEC: "Charles Leclerc",
  HAM: "Lewis Hamilton",
  RUS: "George Russell",
  SAI: "Carlos Sainz",
  ALO: "Fernando Alonso",
  STR: "Lance Stroll",
  GAS: "Pierre Gasly",
  ALB: "Alexander Albon",
  TSU: "Yuki Tsunoda",
  LAW: "Liam Lawson",
  HUL: "Nico Hülkenberg",
  BEA: "Oliver Bearman",
  ANT: "Andrea Kimi Antonelli",
  BOR: "Gabriel Bortoleto",
  DOO: "Jack Doohan",
  HAD: "Isack Hadjar",
  COL: "Franco Colapinto",
  PER: "Sergio Pérez",
};

const BADGE_COLOR = {
  Safe: "bg-green-500",
  Value: "bg-yellow-500",
  Risk: "bg-orange-500",
  Avoid: "bg-red-500",
};

const TEAM_COLORS = {
  "Red Bull Racing": "#3671C6",
  McLaren: "#FF8000",
  Ferrari: "#E8002D",
  Mercedes: "#27F4D2",
  "Aston Martin": "#229971",
  Alpine: "#FF87BC",
  Williams: "#64C4FF",
  "RB F1 Team": "#6692FF",
  "Kick Sauber": "#52E252",
  Haas: "#B6BABD",
  Audi: "#E8E234",
};

function teamAccent(teamName) {
  for (const [key, color] of Object.entries(TEAM_COLORS)) {
    if (teamName?.toLowerCase().includes(key.toLowerCase())) return color;
  }
  return "#6b7280";
}

function DriverAvatar({ abbreviation, size = "md" }) {
  const [failed, setFailed] = useState(false);
  const cls = size === "sm"
    ? "w-8 h-8 text-xs"
    : size === "lg"
    ? "w-14 h-14 text-sm"
    : "w-10 h-10 text-xs";

  if (!failed) {
    return (
      <img
        src={`/drivers/${abbreviation}.png`}
        alt={abbreviation}
        className={`${cls} rounded-full object-cover object-top bg-gray-700 flex-shrink-0`}
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <div className={`${cls} rounded-full bg-gray-700 flex items-center justify-center font-bold text-gray-400 flex-shrink-0`}>
      {abbreviation}
    </div>
  );
}

function PositionChange({ change, status }) {
  if (status === "DNF") {
    return <span className="text-gray-500 text-sm font-medium">DNF</span>;
  }
  if (change === null || change === undefined) return null;
  if (change > 0) return <span className="text-green-400 font-bold text-sm">+{change} ↑</span>;
  if (change < 0) return <span className="text-red-400 font-bold text-sm">{change} ↓</span>;
  return <span className="text-gray-500 text-sm">—</span>;
}

function RaceResultsTable({ results }) {
  return (
    <div className="space-y-1">
      {results.map((row, i) => {
        const accent = teamAccent(row.TeamName);
        const isDNF = row.Status === "DNF";
        return (
          <div
            key={row.Abbreviation}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 border-l-4 ${isDNF ? "bg-gray-800/50 opacity-60" : "bg-gray-800"}`}
            style={{ borderColor: accent }}
          >
            <span className="text-gray-500 text-xs w-6 text-right flex-shrink-0">
              {isDNF ? "—" : `P${row.Position}`}
            </span>
            <DriverAvatar abbreviation={row.Abbreviation} size="sm" />
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-sm leading-tight truncate">{row.FullName}</p>
              <p className="text-gray-500 text-xs truncate">{row.TeamName}</p>
            </div>
            <div className="text-right flex-shrink-0">
              <PositionChange change={row.PositionChange} status={row.Status} />
              {!isDNF && (
                <p className="text-gray-600 text-xs mt-0.5">from P{row.GridPosition}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function QualifyingTable({ results }) {
  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="flex items-center gap-3 px-3 py-1 text-xs text-gray-500 uppercase tracking-wider">
        <span className="w-6 text-right flex-shrink-0">Pos</span>
        <span className="w-8 flex-shrink-0" />
        <span className="flex-1">Driver</span>
        <div className="flex gap-2 flex-shrink-0 text-right">
          <span className="w-20">Q1</span>
          <span className="w-20">Q2</span>
          <span className="w-20">Q3</span>
        </div>
      </div>
      {results.map((row) => {
        const accent = teamAccent(row.TeamName);
        const inQ3 = row.Q3 !== null;
        const inQ2 = row.Q2 !== null;
        return (
          <div
            key={row.Abbreviation}
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 bg-gray-800 border-l-4"
            style={{ borderColor: accent }}
          >
            <span className="text-gray-400 text-xs w-6 text-right flex-shrink-0 font-medium">
              P{row.Position}
            </span>
            <DriverAvatar abbreviation={row.Abbreviation} size="sm" />
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-sm leading-tight truncate">{row.FullName}</p>
              <p className="text-gray-500 text-xs truncate">{row.TeamName}</p>
            </div>
            <div className="flex gap-2 flex-shrink-0 text-right text-xs font-mono">
              <span className={`w-20 ${inQ3 ? "text-yellow-400" : inQ2 ? "text-white" : "text-gray-400"}`}>
                {row.Q1 ?? "—"}
              </span>
              <span className={`w-20 ${inQ3 ? "text-yellow-400" : inQ2 ? "text-white" : "text-gray-600"}`}>
                {row.Q2 ?? "—"}
              </span>
              <span className={`w-20 ${inQ3 ? "text-yellow-300 font-bold" : "text-gray-600"}`}>
                {row.Q3 ?? "—"}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BudgetDriverCard({ driver }) {
  const accent = teamAccent(driver.TeamName);
  return (
    <div
      className="bg-gray-800 rounded-xl p-4 shadow-lg border-l-4"
      style={{ borderColor: accent }}
    >
      <div className="flex items-start gap-3 mb-1">
        <DriverAvatar abbreviation={driver.Abbreviation} size="md" />
        <div className="flex-1 min-w-0">
          <p className="text-base font-bold leading-tight">
            {DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}
          </p>
          <p className="text-gray-400 text-xs">{driver.TeamName}</p>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <p className="text-white font-semibold">${driver.Price?.toFixed(1)}M</p>
          {driver.PickCategory && (
            <span className={`text-white text-xs px-2 py-0.5 rounded-full ${BADGE_COLOR[driver.PickCategory]}`}>
              {driver.PickCategory}
            </span>
          )}
        </div>
      </div>
      <div className="mt-2 flex justify-between text-xs text-gray-500">
        <span>Grid: P{Math.round(driver.GridPosition)}</span>
        <span>Predicted: P{Math.round(driver.Predicted)}</span>
        <span>Score: {driver.FantasyValue?.toFixed(2)}</span>
      </div>
    </div>
  );
}

function ConstructorCard({ constructor: c }) {
  const accent = teamAccent(c.name);
  return (
    <div
      className="bg-gray-800 rounded-xl p-4 shadow-lg border-l-4 flex justify-between items-center"
      style={{ borderColor: accent }}
    >
      <div>
        <p className="text-lg font-bold">{c.name}</p>
        <p className="text-gray-500 text-xs mt-0.5">Constructor</p>
      </div>
      <div className="text-right">
        <p className="text-white font-semibold">${c.price?.toFixed(1)}M</p>
        <p className="text-gray-500 text-xs">Score: {c.score?.toFixed(2)}</p>
      </div>
    </div>
  );
}

function BudgetBar({ used, total = 100 }) {
  const pct = Math.min((used / total) * 100, 100);
  const remaining = total - used;
  const barColor = pct > 90 ? "bg-red-500" : pct > 75 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div className="mb-6">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">Budget used: <span className="text-white font-medium">${used.toFixed(1)}M</span></span>
        <span className="text-gray-400">Remaining: <span className="text-green-400 font-medium">${remaining.toFixed(1)}M</span></span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function CountdownWidget({ nextRace }) {
  const [timeLeft, setTimeLeft] = useState(null);

  useEffect(() => {
    if (!nextRace?.race_date) return;
    const tick = () => {
      const diff = new Date(nextRace.race_date) - new Date();
      if (diff <= 0) { setTimeLeft(null); return; }
      setTimeLeft({
        days: Math.floor(diff / 86400000),
        hours: Math.floor((diff % 86400000) / 3600000),
        minutes: Math.floor((diff % 3600000) / 60000),
        seconds: Math.floor((diff % 60000) / 1000),
      });
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [nextRace]);

  if (!nextRace) return null;

  return (
    <div className="max-w-2xl mx-auto mb-6 bg-gray-800 rounded-xl p-4 border border-gray-700">
      <p className="text-xs text-gray-500 text-center mb-1 uppercase tracking-wider">Next Race</p>
      <p className="text-center text-white font-bold text-lg mb-3">{nextRace.race_name}</p>
      {timeLeft ? (
        <div className="flex justify-center gap-6">
          {[["Days", timeLeft.days], ["Hours", timeLeft.hours], ["Mins", timeLeft.minutes], ["Secs", timeLeft.seconds]].map(([label, val]) => (
            <div key={label} className="text-center">
              <p className="text-2xl font-mono font-bold text-red-500">{String(val).padStart(2, "0")}</p>
              <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-center text-green-400 text-sm font-medium">Race weekend is here!</p>
      )}
    </div>
  );
}

function WeekendTeamWidget() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/weekend-team")
      .then((res) => res.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading || !data || !data.active || !data.team) return null;

  const { race_name, session_used, team } = data;

  return (
    <div className="max-w-2xl mx-auto mb-6 bg-gray-900 rounded-xl border border-red-600/40 overflow-hidden">
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
        <div className="grid grid-cols-1 gap-1.5">
          {team.drivers.map((d) => {
            const accent = teamAccent(d.TeamName);
            return (
              <div key={d.Abbreviation} className="flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-2 border-l-4" style={{ borderColor: accent }}>
                <DriverAvatar abbreviation={d.Abbreviation} size="sm" />
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-sm">{DRIVER_NAMES[d.Abbreviation] || d.Abbreviation}</span>
                  <span className="text-gray-500 text-xs ml-2">{d.TeamName}</span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-white text-xs px-2 py-0.5 rounded-full ${BADGE_COLOR[d.PickCategory]}`}>{d.PickCategory}</span>
                  <span className="text-gray-400 text-xs">${d.Price?.toFixed(1)}M</span>
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

const BUDGET = 100.0;

function ManualTeamBuilder({ upcomingRaces }) {
  const [selectedRace, setSelectedRace] = useState("");
  const [session, setSession] = useState("FP3");
  const [pool, setPool] = useState(null);
  const [optimalTeam, setOptimalTeam] = useState(null);
  const [selectedDrivers, setSelectedDrivers] = useState([]);
  const [selectedConstructors, setSelectedConstructors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const selectedIsSprint = upcomingRaces.find(r => r.race_name === selectedRace)?.is_sprint ?? false;

  const resetPool = () => {
    setPool(null);
    setOptimalTeam(null);
    setSelectedDrivers([]);
    setSelectedConstructors([]);
    setError(null);
  };

  const loadPool = async () => {
    if (!selectedRace) return;
    resetPool();
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/upcoming-race-pool", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year: 2026, race_name: selectedRace, session: selectedIsSprint ? "FP1" : session }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setPool(data.pool);
      if (data.optimal) setOptimalTeam(data.optimal);
    } catch (e) {
      setError(e.message || "Failed to load race data.");
    }
    setLoading(false);
  };

  const toggleDriver = (driver) => {
    const isSelected = selectedDrivers.some(d => d.Abbreviation === driver.Abbreviation);
    if (isSelected) {
      setSelectedDrivers(prev => prev.filter(d => d.Abbreviation !== driver.Abbreviation));
    } else if (selectedDrivers.length < 5) {
      setSelectedDrivers(prev => [...prev, driver]);
    }
  };

  const toggleConstructor = (constructor) => {
    const isSelected = selectedConstructors.some(c => c.name === constructor.name);
    if (isSelected) {
      setSelectedConstructors(prev => prev.filter(c => c.name !== constructor.name));
    } else if (selectedConstructors.length < 2) {
      setSelectedConstructors(prev => [...prev, constructor]);
    }
  };

  const driverCost = selectedDrivers.reduce((s, d) => s + d.Price, 0);
  const constructorCost = selectedConstructors.reduce((s, c) => s + c.price, 0);
  const totalCost = driverCost + constructorCost;
  const remaining = BUDGET - totalCost;
  const overBudget = totalCost > BUDGET;
  const teamComplete = selectedDrivers.length === 5 && selectedConstructors.length === 2;

  const myScore = selectedDrivers.reduce((s, d) => s + d.FantasyValue, 0)
    + selectedConstructors.reduce((s, c) => s + c.score, 0);

  const driverCategoryCounts = selectedDrivers.reduce((acc, d) => {
    acc[d.PickCategory] = (acc[d.PickCategory] || 0) + 1;
    return acc;
  }, {});

  const scoreVsOptimal = optimalTeam ? Math.round((myScore / optimalTeam.total_score) * 100) : null;

  const qualityColor = !teamComplete ? "text-gray-400"
    : scoreVsOptimal >= 90 ? "text-green-400"
    : scoreVsOptimal >= 70 ? "text-yellow-400"
    : "text-orange-400";

  const qualityLabel = !teamComplete ? "—"
    : scoreVsOptimal >= 90 ? "Excellent"
    : scoreVsOptimal >= 70 ? "Good"
    : scoreVsOptimal >= 50 ? "Average"
    : "Weak";

  const budgetPct = Math.min((totalCost / BUDGET) * 100, 100);
  const barColor = overBudget ? "bg-red-500" : budgetPct > 90 ? "bg-yellow-500" : "bg-green-500";

  return (
    <div>
      <p className="text-gray-400 text-sm text-center mb-4">
        Pick 5 drivers + 2 constructors for an upcoming race based on practice data.
      </p>

      <select
        value={selectedRace}
        onChange={(e) => { setSelectedRace(e.target.value); resetPool(); }}
        className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-3"
      >
        <option value="">Select an upcoming race</option>
        {upcomingRaces.map((r) => (
          <option key={r.race_name} value={r.race_name}>
            {r.race_name}{r.is_sprint ? " 🏁 Sprint" : ""}
          </option>
        ))}
      </select>

      {selectedRace && (
        selectedIsSprint ? (
          <p className="text-yellow-400 text-sm mb-3 text-center">Sprint weekend — will use FP1 data</p>
        ) : (
          <select
            value={session}
            onChange={(e) => setSession(e.target.value)}
            className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-3"
          >
            <option value="FP3">FP3 (recommended)</option>
            <option value="FP2">FP2</option>
            <option value="FP1">FP1</option>
          </select>
        )
      )}

      {selectedRace && !pool && !loading && (
        <button
          onClick={loadPool}
          className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 transition font-medium mb-4"
        >
          Load Driver Pool
        </button>
      )}

      {error && <p className="text-red-400 text-sm text-center mb-4">{error}</p>}
      {loading && (
        <div className="text-center mb-4">
          <p className="text-gray-400 text-sm">Fetching practice data and running predictions...</p>
          <p className="text-gray-600 text-xs mt-1">This can take up to 30 seconds</p>
        </div>
      )}

      {pool && (
        <div className="space-y-6">
          {/* Budget bar */}
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400">
                Spent: <span className={`font-semibold ${overBudget ? "text-red-400" : "text-white"}`}>${totalCost.toFixed(1)}M</span>
              </span>
              <span className="text-gray-400">
                Remaining: <span className={`font-semibold ${overBudget ? "text-red-400" : "text-green-400"}`}>
                  {overBudget ? `-$${(totalCost - BUDGET).toFixed(1)}M` : `$${remaining.toFixed(1)}M`}
                </span>
              </span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${budgetPct}%` }} />
            </div>
            {overBudget && (
              <p className="text-red-400 text-xs mt-2 text-center">Over budget — remove a pick to fix this</p>
            )}
          </div>

          {/* Team quality panel */}
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
                  <span key={cat} className={`text-white text-xs px-2 py-0.5 rounded-full ${BADGE_COLOR[cat]}`}>
                    {count}× {cat}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Selected team */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
              Your Drivers ({selectedDrivers.length}/5)
            </h3>
            <div className="grid grid-cols-1 gap-2 mb-4">
              {selectedDrivers.length === 0 ? (
                <p className="text-gray-600 text-sm text-center py-4 border border-dashed border-gray-700 rounded-lg">
                  Click drivers below to add them
                </p>
              ) : (
                selectedDrivers.map((d) => (
                  <SelectedDriverSlot key={d.Abbreviation} driver={d} onRemove={() => toggleDriver(d)} />
                ))
              )}
            </div>

            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
              Your Constructors ({selectedConstructors.length}/2)
            </h3>
            <div className="grid grid-cols-1 gap-2 mb-6">
              {selectedConstructors.length === 0 ? (
                <p className="text-gray-600 text-sm text-center py-4 border border-dashed border-gray-700 rounded-lg">
                  Click constructors below to add them
                </p>
              ) : (
                selectedConstructors.map((c) => (
                  <SelectedConstructorSlot key={c.name} constructor={c} onRemove={() => toggleConstructor(c)} />
                ))
              )}
            </div>
          </div>

          {/* Driver pool */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Available Drivers</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {pool.drivers.map((driver) => {
                const isSelected = selectedDrivers.some(d => d.Abbreviation === driver.Abbreviation);
                const canAdd = !isSelected && selectedDrivers.length < 5;
                return (
                  <PoolDriverCard
                    key={driver.Abbreviation}
                    driver={driver}
                    isSelected={isSelected}
                    canAdd={canAdd}
                    onToggle={() => toggleDriver(driver)}
                  />
                );
              })}
            </div>
          </div>

          {/* Constructor pool */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Available Constructors</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {pool.constructors.map((c) => {
                const isSelected = selectedConstructors.some(sc => sc.name === c.name);
                const canAdd = !isSelected && selectedConstructors.length < 2;
                return (
                  <PoolConstructorCard
                    key={c.name}
                    constructor={c}
                    isSelected={isSelected}
                    canAdd={canAdd}
                    onToggle={() => toggleConstructor(c)}
                  />
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SelectedDriverSlot({ driver, onRemove }) {
  const accent = teamAccent(driver.TeamName);
  return (
    <div className="bg-gray-800 rounded-lg p-3 border-l-4 flex items-center gap-2" style={{ borderColor: accent }}>
      <DriverAvatar abbreviation={driver.Abbreviation} size="sm" />
      <div className="flex-1 min-w-0">
        <span className="font-semibold text-sm">{DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}</span>
        <span className="text-gray-500 text-xs ml-2">${driver.Price?.toFixed(1)}M</span>
        <span className={`ml-2 text-white text-xs px-2 py-0.5 rounded-full ${BADGE_COLOR[driver.PickCategory]}`}>
          {driver.PickCategory}
        </span>
      </div>
      <button onClick={onRemove} className="text-gray-500 hover:text-red-400 text-xs ml-2 transition flex-shrink-0">✕</button>
    </div>
  );
}

function SelectedConstructorSlot({ constructor: c, onRemove }) {
  const accent = teamAccent(c.name);
  return (
    <div className="bg-gray-800 rounded-lg p-3 border-l-4 flex justify-between items-center" style={{ borderColor: accent }}>
      <div>
        <span className="font-semibold text-sm">{c.name}</span>
        <span className="text-gray-500 text-xs ml-2">${c.price?.toFixed(1)}M</span>
      </div>
      <button onClick={onRemove} className="text-gray-500 hover:text-red-400 text-xs ml-2 transition">✕</button>
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
      className={`text-left w-full rounded-xl p-3 border-l-4 transition ${
        isSelected ? "bg-gray-700 ring-2 ring-white/20"
        : dimmed ? "bg-gray-800/50 opacity-40 cursor-not-allowed"
        : "bg-gray-800 hover:bg-gray-750 cursor-pointer"
      }`}
      style={{ borderColor: accent }}
    >
      <div className="flex items-start gap-2">
        <DriverAvatar abbreviation={driver.Abbreviation} size="sm" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm leading-tight truncate">
            {DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}
          </p>
          <p className="text-gray-400 text-xs">{driver.TeamName}</p>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <p className="text-white text-sm font-semibold">${driver.Price?.toFixed(1)}M</p>
          <span className={`text-white text-xs px-2 py-0.5 rounded-full ${BADGE_COLOR[driver.PickCategory]}`}>
            {driver.PickCategory}
          </span>
        </div>
      </div>
      <div className="flex justify-between text-xs text-gray-500 mt-2">
        <span>Grid: P{Math.round(driver.GridPosition)}</span>
        <span>Predicted: P{Math.round(driver.Predicted)}</span>
        <span>Score: {driver.FantasyValue?.toFixed(2)}</span>
      </div>
      {isSelected && <p className="text-xs text-white/50 mt-1 text-right">Click to remove</p>}
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
      className={`text-left w-full rounded-xl p-3 border-l-4 transition flex justify-between items-center ${
        isSelected ? "bg-gray-700 ring-2 ring-white/20"
        : dimmed ? "bg-gray-800/50 opacity-40 cursor-not-allowed"
        : "bg-gray-800 hover:bg-gray-750 cursor-pointer"
      }`}
      style={{ borderColor: accent }}
    >
      <div>
        <p className="font-semibold text-sm">{c.name}</p>
        <p className="text-gray-500 text-xs">Score: {c.score?.toFixed(2)}</p>
      </div>
      <div className="text-right">
        <p className="text-white font-semibold text-sm">${c.price?.toFixed(1)}M</p>
        {isSelected && <p className="text-xs text-white/50 mt-1">Click to remove</p>}
      </div>
    </button>
  );
}

function App() {
  const [mode, setMode] = useState("results");
  const [races, setRaces] = useState([]);
  const [upcomingRaces, setUpcomingRaces] = useState([]);
  const [nextRace, setNextRace] = useState(null);

  // Race Results tab
  const [resultsRace, setResultsRace] = useState("");
  const [raceResults, setRaceResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState(null);

  // Qualifying tab
  const [qualRace, setQualRace] = useState("");
  const [qualResults, setQualResults] = useState(null);
  const [qualLoading, setQualLoading] = useState(false);
  const [qualError, setQualError] = useState(null);

  // Budget Team tab
  const [selectedBudgetRace, setSelectedBudgetRace] = useState("");
  const [budgetTeam, setBudgetTeam] = useState(null);
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [budgetError, setBudgetError] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/races")
      .then((r) => r.json())
      .then(setRaces)
      .catch(() => {});

    fetch("http://127.0.0.1:8000/upcoming-races")
      .then((r) => r.json())
      .then(setUpcomingRaces)
      .catch(() => {});

    fetch("http://127.0.0.1:8000/next-race")
      .then((r) => r.json())
      .then(setNextRace)
      .catch(() => {});
  }, []);

  const fetchRaceResults = async (raceName) => {
    if (!raceName) return;
    setResultsLoading(true);
    setResultsError(null);
    setRaceResults(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/race-results", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: raceName }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setRaceResults(data);
    } catch (e) {
      setResultsError(e.message || "Failed to load race results.");
    }
    setResultsLoading(false);
  };

  const fetchQualifying = async () => {
    if (!qualRace) return;
    setQualLoading(true);
    setQualError(null);
    setQualResults(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/qualifying-results", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: qualRace }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setQualResults(data);
    } catch (e) {
      setQualError(e.message || "Failed to load qualifying data.");
    }
    setQualLoading(false);
  };

  const fetchBudgetTeam = async () => {
    if (!selectedBudgetRace) return;
    setBudgetLoading(true);
    setBudgetError(null);
    setBudgetTeam(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/predict-budget", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: selectedBudgetRace, budget: 100.0 }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setBudgetTeam(data);
    } catch (e) {
      setBudgetError(e.message || "Failed to build budget team.");
    }
    setBudgetLoading(false);
  };

  const tabs = [
    { id: "results",     label: "Race Results" },
    { id: "qualifying",  label: "Qualifying" },
    { id: "budget",      label: "Budget Team" },
    { id: "manual",      label: "Manual Team" },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-4xl font-bold mb-2 text-center">F1 Fantasy Predictor</h1>
      <p className="text-center text-gray-500 mb-6 text-sm">2026 Season</p>

      <CountdownWidget nextRace={nextRace} />
      <WeekendTeamWidget />

      {/* Tabs */}
      <div className="max-w-2xl mx-auto flex rounded-lg overflow-hidden border border-gray-700 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setMode(tab.id)}
            className={`flex-1 py-2 text-xs font-medium transition ${
              mode === tab.id ? "bg-red-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="max-w-2xl mx-auto mb-8">

        {/* Race Results */}
        {mode === "results" && (
          <>
            <select
              value={resultsRace}
              onChange={(e) => {
                setResultsRace(e.target.value);
                fetchRaceResults(e.target.value);
              }}
              className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-4"
            >
              <option value="">Select a completed race</option>
              {races.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {resultsLoading && <p className="text-gray-400 text-sm text-center">Loading results...</p>}
            {resultsError && <p className="text-red-400 text-sm text-center">{resultsError}</p>}
            {raceResults && (
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Race Results</h2>
                  <span className="text-xs text-gray-600">{resultsRace}</span>
                </div>
                <RaceResultsTable results={raceResults} />
              </div>
            )}
          </>
        )}

        {/* Qualifying */}
        {mode === "qualifying" && (
          <>
            <select
              value={qualRace}
              onChange={(e) => { setQualRace(e.target.value); setQualResults(null); setQualError(null); }}
              className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-3"
            >
              <option value="">Select a completed race</option>
              {races.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {qualRace && !qualResults && !qualLoading && (
              <button
                onClick={fetchQualifying}
                className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 transition font-medium mb-4"
              >
                Load Qualifying Results
              </button>
            )}
            {qualLoading && (
              <div className="text-center mb-4">
                <p className="text-gray-400 text-sm">Fetching qualifying data from FastF1...</p>
                <p className="text-gray-600 text-xs mt-1">May take 15–30 seconds on first load</p>
              </div>
            )}
            {qualError && <p className="text-red-400 text-sm text-center mb-4">{qualError}</p>}
            {qualResults && (
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Qualifying</h2>
                  <span className="text-xs text-gray-600">{qualRace}</span>
                </div>
                <QualifyingTable results={qualResults} />
              </div>
            )}
          </>
        )}

        {/* Budget Team */}
        {mode === "budget" && (
          <>
            <p className="text-gray-400 text-sm text-center mb-4">
              Finds the highest-scoring 5 drivers + 2 constructors within the $100M budget.
            </p>
            <select
              value={selectedBudgetRace}
              onChange={(e) => { setSelectedBudgetRace(e.target.value); setBudgetTeam(null); }}
              className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-4"
            >
              <option value="">Select a race</option>
              {races.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            <button
              onClick={fetchBudgetTeam}
              disabled={!selectedBudgetRace || budgetLoading}
              className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-600 transition font-medium"
            >
              {budgetLoading ? "Solving..." : "Build Optimal Team"}
            </button>
            {budgetError && <p className="mt-4 text-red-400 text-sm text-center">{budgetError}</p>}
          </>
        )}

        {/* Manual Team */}
        {mode === "manual" && (
          <ManualTeamBuilder upcomingRaces={upcomingRaces} />
        )}
      </div>

      {/* Budget team results */}
      {mode === "budget" && budgetTeam && (
        <div className="max-w-4xl mx-auto">
          <BudgetBar used={budgetTeam.total_cost} />
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-200">Optimal Team</h2>
            <div className="text-right">
              <p className="text-xs text-gray-500">Total score</p>
              <p className="text-white font-bold">{budgetTeam.total_score?.toFixed(2)}</p>
            </div>
          </div>
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Drivers</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {budgetTeam.drivers.map((driver, i) => (
              <BudgetDriverCard key={i} driver={driver} />
            ))}
          </div>
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Constructors</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {budgetTeam.constructors.map((c, i) => (
              <ConstructorCard key={i} constructor={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
