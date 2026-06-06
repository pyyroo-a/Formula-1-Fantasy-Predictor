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
  OCO: "Esteban Ocon",
  ALB: "Alexander Albon",
  SAR: "Logan Sargeant",
  TSU: "Yuki Tsunoda",
  RIC: "Daniel Ricciardo",
  LAW: "Liam Lawson",
  HUL: "Nico Hülkenberg",
  MAG: "Kevin Magnussen",
  BOT: "Valtteri Bottas",
  ZHO: "Zhou Guanyu",
  PER: "Sergio Pérez",
  BEA: "Oliver Bearman",
  ANT: "Andrea Kimi Antonelli",
  COL: "Franco Colapinto",
  BOR: "Gabriel Bortoleto",
  DOO: "Jack Doohan",
  HAD: "Isack Hadjar",
};

function App() {
  const [races, setRaces] = useState([]);
  const [selectedRace, setSelectedRace] = useState("");
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/races")
      .then((res) => res.json())
      .then((data) => setRaces(data));
  }, []);

  const fetchTeam = async () => {
    if (!selectedRace) return;
    setLoading(true);
    const response = await fetch("http://127.0.0.1:8000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ race_name: selectedRace }),
    });
    const data = await response.json();
    setTeam(data);
    setLoading(false);
  };

  const badgeColor = {
    Safe: "bg-green-500",
    Value: "bg-yellow-500",
    Risk: "bg-orange-500",
    Avoid: "bg-red-500",
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-4xl font-bold mb-8 text-center">🏎️ F1 Fantasy Predictor</h1>

      <div className="max-w-2xl mx-auto mb-8">
        <select
          value={selectedRace}
          onChange={(e) => setSelectedRace(e.target.value)}
          className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700"
        >
          <option value="">Select a race</option>
          {races.map((race) => (
            <option key={race} value={race}>{race}</option>
          ))}
        </select>

        <button
          onClick={fetchTeam}
          disabled={!selectedRace || loading}
          className="mt-4 w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-600 transition"
        >
          {loading ? "Loading..." : "Get Fantasy Team"}
        </button>
      </div>

      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
        {team.map((driver, index) => (
          <div key={index} className="bg-gray-800 rounded-xl p-4 shadow-lg">
            <div className="flex justify-between items-center mb-2">
              <div>
                <span className="text-2xl font-bold">{DRIVER_NAMES[driver.Abbreviation] || driver.Abbreviation}</span>
                <span className="text-gray-500 text-sm ml-2">({driver.Abbreviation})</span>
              </div>
              <span className={`text-white text-sm px-3 py-1 rounded-full ${badgeColor[driver.PickCategory]}`}>
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
        ))}
      </div>
    </div>
  );
}

export default App;