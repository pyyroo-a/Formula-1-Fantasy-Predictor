import { useState, useEffect } from "react";

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

function DriverCard({ driver }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 shadow-lg">
      <div className="flex justify-between items-center mb-2">
        <div>
          <span className="text-xl font-bold">
            {DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}
          </span>
          <span className="text-gray-500 text-sm ml-2">({driver.Abbreviation})</span>
        </div>
        <span className={`text-white text-sm px-3 py-1 rounded-full ${BADGE_COLOR[driver.PickCategory]}`}>
          {driver.PickCategory}
        </span>
      </div>
      <p className="text-gray-400 text-sm mb-2">{driver.TeamName}</p>
      <p className="text-gray-200 text-sm">{driver.Explanation}</p>
      <div className="mt-3 flex justify-between text-xs text-gray-500">
        <span>Grid: P{Math.round(driver.GridPosition)}</span>
        <span>Predicted: P{Math.round(driver.Predicted)}</span>
        <span>Value: {driver.FantasyValue?.toFixed(2)}</span>
      </div>
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
      <div className="flex justify-between items-start mb-1">
        <div>
          <p className="text-lg font-bold leading-tight">
            {DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}
          </p>
          <p className="text-gray-400 text-xs">{driver.TeamName}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <p className="text-white font-semibold">${driver.Price?.toFixed(1)}M</p>
          {driver.PickCategory && (
            <span className={`text-white text-xs px-2 py-0.5 rounded-full ${BADGE_COLOR[driver.PickCategory]}`}>
              {driver.PickCategory}
            </span>
          )}
        </div>
      </div>
      <div className="mt-3 flex justify-between text-xs text-gray-500">
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

function App() {
  const [mode, setMode] = useState("completed"); // "completed" | "upcoming" | "budget"
  const [races, setRaces] = useState([]);
  const [upcomingRaces, setUpcomingRaces] = useState([]);
  const [selectedRace, setSelectedRace] = useState("");
  const [selectedUpcoming, setSelectedUpcoming] = useState("");
  const [selectedBudgetRace, setSelectedBudgetRace] = useState("");
  const [session, setSession] = useState("FP3");
  const [team, setTeam] = useState([]);
  const [budgetTeam, setBudgetTeam] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const selectedIsSprint = upcomingRaces.find(r => r.race_name === selectedUpcoming)?.is_sprint ?? false;

  useEffect(() => {
    fetch("http://127.0.0.1:8000/races")
      .then((res) => res.json())
      .then((data) => setRaces(data))
      .catch(() => setError("Could not load races from server."));

    fetch("http://127.0.0.1:8000/upcoming-races")
      .then((res) => res.json())
      .then((data) => setUpcomingRaces(data))
      .catch(() => {});
  }, []);

  const fetchCompleted = async () => {
    if (!selectedRace) return;
    setLoading(true);
    setError(null);
    setTeam([]);
    try {
      const res = await fetch("http://127.0.0.1:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: selectedRace }),
      });
      const data = await res.json();
      setTeam(data);
    } catch {
      setError("Failed to get team. Make sure the server is running.");
    }
    setLoading(false);
  };

  const fetchUpcoming = async () => {
    if (!selectedUpcoming) return;
    setLoading(true);
    setError(null);
    setTeam([]);
    try {
      const res = await fetch("http://127.0.0.1:8000/predict-upcoming", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year: 2026, race_name: selectedUpcoming, session }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setTeam(data);
    } catch (e) {
      setError(e.message || "Failed to fetch practice data.");
    }
    setLoading(false);
  };

  const fetchBudgetTeam = async () => {
    if (!selectedBudgetRace) return;
    setLoading(true);
    setError(null);
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
      setError(e.message || "Failed to build budget team.");
    }
    setLoading(false);
  };

  const tabs = [
    { id: "completed", label: "Completed Races" },
    { id: "upcoming", label: "Upcoming Race" },
    { id: "budget", label: "Budget Team" },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-4xl font-bold mb-2 text-center">F1 Fantasy Predictor</h1>
      <p className="text-center text-gray-500 mb-8 text-sm">2026 Season</p>

      {/* Mode tabs */}
      <div className="max-w-2xl mx-auto flex rounded-lg overflow-hidden border border-gray-700 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setMode(tab.id); setTeam([]); setBudgetTeam(null); setError(null); }}
            className={`flex-1 py-2 text-sm font-medium transition ${
              mode === tab.id ? "bg-red-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="max-w-2xl mx-auto mb-8">
        {/* Completed races */}
        {mode === "completed" && (
          <>
            <select
              value={selectedRace}
              onChange={(e) => setSelectedRace(e.target.value)}
              className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-4"
            >
              <option value="">Select a completed race</option>
              {races.map((race) => (
                <option key={race} value={race}>{race}</option>
              ))}
            </select>
            <button
              onClick={fetchCompleted}
              disabled={!selectedRace || loading}
              className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-600 transition font-medium"
            >
              {loading ? "Loading..." : "Get Fantasy Team"}
            </button>
          </>
        )}

        {/* Upcoming races */}
        {mode === "upcoming" && (
          <>
            <select
              value={selectedUpcoming}
              onChange={(e) => { setSelectedUpcoming(e.target.value); setTeam([]); }}
              className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-3"
            >
              <option value="">Select upcoming race</option>
              {upcomingRaces.map((r) => (
                <option key={r.race_name} value={r.race_name}>
                  {r.race_name}{r.is_sprint ? " 🏁 Sprint" : ""}
                </option>
              ))}
            </select>

            {selectedIsSprint ? (
              <p className="text-yellow-400 text-sm mb-4 text-center">
                Sprint weekend — prediction will use FP1 data (only practice session available)
              </p>
            ) : (
              <select
                value={session}
                onChange={(e) => setSession(e.target.value)}
                className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-4"
              >
                <option value="FP3">FP3 (recommended)</option>
                <option value="FP2">FP2</option>
              </select>
            )}

            <button
              onClick={fetchUpcoming}
              disabled={!selectedUpcoming || loading}
              className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-600 transition font-medium"
            >
              {loading ? "Fetching practice data..." : "Predict Upcoming Race"}
            </button>
          </>
        )}

        {/* Budget team */}
        {mode === "budget" && (
          <>
            <p className="text-gray-400 text-sm text-center mb-4">
              Finds the highest-scoring 5 drivers + 2 constructors within the $100M budget, based on race predictions.
            </p>
            <select
              value={selectedBudgetRace}
              onChange={(e) => { setSelectedBudgetRace(e.target.value); setBudgetTeam(null); }}
              className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-4"
            >
              <option value="">Select a race</option>
              {races.map((race) => (
                <option key={race} value={race}>{race}</option>
              ))}
            </select>
            <button
              onClick={fetchBudgetTeam}
              disabled={!selectedBudgetRace || loading}
              className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-600 transition font-medium"
            >
              {loading ? "Solving..." : "Build Optimal Team"}
            </button>
          </>
        )}

        {error && (
          <p className="mt-4 text-red-400 text-sm text-center">{error}</p>
        )}
      </div>

      {/* Standard team results */}
      {(mode === "completed" || mode === "upcoming") && team.length > 0 && (
        <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
          {team.map((driver, index) => (
            <DriverCard key={index} driver={driver} />
          ))}
        </div>
      )}

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
