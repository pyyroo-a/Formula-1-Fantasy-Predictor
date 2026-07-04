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

function App() {
  const [mode, setMode] = useState("completed"); // "completed" | "upcoming"
  const [races, setRaces] = useState([]);
  const [upcomingRaces, setUpcomingRaces] = useState([]); // [{ race_name, is_sprint }]
  const [selectedRace, setSelectedRace] = useState("");
  const [selectedUpcoming, setSelectedUpcoming] = useState("");
  const [session, setSession] = useState("FP3");
  const [team, setTeam] = useState([]);
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

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-4xl font-bold mb-2 text-center">🏎️ F1 Fantasy Predictor</h1>
      <p className="text-center text-gray-500 mb-8 text-sm">2026 Season</p>

      {/* Mode toggle */}
      <div className="max-w-2xl mx-auto flex rounded-lg overflow-hidden border border-gray-700 mb-6">
        <button
          onClick={() => { setMode("completed"); setTeam([]); setError(null); }}
          className={`flex-1 py-2 text-sm font-medium transition ${
            mode === "completed" ? "bg-red-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          }`}
        >
          Completed Races
        </button>
        <button
          onClick={() => { setMode("upcoming"); setTeam([]); setError(null); }}
          className={`flex-1 py-2 text-sm font-medium transition ${
            mode === "upcoming" ? "bg-red-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          }`}
        >
          Upcoming Race
        </button>
      </div>

      <div className="max-w-2xl mx-auto mb-8">
        {mode === "completed" ? (
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
        ) : (
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

        {error && (
          <p className="mt-4 text-red-400 text-sm text-center">{error}</p>
        )}
      </div>

      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
        {team.map((driver, index) => (
          <DriverCard key={index} driver={driver} />
        ))}
      </div>
    </div>
  );
}

export default App;
